import os
import pathlib
import json
import tempfile
import subprocess

import numpy as np
import pandas as pd
from datetime import datetime
import pyodbc
from dataclasses import dataclass
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import logging

pyodbc.pooling = False


@dataclass
class DBColumn:

    columnName: str
    columnType: str
    isPrimaryKey: bool = False
    isAutoIncrement: bool = False
    isNullable: bool = False

    def getCreateString(self, tableName: str):

        createStr = "[" + self.columnName + "] " + self.columnType + " "
        createStr += " IDENTITY(1,1)" if self.isAutoIncrement else ""
        createStr += ("" if self.isNullable else " NOT ") + "NULL "
        createStr += ", "

        primaryKeyIndexStr = None
        if self.isPrimaryKey:
            primaryKeyIndexStr = (
                f"CONSTRAINT [PK_{tableName}] PRIMARY KEY CLUSTERED ([{self.columnName}] ASC) "
                + f"WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, "
                + f"ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]"
            )
        return createStr, primaryKeyIndexStr


class DBConnection:

    utils = None
    logger = None

    config: dict = None
    pyodbcCnxn: object = None
    alchemyCnxn: object = None
    defaultSchema: str = None

    def __init__(self, utils, config):
        self.logger = logging.getLogger(__name__)

        self.utils = utils
        self.config = config["db"]
        self.getConnectionConfig(secretsConfig=config["secrets"])
        self.openDBConnection()

        self.defaultSchema = self.config["defaultSchema"]
        return

    def getConnectionConfig(self, secretsConfig: dict) -> dict:
        connstrKey = self.config["connstrKey"]
        connstrParams = None
        if connstrKey in os.environ:
            connstrParams = os.environ[connstrKey]
        else:
            connstrParams = secretsConfig[connstrKey]
        paramsDict = dict(
            subString.split("=")
            for subString in connstrParams.split(";")
            if ("=" in subString)
        )
        self.config = dict(self.config, **paramsDict)
        return

    def openDBConnection(self) -> bool:
        # Read connection string from environment variable
        # If not available there, then read from db_connstr.json
        trustedCnxn = (
            True
            if (self.config["uid"] is None or len(self.config["uid"]) == 0)
            else False
        )

        # pyodbc connection for read operations
        self.pyodbcCnxn = pyodbc.connect(
            driver=self.config["driver"],
            server=self.config["server"],
            uid=None if trustedCnxn else self.config["uid"],
            pwd=None if trustedCnxn else self.config["pwd"],
            database=self.config["database"],
            trusted_connection=("yes" if trustedCnxn else "no"),
        )

        # sqlalchemy connection for write operations
        sqlAlchemyString = (
            "mssql+pyodbc://"
            + ("" if trustedCnxn else self.config["uid"] + ":" + self.config["pwd"])
            + "@"
            + self.config["server"]
            + "/"
            + self.config["database"]
            + "?driver="
            + self.config["driver"].replace(" ", "+")
            + ("&trusted_connection=yes" if trustedCnxn else "")
        )

        self.logger.info(
            f"Connected to DB: {self.config['database']}@{self.config['server']}"
        )
        self.alchemyCnxn = create_engine(sqlAlchemyString, fast_executemany=True)

        return True

    def closeDBConnection(self):
        if self.pyodbcCnxn is not None:
            self.pyodbcCnxn.close()
        if self.alchemyCnxn is not None:
            self.alchemyCnxn.close()

    # -------------------------------------------------------------------------#
    # ------------------------- DATABASE READ/WRITE  --------------------------#

    # Function that takes as argument another function and optional keyword arguments
    # The execFunction is executed with db connection retry enabled - so if there is
    # a communication failure error, the connection is re-established and the function
    # is executed again.
    def execWithCnxnRetry(
        self,
        execFunction: object = None,
        alchemySession: bool = False,
        alchemyExecute: bool = False,
        **kwargs,
    ):
        results = None
        retryCount = 0
        retryFlag = True
        maxRetries = self.config["maxRetries"]
        while retryFlag and retryCount < maxRetries:
            try:
                if alchemySession:
                    with Session(self.alchemyCnxn) as session:
                        if alchemyExecute:
                            session.execute(
                                **kwargs,
                            )
                        else:
                            results = execFunction(con=session.get_bind(), **kwargs)
                        session.commit()
                else:
                    results = execFunction(con=self.pyodbcCnxn, **kwargs)
            except SQLAlchemyError as err:
                self.logger.error(
                    f"{type(err)} error encountered when executing SQL query."
                )
                self.logger.error(err)
                exit()
            except pyodbc.Error as err:
                if err.args[0] == "08S01":  # Communication failure error
                    self.logger.error(
                        f"DB communication failure: {retryCount}/{maxRetries}. Retrying after 1 second."
                    )
                    if alchemySession:
                        session.rollback()

                    self.closeDBConnection()
                    self.openDBConnection()
                    retryFlag = True
                else:
                    self.logger.error(
                        f"{type(err)} error encountered when executing SQL query."
                    )
                    self.logger.error(err)
            retryFlag = False
        return results

    # Function to execute any select query and return a dataframe of results
    def execSelectQuery(self, query: str) -> pd.DataFrame:
        results = self.execWithCnxnRetry(
            execFunction=pd.read_sql,
            alchemySession=True,
            alchemyExecute=False,
            sql=query,
            chunksize=self.config["maxReadRows"],
        )

        results = pd.concat([chunk for chunk in results], axis=0, ignore_index=True)
        results.reset_index(drop=True, inplace=True)
        return results

    # Function to create a new table in the database, given a schema name,
    # table name and a list of columns of type DBColumn
    def execCreateTableQuery(
        self,
        tableName: str,
        columnList: list,
        indexColumns: list = None,
        dropExisting: bool = False,
    ) -> bool:

        query = ""
        if dropExisting:
            query += f"DROP TABLE IF EXISTS {self.defaultSchema}.{tableName}; "
        elif self.checkTableExists(tableName=tableName, schemaName=self.defaultSchema):
            # Table already exists and dropExisting is False
            return True

        query += f"CREATE TABLE {self.defaultSchema}.{tableName} ("
        primaryKeyIndexStr = None
        for column in columnList:
            createStr, pkStr = column.getCreateString(tableName=tableName)
            if pkStr is not None:
                primaryKeyIndexStr = pkStr
            query += createStr
        if primaryKeyIndexStr is not None:
            query += primaryKeyIndexStr

        query += ") ON [PRIMARY]; "

        if indexColumns is not None:
            for columnName in indexColumns:
                query += f"CREATE NONCLUSTERED INDEX [IX_{tableName}_{columnName}] ON {self.defaultSchema}.{tableName} ([{columnName}] ASC)"
                query += " WITH (STATISTICS_NORECOMPUTE = OFF, DROP_EXISTING = OFF, ONLINE = OFF) ON [PRIMARY]; "

        self.execWithCnxnRetry(
            alchemySession=True, alchemyExecute=True, statement=query
        )

        return True

    # Function to insert rows from a dataframe into an SQL table
    def execInsertQuery(
        self,
        tableName: str,
        insertData: pd.DataFrame,
        truncateData: bool = False,
    ) -> bool:
        if self.utils.isNullDataFrame(insertData):
            self.logger.warn("Empty dataframe found - nothing to insert.")
            return True
        if not self.checkTableExists(
            tableName=tableName, schemaName=self.defaultSchema
        ):
            self.logger.warn(f"Insert statement failed - {tableName} does not exist.")
            return False

        if truncateData:
            query = f"TRUNCATE TABLE {self.defaultSchema}.{tableName}; "
            query += (
                f"DBCC CHECKIDENT ('{self.defaultSchema}.{tableName}', RESEED, 1); "
            )
            self.execWithCnxnRetry(
                alchemySession=True, alchemyExecute=True, statement=query
            )

        if (self.config["bcpToggle"] == 1) and (
            insertData.shape[0] >= self.config["maxInsertRows"]
        ):
            self.execInsertWithBCP(insertData=insertData, tableName=tableName)
        else:
            self.execWithCnxnRetry(
                execFunction=insertData.to_sql,
                alchemySession=True,
                name=tableName,
                schema=self.defaultSchema,
                if_exists="append",
                index=False,
                chunksize=self.config["maxInsertRows"],
                method=None,
            )

        return True

    # Function to delete rows from an SQL table filtered by matching data in a dataframe
    # IMP: The filter condition across multiple columns is applied with AND so the columns
    # should only have 1-to-1 mapping for the correct set of rows to get deleted
    def execDeleteByData(self, tableName: str, deleteData: pd.DataFrame) -> bool:
        deleteQueries = []
        for col in deleteData.columns:
            deleteQueries.append((col, list(deleteData[col])))
        return self.execDeleteByQueries(
            tableName=tableName, deleteQueries=deleteQueries, isQueryCondition=False
        )

    # Function to delete rows from an SQL table filtered by a delete query
    def execDeleteByQuery(
        self, tableName: str, filterColumn: str, deleteQuery: str
    ) -> bool:
        return self.execDeleteByQueries(
            tableName=tableName, deleteQueries=[(filterColumn, deleteQuery)]
        )

    # Function to delete rows from an SQL table filtered by multiple delete queries
    def execDeleteByQueries(
        self, tableName: str, deleteQueries: list, isQueryCondition: bool = True
    ) -> bool:
        if not self.checkTableExists(
            tableName=tableName, schemaName=self.defaultSchema
        ):
            self.logger.warn(f"Delete statement failed - {tableName} does not exist.")
            return False

        query = f"DELETE FROM [{self.defaultSchema}].[{tableName}]"
        query += self.getMultipleConditionsSQL(
            filterConditions=deleteQueries, isQueryCondition=isQueryCondition
        )

        self.execWithCnxnRetry(
            alchemySession=True, alchemyExecute=True, statement=query
        )
        return True

    # Function to drop an SQL table from the DB
    def dropTableFromDB(self, tableName: str):
        query = f"DROP TABLE IF EXISTS {self.defaultSchema}.{tableName}; "
        self.execWithCnxnRetry(
            alchemySession=True, alchemyExecute=True, statement=query
        )
        return

    # Function that takes as input a dataframe and writes it to the DB
    # If the table does not exist, it is created based on the dataframe schema
    def writeDataFrameToDB(
        self,
        data: pd.DataFrame,
        tableName: str,
        truncateData: bool = False,
        addPrimaryKey: bool = True,
        addUpdateDate: bool = True,
        overrideTypes: dict = None,
        indexColumns: list = None,
    ) -> bool:

        if addUpdateDate and ("UpdatedOn" not in data):
            data["UpdatedOn"] = self.utils.getLocalISTTime()

        tableExists = self.checkTableExists(
            tableName=tableName, schemaName=self.defaultSchema
        )
        createResult = True
        if not tableExists:
            columnList = self.getColumnListFromData(
                data=data,
                tableName=tableName,
                overrideTypes=overrideTypes,
                addPrimaryKey=addPrimaryKey,
            )
            createResult = self.execCreateTableQuery(
                tableName=tableName,
                columnList=columnList,
                indexColumns=indexColumns,
                dropExisting=False,
            )

        insertResult = False
        if createResult:
            insertResult = self.execInsertQuery(
                tableName=tableName, insertData=data, truncateData=truncateData
            )

        return insertResult

    # Function that alters an existing table to set the primary key column
    # First, the column is set non-nullable int and then the primary key
    # constraint is added
    def setPrimaryKeyColumn(self, tableName: str, columnName: str) -> bool:
        nonNullQuery = f"ALTER TABLE [{self.defaultSchema}].[{tableName}] ALTER COLUMN [{columnName}] INT NOT NULL;"
        self.execWithCnxnRetry(
            alchemySession=True, alchemyExecute=True, statement=nonNullQuery
        )
        primaryKeyQuery = (
            f"ALTER TABLE {self.defaultSchema}.{tableName} ADD CONSTRAINT [PK_{tableName}] PRIMARY KEY CLUSTERED ([{columnName}] ASC) "
            + f"WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, "
            + f"ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]"
        )
        self.execWithCnxnRetry(
            alchemySession=True, alchemyExecute=True, statement=primaryKeyQuery
        )
        return

    # -------------------------------------------------------------------------#
    # -----------------------  SELECT QUERY VARIATIONS ------------------------#

    # Function to select specific columns from a specific table
    def selectTable(
        self,
        tableName: str,
        schemaName: str = None,
        columnList: list = None,
        onlyQuery: bool = False,
    ) -> (pd.DataFrame, str):
        if not self.checkTableExists(tableName=tableName, schemaName=schemaName):
            self.logger.warn(f"Select statement failed - {tableName} does not exist.")
            return None, None
        execQuery, baseQuery = self.getSelectQuery(
            tableName=tableName, schemaName=schemaName, columnList=columnList
        )
        if onlyQuery:
            return None, baseQuery
        data = self.execSelectQuery(query=execQuery)
        return data, baseQuery

    # Function to select specific columns from a specific table with a WHERE clause
    def selectWithWhere(
        self,
        tableName: str,
        schemaName: str = None,
        columnList: list = None,
        filterColumn: str = None,
        filterValue: object = None,
        onlyQuery: bool = False,
    ) -> (pd.DataFrame, str):

        return self.selectWithMultipleWheres(
            tableName=tableName,
            schemaName=schemaName,
            columnList=columnList,
            filterConditions=[(filterColumn, filterValue)],
            onlyQuery=onlyQuery,
        )

    # Function to select specific columns from a specific table with a WHERE clause
    def selectWithMultipleWheres(
        self,
        tableName: str,
        schemaName: str = None,
        columnList: list = None,
        filterConditions: list = None,
        onlyQuery: bool = False,
    ) -> (pd.DataFrame, str):
        if not self.checkTableExists(tableName=tableName, schemaName=schemaName):
            self.logger.warn(f"Select statement failed - {tableName} does not exist.")
            return None, None
        execQuery, baseQuery = self.getSelectQuery(
            tableName=tableName, schemaName=schemaName, columnList=columnList
        )
        conditionsSQL = self.getMultipleConditionsSQL(filterConditions=filterConditions)
        execQuery += conditionsSQL
        baseQuery += conditionsSQL
        if onlyQuery:
            return None, baseQuery
        data = self.execSelectQuery(query=execQuery)
        return data, baseQuery

    # Function to select specific columns from a specific table with a date filter
    def selectWithDates(
        self,
        tableName: str,
        dateColumn: str,
        schemaName: str = None,
        columnList: list = None,
        dateStart: datetime = None,
        dateEnd: datetime = None,
        onlyQuery: bool = False,
    ) -> (pd.DataFrame, str):
        def addDates(query: str):
            return self.addDatesFilterToQuery(
                query=query,
                dateColumn=dateColumn,
                dateStart=dateStart,
                includeStart=True,
                dateEnd=dateEnd,
                includeEnd=True,
            )

        if dateColumn is None:
            self.logger.error(f"Select with dates failed - dateColumn is missing.")
            return None, None
        if not self.checkTableExists(tableName=tableName, schemaName=schemaName):
            self.logger.warn(f"Select statement failed - {tableName} does not exist.")
            return None, None
        execQuery, baseQuery = self.getSelectQuery(
            tableName=tableName, schemaName=schemaName, columnList=columnList
        )
        execQuery = addDates(query=execQuery)
        baseQuery = addDates(query=baseQuery)
        if onlyQuery:
            return None, baseQuery
        data = self.execSelectQuery(query=execQuery)
        return data, baseQuery

    # Function to select specific columns from a specific table with an
    # additional sql query as filter
    def selectWithSQL(
        self,
        tableName: str,
        schemaName: str = None,
        columnList: list = None,
        filterColumn: str = None,
        filterQuery: str = None,
        onlyQuery: bool = False,
    ) -> (pd.DataFrame, str):
        return self.selectWithMultipleSQLs(
            tableName=tableName,
            schemaName=schemaName,
            columnList=columnList,
            filterQueries=[(filterColumn, filterQuery)],
            onlyQuery=onlyQuery,
        )

    # Function to select specific columns from a specific table with
    # additional sql queries as filters
    def selectWithMultipleSQLs(
        self,
        tableName: str,
        schemaName: str = None,
        columnList: list = None,
        filterQueries: list = None,
        onlyQuery: bool = False,
    ) -> (pd.DataFrame, str):
        def addSQLs(query: str):
            if filterQueries is not None:
                if self.utils.isNullList(filterQueries):
                    self.logger.error(
                        "Invalid filterQueries argument for query with multiple sql filters."
                    )
                    return None, None

                for fq in filterQueries:
                    filterColumn, filterQuery = fq
                    if (filterColumn is not None) & (filterQuery is not None):
                        connectorStr = "AND" if "WHERE" in query else "WHERE"
                        query += f" {connectorStr} {filterColumn} IN ({filterQuery})"
            return query

        if not self.checkTableExists(tableName=tableName, schemaName=schemaName):
            self.logger.warn(f"Select statement failed - {tableName} does not exist.")
            return None, None
        execQuery, baseQuery = self.getSelectQuery(
            tableName=tableName,
            schemaName=schemaName,
            columnList=columnList,
        )
        execQuery = addSQLs(query=execQuery)
        baseQuery = addSQLs(query=baseQuery)
        if onlyQuery:
            return None, baseQuery
        data = self.execSelectQuery(query=execQuery)
        return data, baseQuery

    # Function that takes an sql query as input and adds date filters to it
    # Start and End dates can be added with inclusive/ exclusive boundary dates
    def addDatesFilterToQuery(
        self,
        query: str,
        dateColumn: str,
        dateStart: datetime = None,
        includeStart: bool = False,
        dateEnd: datetime = None,
        includeEnd: bool = False,
    ) -> str:
        def appendCondition(q, val, opr=">", eq=False):
            conn = "AND" if ("WHERE" in q) else "WHERE"
            if val is not None:
                q += f" {conn} {dateColumn} {opr}{'=' if eq else ''} '{self.getSQLDate(val)}'"
            return q

        query = appendCondition(query, dateStart, ">", includeStart)
        query = appendCondition(query, dateEnd, "<", includeEnd)
        return query

    # -------------------------------------------------------------------------#
    # -------------------------- SQL UTIL FUNCTIONS ---------------------------#

    # Function that generates a list of sql columns based on the dataframe
    def getColumnListFromData(
        self,
        data: pd.DataFrame,
        tableName: str,
        overrideTypes: dict = None,
        addPrimaryKey: bool = False,
    ) -> list:
        columnList = list()
        if addPrimaryKey:
            primaryKeyCol = DBColumn(
                columnName=f"{tableName}Id",
                columnType="INT",
                isPrimaryKey=True,
                isAutoIncrement=True,
                isNullable=False,
            )
            columnList.append(primaryKeyCol)

        for col in data.columns:
            colType = (
                overrideTypes[col]
                if ((overrideTypes is not None) and (col in overrideTypes))
                else self.getSQLVariableType(colType=data[col].dtype)
            )
            newCol = DBColumn(
                columnName=col,
                columnType=colType,
                isNullable=True,
            )
            columnList.append(newCol)

        return columnList

    # Function that checks if a table exists in the given schema
    def checkTableExists(self, tableName: str, schemaName: str) -> bool:
        if schemaName is None:
            schemaName = self.defaultSchema
        query = (
            f"SELECT 1 WHERE (OBJECT_ID('[{schemaName}].[{tableName}]') IS NOT NULL)"
        )
        results = self.execSelectQuery(query)
        tableExists = not self.utils.isNullDataFrame(results)
        return tableExists

    # Function to get the table schema for any table in the database
    def getTableSchema(self, tableName: str) -> (pd.DataFrame, str):
        query = (
            f"SELECT ORDINAL_POSITION, COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT "
            + f"FROM INFORMATION_SCHEMA. COLUMNS WHERE TABLE_NAME = '{tableName}'"
        )
        results = self.execSelectQuery(query)
        return results, str

    def setSelectColumns(self, query: str, columnList: list) -> str:
        if self.utils.isNullList(columnList):
            return query
        query = query.replace("*", ",".join(columnList))
        return query

    # Function that creates the generic SQL select statment
    def getSelectQuery(
        self, tableName: str, schemaName: str = None, columnList: list = None
    ) -> str:
        if schemaName is None:
            schemaName = self.defaultSchema
        baseQuery = f"SELECT * FROM [{schemaName}].[{tableName}] WITH (NOLOCK)"
        execQuery = self.setSelectColumns(query=baseQuery, columnList=columnList)
        return execQuery, baseQuery

    # Function that generates the SQL WHERE condition statement based
    # on the list of filter conditions
    def getMultipleConditionsSQL(
        self, filterConditions: list, isQueryCondition: bool = False
    ) -> str:
        query = ""
        if filterConditions:
            conditionCount = 0
            # Enumerate over all conditions
            for condition in filterConditions:
                # Unwrap the tuple containing the WHERE condition
                filterColumn, filterValue = condition
                # Check if condition is valid
                if (filterColumn is not None) & (filterValue is not None):
                    # Select the correct connector string
                    connectorStr = "WHERE" if (conditionCount == 0) else "AND"
                    # Enclose filter value in single quotes if it is a string column
                    sqlString = (
                        filterValue
                        if isQueryCondition
                        else self.getSQLString(filterValue=filterValue)
                    )
                    conditionStr = f"IN ({sqlString})"
                    query += f" {connectorStr} {filterColumn} {conditionStr}"
                    conditionCount += 1
        return query

    # Function that returns the properly formatted string
    # for adding as a condition to the SQL WHERE clause
    def getSQLString(self, filterValue):
        def addSingleQuotes(val):
            return isinstance(val, str) or isinstance(val, datetime)

        def handleDateValues(val):
            if isinstance(val, list):
                if isinstance(val[0], datetime):
                    val = [self.getSQLDate(v) for v in val]
            elif isinstance(val, datetime):
                val = self.getSQLDate(val)
            return val

        sqlString = None
        isList = isinstance(filterValue, list)
        addQuotes = (isList and addSingleQuotes(filterValue[0])) or (
            addSingleQuotes(filterValue)
        )
        filterValue = handleDateValues(filterValue)
        if isList:
            listConnector = "','" if addQuotes else ","
            filterValue = listConnector.join(list(map(str, filterValue)))
        sqlString = f"'{filterValue}'" if addQuotes else filterValue
        return sqlString

    # Function to convert datetime variable into an SQL data
    def getSQLDate(self, dateVal: datetime) -> str:
        return dateVal.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def getSQLVariableType(self, colType) -> str:
        if (colType == np.int32) or (colType == np.int64) or (colType == "Int64"):
            sqlType = "INT"
        elif (
            (colType == np.float32) or (colType == np.float64) or (colType == "Float64")
        ):
            sqlType = "DECIMAL(10, 4)"
        elif colType == bool:
            sqlType = "BIT"
        elif (colType == "datetime64[ns]") or (colType == np.datetime64):
            sqlType = "DATETIME"
        else:
            sqlType = "NVARCHAR(256)"
        return sqlType

    # -------------------------------------------------------------------------#
    # ----------------------- SQL BULK OPERATION USING BCP --------------------#

    def execSelectWithBCP(self, query: str, columnList: list) -> pd.DataFrame:
        if self.config["bcpToggle"] == 0:
            return self.execSelectQuery(query=query)

        resultsTmpFile = self.getBCPTempFile()
        try:
            bcpCommand = f'BCP "{query}" queryout "{resultsTmpFile}" -c {self.getBCPConnectionString()}'
            subprocess.run(
                bcpCommand, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
            )
            results = None
            if os.path.isfile(resultsTmpFile) and os.path.getsize(resultsTmpFile) > 0:
                results = pd.read_csv(resultsTmpFile, sep="\t", header=None)
                results.columns = columnList
        except Exception as err:
            self.logger.error(
                f"Error exporting BCP query results: {query} to {resultsTmpFile}."
            )
            self.logger.error(err)
        finally:
            if os.path.exists(resultsTmpFile):
                os.remove(resultsTmpFile)

        return results

    def execInsertWithBCP(self, insertData: pd.DataFrame, tableName: str) -> bool:
        if self.utils.isNullDataFrame(insertData):
            self.logger.warn("Empty dataframe found - nothing to insert.")
            return True

        if not self.checkTableExists(
            tableName=tableName, schemaName=self.defaultSchema
        ):
            self.logger.warn(f"Insert statement failed - {tableName} does not exist.")
            return False

        dataTmpFile = self.getBCPTempFile()
        fmtTmpFile = self.getBCPTempFile(prefix="fmt", ext="fmt")
        try:
            bcpFmtCommand = f"bcp [{self.defaultSchema}].[{tableName}] format nul -f {fmtTmpFile} -c {self.getBCPConnectionString()}"
            subprocess.run(
                bcpFmtCommand, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
            )
            self.modifyFmtFile(fmtFile=fmtTmpFile, tableName=tableName)

            insertData.to_csv(
                dataTmpFile, sep="\t", float_format="%.4f", header=False, index=False
            )
            bcpCommand = f'bcp [{self.defaultSchema}].[{tableName}] in "{dataTmpFile}" -f "{fmtTmpFile}" {self.getBCPConnectionString()}'
            subprocess.run(
                bcpCommand, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
            )
        except Exception:
            self.logger.error(
                f"Error importing csv using BCP from {dataTmpFile} to {tableName}."
            )
        finally:
            if os.path.exists(dataTmpFile):
                os.remove(dataTmpFile)
            if os.path.exists(fmtTmpFile):
                os.remove(fmtTmpFile)

        return True

    def getBCPTempFile(self, prefix="tmp", ext="csv") -> str:
        tmpDirPath = tempfile.gettempdir()
        if not os.path.exists(tmpDirPath):
            os.makedirs(tmpDirPath)
        timeStamp = self.utils.getLocalISTTime().strftime("%Y%m%d%H%M%S%f")
        tmpFile = os.path.join(
            tmpDirPath,
            f"{prefix}{timeStamp}.{ext}",
        )
        return tmpFile

    def getBCPConnectionString(self) -> str:
        trustedCnxn = (
            True
            if (self.config["uid"] is None or len(self.config["uid"]) == 0)
            else False
        )
        authentication = (
            "-T"
            if trustedCnxn
            else f'-U "{self.config["uid"]}" -P "{self.config["pwd"]}"'
        )
        cnxnString = f'-a 65535 -S "{self.config["server"]}" -d "{self.config["database"]}" {authentication} '

        return cnxnString

    def modifyFmtFile(self, fmtFile: str, tableName: str):
        with open(fmtFile, "r") as file:
            fmtLines = file.readlines()
            newFmtLines = []
            for fmtLine in fmtLines:
                if f"{tableName}Id" in fmtLine:
                    fmtValues = fmtLine.split()
                    fmtValues[2] = "0"
                    fmtValues[3] = "0"
                    fmtValues[4] = '""'
                    fmtValues[5] = "0"
                    fmtLine = "    ".join(fmtValues) + "\n"
                newFmtLines.append(fmtLine)
        with open(fmtFile, "w") as file:
            file.writelines(newFmtLines)
        return
