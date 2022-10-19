import pandas as pd
import numpy as np
from datetime import datetime
import logging


class Data:

    db = None
    utils = None
    logger = None

    def __init__(self, db, utils):
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.utils = utils
    
    # -------------------------------------------------- Content Data ------------------------------------------------ #

    # Function to get the list of CourseIds that are active for signup
    def getActiveCourseIds(self, onlyQuery: bool = False) -> tuple:

        activeCourses, query = self.db.selectWithWhere(
            tableName="CourseView",
            columnList=["CourseId"],
            filterColumn="IsActiveForSignup",
            filterValue=1,
            onlyQuery=onlyQuery,
        )

        if onlyQuery:
            return None, query

        activeCourseIds = list(activeCourses["CourseId"])
        if len(activeCourseIds) == 0:
            self.logger.error("No active courses found.")
        return activeCourseIds, query

    # Function that returns a dictionary of all content ids and names
    def getContentNames(self) -> dict:
        contentDict = dict()
        contentTypes = ["Course", "Class", "Subject", "Chapter"]
        for content in contentTypes:
            data, _ = self.db.selectWithWhere(
                tableName=f"{content}View",
                schemaName="new",
                columnList=[f"{content}Id", f"{content}Name"],
                filterColumn="IsActive",
                filterValue=1,
            )
            data.dropna(inplace=True)
            contentDict[content] = data
        return contentDict

    # Function to return the CourseChapterIds for a given list of
    # courses/classes/subjects/chapters
    def getCourseChapters(
        self,
        content: object,
        columnList: list = None,
        includeNames: bool = False,
        onlyQuery: bool = False,
    ) -> (pd.DataFrame, str):

        if (content.courseIds is not None) and (len(content.courseIds) == 0):
            self.logger.info(
                "Empty list of courseIds provided. Data for all the courses will be returned."
            )
            content.courseIds = None

        # Select the matching CourseChapterIds from CourseChapterView
        courseChapters, baseQuery = self.db.selectWithMultipleWheres(
            tableName="CourseChapter",
            columnList=columnList,
            filterConditions=[
                ("CourseId", content.courseIds),
                ("ClassId", content.classIds),
                ("SubjectId", content.subjectIds),
                ("ChapterId", content.chapterIds),
            ],
            onlyQuery=onlyQuery,
        )

        if includeNames:
            contentNames = self.getContentNames()
            for content in contentNames:
                if f"{content}Id" in courseChapters:
                    courseChapters = courseChapters.join(
                        contentNames[content].set_index(f"{content}Id"),
                        on=f"{content}Id",
                        how="inner",
                    )

        if (not onlyQuery) and self.utils.isNullDataFrame(courseChapters):
            self.logger.warn(
                f"No chapters found for CourseId={content.courseIds} and ChapterIds={content.chapterIds}"
            )
            return None, baseQuery

        return courseChapters, baseQuery  

    # Function to return the CourseKSCs for a given list of CourseChapterIds
    def getKSCsForCourseChapters(
        self,
        courseChapters: pd.DataFrame,
        columnList: list = None,
        includeKSCDetails: bool = False,
        onlyQuery: bool = False,
    ) -> pd.DataFrame:
        # Use the CourseChapterIds to get the list of applicable KSCs
        courseChapterIds = list(courseChapters["CourseChapterId"])

        KSCCluster,_=self.db.selectWithWhere(
            tableName="KSCCluster",
            columnList=columnList,
            filterColumn="CourseChapterId",
            filterValue=courseChapterIds,
            onlyQuery=False,
        )
        
        courseKSCs,query=self.db.selectWithWhere(
            tableName="KSCClusterKSC",
            columnList=columnList,
            filterColumn="KSCClusterId",
            filterValue=list(KSCCluster["KSCClusterId"]),
            onlyQuery=False
        )
        if onlyQuery:
            return None, query

        if self.utils.isNullDataFrame(courseKSCs):
            self.logger.warn(f"No KSCs found for CourseChapterIds={courseChapterIds}")
            return None, None

        if includeKSCDetails:
            kscDetails, _ = self.db.selectWithWhere(
                tableName="KSCView",
                columnList=["KSCId", "KSCText", "KSCDiagramURL"],
                filterColumn="KSCId",
                filterValue=list(courseKSCs["KSCId"]),
                onlyQuery=False,
            )
            courseKSCs = courseKSCs.join(
                kscDetails.set_index("KSCId"), on="KSCId", how="inner"
            )

        return courseKSCs

    # Function to fetch existing KSCClusterKSC mappings from DB
    def getKSCClusterKSCs(
        self, tableName, addClusterName: bool = False, onlyQuery: bool = False
    ) -> (pd.DataFrame, str):
        kscClusterKSCs, query = self.db.selectTable(
            tableName=tableName,
            schemaName="dbo",
            columnList=["KSCClusterId", "KSCId", "DisplayRank", "IsVisible"],
            onlyQuery=onlyQuery,
        )

        if onlyQuery:
            return None, query

        if self.utils.isNullDataFrame(kscClusterKSCs):
            self.logger.warn("No KSCClusterKSCs found in DB.")
            return None, query

        if addClusterName:
            kscClusters, _ = self.db.selectTable(
                tableName="KSCCluster",
                schemaName="new",
                columnList=["KSCClusterId, KSCClusterName, CourseChapterId"],
                onlyQuery=False,
            )

            kscClusterKSCs = kscClusterKSCs.join(
                kscClusters.set_index("KSCClusterId"), on="KSCClusterId", how="left"
            )

        return kscClusterKSCs, query

    # Function to return the CourseKSCs for a given list of CourseChapterIds
    def getCourseKSCsByQuery(
        self, courseChaptersQuery: str, columnList: list = None
    ) -> pd.DataFrame:
        # Use the CourseChapterIds to get the list of applicable KSCs
        courseKSCs, _ = self.db.selectWithSQL(
            tableName="CourseKSC",
            columnList=columnList,
            filterColumn="CourseChapterId",
            filterQuery=courseChaptersQuery,
            onlyQuery=False,
        )

        if self.utils.isNullDataFrame(courseKSCs):
            self.logger.warn(f"No KSCs found for query={courseChaptersQuery}")
            return None

        return courseKSCs

    # Function to get the list of questions that are excluded from specific
    # coursechapters in the CourseChapterQuestionExclusion table
    def getExcludedQuestions(self, courseChapters: pd.DataFrame):
        excludedQuestions, _ = self.db.selectWithWhere(
            tableName="CourseChapterQuestionExclusion",
            filterColumn="CourseChapterId",
            filterValue=list(courseChapters["CourseChapterId"]),
            onlyQuery=False,
        )
        if self.utils.isNullDataFrame(excludedQuestions):
            return None
        return excludedQuestions

    # Function to return the QuestionIds for a given list of CourseKSCs
    def getQuestionsForCourseChapters(
        self,
        courseChapters: pd.DataFrame,
        columnList: list = None,
        onlyPrimary: bool = False,
        includeMetrics: bool = False,
        metricsColumns: list = None,
    ) -> pd.DataFrame:
        _, baseQuery = self.getKSCsForCourseChapters(
            courseChapters=courseChapters,  onlyQuery=True
        )
        courseKSCQuery = self.db.setSelectColumns(query=baseQuery, columnList=["KSCId"])
        # Use the KSCIds to get the list of valid questions from
        # QuestionKSCView where IsPrimaryKSC is true
        questions, baseQuery = self.db.selectWithMultipleSQLs(
            tableName="QuestionKSCView",
            filterQueries=[("KSCId", courseKSCQuery)],
            columnList=["QuestionId", "KSCId","IsPrimaryKSC"],
            onlyQuery=False,
        )
        questionsQuery = self.db.setSelectColumns(
            query=baseQuery, columnList=["QuestionId"]
        )
        # Remove excluded questions based on the CourseChapterQuestionExclusion table
        excludedQuestions = self.getExcludedQuestions(courseChapters=courseChapters)
        if not self.utils.isNullDataFrame(excludedQuestions):
            questions = questions.loc[
                ~questions["QuestionId"].isin(excludedQuestions["QuestionId"])
            ]

        # Add details for each question from QuestionView
        questionDetails, _ = self.db.selectWithMultipleSQLs(
            tableName="QuestionView",
            columnList=columnList,
            filterQueries=[
                ("QuestionId", questionsQuery),
                ("IsSuspended", 0),
            ],
        )

        if self.utils.isNullDataFrame(questionDetails):
            self.logger.warn(f"No question details found for given CourseChapters.")
            return None

        # Add KSC details for each question from KSCView
        kscDetails, _ = self.db.selectWithSQL(
            tableName="KSCView",
            columnList=["KSCId", "KSCText", "KSCDiagramURL"],
            filterColumn="KSCId",
            filterQuery=courseKSCQuery,
        )

        if self.utils.isNullDataFrame(kscDetails):
            self.logger.warn(f"No KSC details found for given CourseChapters.")
            return None

        # Join questionDetails and kscDetails to questions data
        questions = questions.merge(questionDetails, on="QuestionId", how="inner")
        questions = questions.merge(kscDetails, on="KSCId", how="inner")

        if includeMetrics:
            questionMetrics, _ = self.db.selectWithMultipleSQLs(
                tableName="QuestionMetrics",
                filterQueries=[("QuestionId", questionsQuery), ("IsParentMetric", 0)],
                columnList=["QuestionId", "CourseChapterId"] + metricsColumns,
            )
            questionMetrics = questionMetrics.merge(
                courseChapters[["CourseChapterId"]],
                on="CourseChapterId",
                how="inner",
            )
            questions = questions.merge(questionMetrics, on="QuestionId", how="left")

        questions.sort_values(by=[ "QuestionId"], inplace=True)
        questions.reset_index(drop=True, inplace=True)

        return questions

    # Function to return the QuestionIds for a given list of CourseKSCs
    def getQuestionsForCourseKSCs(
        self,
        courseKSCs: pd.DataFrame,
        columnList: list = None,
        onlyPrimary: bool = False,
    ) -> pd.DataFrame:
        # Set the filter conditions for questions
        kscIds = list(courseKSCs["KSCId"])
        filterConditions = [("KSCId", kscIds, False)]
        if onlyPrimary:
            filterConditions += [("IsPrimaryKSC", 1, False)]
        # Use the KSCIds to get the list of valid questions from
        # QuestionKSCView where IsPrimaryKSC is true
        questions, _ = self.db.selectMultipleWheres(
            tableName="QuestionKSCView",
            columnList=columnList,
            filterConditions=[("KSCId", kscIds), ("IsPrimaryKSC", 1)],
            onlyQuery=False,
        )

        if self.utils.isNullDataFrame(questions):
            self.logger.warn(f"No questions found for KSCIds={kscIds}")
            return None

        return questions

    # Function to return the QuestionKSCReview data for a given list of
    # QuestionIds and KSCIds
    def getQuestionKSCReviews(
        self,
        dbTableName: str,
        courseChapters: pd.DataFrame,
        columnList: list = None,
    ) -> pd.DataFrame:

        _, baseQuery = self.getKSCsForCourseChapters(
            courseChapters=courseChapters, onlyQuery=True
        )
        kscQuery = self.db.setSelectColumns(query=baseQuery, columnList=["KSCId"])

        _, baseQuery = self.db.selectWithMultipleSQLs(
            tableName="QuestionKSCView",
            filterQueries=[("KSCId", kscQuery), ("IsPrimaryKSC", 1)],
            onlyQuery=True,
        )
        questionQuery = self.db.setSelectColumns(
            query=baseQuery, columnList=["QuestionId"]
        )

        # Use the QuestionIds and KSCIds to get the list of existing
        # QuestionKSCReviews from DB
        questionReviews, _ = self.db.selectWithMultipleSQLs(
            tableName=dbTableName,
            columnList=columnList,
            filterQueries=[("QuestionId", questionQuery), ("KSCId", kscQuery)],
        )

        if self.utils.isNullDataFrame(questionReviews):
            self.logger.debug(
                f"No QuestionReviews found for courseChapters={courseChapters}"
            )
            return None

        return questionReviews

    # ----------------------------------------------- KSC Mapping Data ------------------------------------------------ #

    def getKSCClustersforKSCs(
        self,
        allKSCs: pd.DataFrame,
        allCourseChapters: pd.DataFrame,
        columnList: list = None,
    ) -> pd.DataFrame:

        kscIds = list(allKSCs["KSCId"])
        courseKSCs, _ = self.db.selectWithWhere(
            tableName="CourseKSC",
            columnList=["KSCId", "CourseChapterId"],
            filterColumn="KSCId",
            filterValue=kscIds,
            onlyQuery=False,
        )

        if self.utils.isNullDataFrame(courseKSCs):
            self.logger.warn(f"No data found for query={kscIds}")
            return None

        kscClusters, _ = self.db.selectWithWhere(
            tableName="KSCCluster",
            columnList=["CourseChapterId", "KSCClusterId", "KSCClusterName"],
            filterColumn="CourseChapterId",
            filterValue=list(courseKSCs["CourseChapterId"]),
            onlyQuery=False,
        )

        allCoursesClusters = courseKSCs.join(
            kscClusters.set_index("CourseChapterId"), on="CourseChapterId", how="inner"
        )

        allCoursesClusters = allCoursesClusters.join(
            allCourseChapters[["CourseChapterId", "CourseId", "CourseName"]].set_index(
                "CourseChapterId"
            ),
            on="CourseChapterId",
            how="inner",
        )
        return allCoursesClusters

    # Function to return the KSCCluster data for a given list of KSCIds
    def getKSCClusterMappings(
        self,
        courseChapters: pd.DataFrame,
        columnList: list = None,
    ) -> pd.DataFrame:
        return None

    def getChaptersRatingReviews(
        self,
        dbTableName: str,
        courseChapters: pd.DataFrame,
        columnList: list = None,
    ) -> pd.DataFrame:
        return None

    def getKSCClusterReviews(
        self,
        dbTableName: str,
        courseChapters: pd.DataFrame,
        columnList: list = None,
    ) -> pd.DataFrame:
        return None

    def getKSCClustersforKSCIds(
        self,
        allKSCs: pd.DataFrame,
        columnList: list = None,
        onlyQuery: bool = False,
    ) -> pd.DataFrame:

        kscIds = list(allKSCs["KSCId"])
        courseChapterId = list(allKSCs["CourseChapterId"])
        courseKSCs, _ = self.db.selectWithWhere(
            tableName="CourseKSC",
            columnList=["CourseChapterId", "KSCId"],
            filterColumn="courseChapterId",
            filterValue=courseChapterId,
            onlyQuery=False,
        )
        if self.utils.isNullDataFrame(courseKSCs):
            self.logger.warn(f"No data found for query={kscIds}")
            return None

        kscclustersId, _ = self.db.selectWithWhere(
            tableName="KSCClusterKSC",
            columnList=["KSCId", "KSCClusterId"],
            filterColumn="KSCId",
            filterValue=kscIds,
            onlyQuery=False,
        )
        kscClustersName, _ = self.db.selectWithWhere(
            tableName="KSCCluster",
            columnList=["KSCClusterId", "KSCClusterName"],
            filterColumn="KSCClusterId",
            filterValue=list(kscclustersId["KSCClusterId"]),
            onlyQuery=False,
        )

        kscClusterMapping = courseKSCs.merge(
            kscclustersId,
            on="KSCId",
            how="inner",
        ).merge(kscClustersName, on="KSCClusterId", how="inner")

        return kscClusterMapping

    # Function to return the CourseKSCs for a given list of CourseChapterIds
    def getKSCsForAllCourseChapters(
        self,
        courseChapters: pd.DataFrame,
        columnList: list = None,
        includeKSCDetails: bool = False,
        onlyQuery: bool = False,
    ) -> pd.DataFrame:
        # Use the CourseChapterIds to get the list of applicable KSCs
        courseChapterIds = list(courseChapters["CourseChapterId"])
        courseKSCs, baseQuery = self.db.selectWithWhere(
            tableName="CourseKSC",
            columnList=columnList,
            filterColumn="CourseChapterId",
            filterValue=courseChapterIds,
            onlyQuery=False,
        )
        if onlyQuery:
            return None, baseQuery

        if self.utils.isNullDataFrame(courseKSCs):
            self.logger.warn(f"No KSCs found for CourseChapterIds={courseChapterIds}")
            return None, baseQuery

        kscQuery = self.db.setSelectColumns(query=baseQuery, columnList=["KSCId"])
        if includeKSCDetails:
            kscDetails, _ = self.db.selectWithSQL(
                tableName="KSCView",
                columnList=["KSCId", "KSCText", "KSCClusterId", "KSCDiagramURL"],
                filterColumn="KSCId",
                filterQuery=kscQuery,
                onlyQuery=False,
            )
            courseKSCs = courseKSCs.join(
                kscDetails.set_index("KSCId"), on="KSCId", how="inner"
            )

        courseKSCs.reset_index(inplace=True, drop=True)

        return courseKSCs, baseQuery
