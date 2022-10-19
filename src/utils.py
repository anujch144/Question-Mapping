import os
import numpy as np
import pandas as pd
import pytz
from datetime import datetime


class Utils:
    def __init__(self):
        pass

    # Function to print time taken by a particular process, given the start and end times
    def printElapsedTime(self, startTime: datetime, endTime: datetime) -> None:
        elapsedTime = endTime - startTime
        print("-- Process time = %.2f seconds --" % (elapsedTime))

    def jsonToPython(self, val):
        if val == "null":
            return None
        if val == "false":
            return False
        if val == "true":
            return True
        return val

    def dataFrameToJson(self, df: pd.DataFrame) -> str:
        if self.isNullDataFrame(df):
            return None
        return df.to_json(orient="split")
    
    def jsonToDataFrame(self, jsonString: str) -> pd.DataFrame:
        if jsonString is None:
            return None
        return pd.read_json(jsonString, orient="split")
    
    # Function to check if a dataframe variable is null or empty
    def isNullDataFrame(self, df: pd.DataFrame) -> bool:
        if df is None:
            return True
        if not (isinstance(df, pd.DataFrame)):
            return True
        if isinstance(df, pd.DataFrame) and df.empty:
            return True
        return False

    # Function to check if a list variable is null or empty
    def isNullList(self, inputList: list) -> bool:
        if inputList is None:
            return True
        if not (isinstance(inputList, list)):
            return True
        if all(item is None for item in inputList):
            return True
        return False
        
    # Function to flatten the column headers of a multi-level column index
    def flattenMultiLevelColumns(
        self, df: pd.DataFrame, sep: str = "_"
    ) -> pd.DataFrame:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [sep.join(col).strip(sep) for col in df.columns.values]
        return df

    # Function to check if a variable is numeric or not
    def isNumeric(self, val) -> bool:
        return isinstance(val, (int, float, complex)) and not isinstance(val, bool)

    # Function to convert column to int
    def convertToInt(self, df: pd.DataFrame, columnName: str) -> pd.DataFrame:
        df[columnName] = np.round(
            pd.to_numeric(df[columnName], errors="coerce"), 0
        ).astype("Int64")
        return df

    # Function to convert column to float
    def convertToFloat(
        self, df: pd.DataFrame, columnName: str, maxPrecision: int = 4
    ) -> pd.DataFrame:
        df[columnName] = pd.to_numeric(df[columnName], errors="coerce").astype(
            "Float64"
        )
        df[columnName] = np.round(df[columnName], decimals=maxPrecision)
        return df

    # Function to print numbers with proper formatting
    def getFormattedNumber(self, num, isPct: bool = False, decimals: int = 0) -> str:
        # Default formatting is comma separated numbers
        formatString = "{0:,." + str(decimals) + "f}"
        # If percent formatting is required
        if isPct:
            num = num * 100
            formatString = "{:." + str(decimals) + "f}%"
        return formatString.format(num)

    # Add a Week of the Year column to a dataframe for a given Date column
    def addWeekOfYear(
        self, df: pd.DataFrame, dateColumn: str, outputColumn: str = "WeekYear"
    ) -> pd.DataFrame:
        df[outputColumn] = df[dateColumn].apply(
            lambda x: str(x.isocalendar()[1]) + "-" + str(x.year)
        )
        return df

    # Function to multiply a scalar value  to each element of a tuple
    def multiplyTuple(self, tup: tuple, multiplier: int) -> list:
        return [i * multiplier for i in tup]

    # Function that returns local time in IST
    def getLocalISTTime(self) -> datetime:
        istTimeZone = pytz.timezone("Asia/Kolkata")
        localTime = datetime.now(istTimeZone)
        localTime = localTime.replace(tzinfo=None)
        return localTime

    # Function to recursively get list of files in a directory
    # filtered by a given extension
    def listFilesInFolder(
        self,
        folderPath: str,
        filePrefix: str = None,
        fileExt: str = None,
        includePath: bool = False,
    ) -> list:
        fileList = list()
        for root, dirs, files in os.walk(folderPath):
            for f in files:
                if ((filePrefix is None) or f.startswith(filePrefix)) and (
                    (fileExt is None) or f.endswith(f".{fileExt}")
                ):
                    fpath = os.path.join(root, f) if includePath else f
                    fileList.append(fpath)

        return fileList

    # Functions that return the appropriate column name for a particular metric type
    # by adding suffixes to a variable name
    def addColumnSuffix(
        self, inputVar: str, varType: str, config: dict, isCut: bool
    ) -> str:
        if varType == "trend":
            return inputVar[0].upper() + inputVar[1:]
        configHeading = varType + ("Cut" if isCut else "")
        return inputVar.title() + (config[configHeading])

    def scoreColumn(self, inputVar: str, config: dict) -> str:
        return self.addColumnSuffix(
            inputVar=inputVar, varType="score", config=config, isCut=False
        )

    def rankColumn(self, inputVar: str, config: dict) -> str:
        return self.addColumnSuffix(
            inputVar=inputVar, varType="rank", config=config, isCut=False
        )
