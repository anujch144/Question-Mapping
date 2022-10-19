import pandas as pd
import numpy as np
from sklearn import preprocessing
from datetime import datetime, timedelta
import scipy.signal

import logging


class Calculations:

    utils = None
    logger = None

    def __init__(self, utils):
        self.logger = logging.getLogger(__name__)
        self.utils = utils

    # Function to compute sigmoid value (1 / (1 + e ^ (-x)))
    # Useful for supressing unbound values to a fixed range
    def sigmoid(self, x: float, k: float = 1) -> float:
        return (2 / (1 + np.exp(-x / k))) - 1

    # Function to compute any metric ratio - it checks for the
    # denominator count and if less than some threshold value,
    # function returns None. This ensures metrics are computed only
    # if we have sufficient observations
    def computeRatio(
        self, num: list, den: list, checkCount: bool = False, minCount: int = 20
    ) -> list:
        ratios = np.where(
            ((den is None) | (den == 0) | (checkCount & (den < minCount))),
            None,
            num / den,
        )
        ratios = ratios.astype(float)
        return ratios

    # Function to compute Accuracy = e^(TotalCorrect / TotalAttempted)
    def computeAccuracy(
        self,
        correct: list,
        attempts: list,
        checkCount: bool = False,
        minCount: int = 20,
    ) -> list:
        accuracy = self.computeRatio(
            num=correct,
            den=attempts,
            checkCount=checkCount,
            minCount=minCount,
        )
        accuracy = np.exp(accuracy)
        return accuracy

    # Function to compute Span = Log(1 + (TotalAttempted / TotalQuestions))
    def computeSpan(self, attempts, attemptsMedian) -> float:
        span = self.computeRatio(
            num=attempts,
            den=attemptsMedian,
        )
        span = np.where(span is None, None, self.sigmoid(np.log(1 + span)))
        return span

    # Function to compute Speed = Tanh(Log(ParentTimeMedian / QuesTimeMedian))
    def computeSpeed(
        self,
        quesTime: list,
        parentTime: list,
        attempts: list,
        checkCount: bool = False,
        minCount: int = 20,
    ) -> list:
        speed = self.computeRatio(num=parentTime, den=quesTime)
        speed = np.where(
            (speed is None) | (checkCount & (attempts < minCount)),
            None,
            self.sigmoid(np.log(1 + speed)),
        )
        return speed

    # Function to compute Velocity or Expertise = (Accuracy + Span + Speed)
    def computeVelocity(
        self,
        accuracy: list,
        speed: list,
        span: list = None,
    ) -> list:
        return accuracy + speed + (span if span is not None else 0)
    
    # Function that computes Accuracy, Span, Speed and Velocity
    def computeStatisticalMetrics(
        self,
        metricsData: pd.DataFrame,
        attemptsColumn: str = "Attempted",
        correctColumn: str = "Correct",
        quesTimeColumn: str = "QuesTimeMedian",
        attemptsMedianColumn: str = "AttemptsMedian",
        parentTimeColumn: str = "ParentTimeMedian",
        includeSpan: bool = True,
        checkCount: bool = False,
        minCount: int = 20,
    ) -> pd.DataFrame:

        # Compute Accuracy = Correct / Attempted
        metricsData["Accuracy"] = self.computeAccuracy(
            correct=metricsData[correctColumn],
            attempts=metricsData[attemptsColumn],
            checkCount=checkCount,
            minCount=minCount,
        )

        # Compute Span = Attempted / AttemptsMedian
        if includeSpan:
            metricsData["Span"] = self.computeSpan(
                attempts=metricsData[attemptsColumn],
                attemptsMedian=metricsData[attemptsMedianColumn],
            )

        # Compute Speed = ParentMedianTime / QuesMedianTime
        metricsData["Speed"] = self.computeSpeed(
            quesTime=metricsData[quesTimeColumn],
            parentTime=metricsData[parentTimeColumn],
            attempts=metricsData[attemptsColumn],
            checkCount=checkCount,
            minCount=minCount,
        )

        # Compute Velocity = (Accuracy + Span + Speed)
        span = metricsData["Span"] if includeSpan else None
        metricsData["Velocity"] = self.computeVelocity(
            accuracy=metricsData["Accuracy"], speed=metricsData["Speed"], span=span
        )
                
        return metricsData
    
    # Scale a given set of values from lower limit to upper limit
    # using Scikit Learn's MinMaxScaler
    def applyMinMaxScaler(
        self, inputValues: list, lowerLimit: float = 0, upperLimit: float = 1
    ) -> list:
        minMaxScaler = preprocessing.MinMaxScaler(
            feature_range=(lowerLimit, upperLimit)
        )
        scaledValues = minMaxScaler.fit_transform(inputValues)
        return scaledValues

    # Scale a given set of values with mean 0 and standard deviation 1
    # using Scikit Learn's StandardScaler
    def applyStandardScaler(self, inputValues: list) -> list:
        standardScaler = preprocessing.StandardScaler()
        scaledValues = standardScaler.fit_transform(inputValues)
        return scaledValues

    def calculateColumnZScores(
        self,
        df: pd.DataFrame,
        groupColumns: list,
        scoreColumn: str,
        outputColumn: str = None,
        lowerLimit: float = 0,
        upperLimit: float = 1,
        scaleInput: bool = False,
        logTransform: bool = False,
        scaleOutput: bool = False,
    ) -> pd.DataFrame:
        if not isinstance(groupColumns, list):
            groupColumns = [groupColumns]
        if outputColumn is None:
            outputColumn = scoreColumn + "ZScore"
        if self.utils.isNullDataFrame(df):
            return df
    
        df.sort_values(by=groupColumns + [scoreColumn], ascending=True, inplace=True)
        zscores = (
            df[groupColumns + [scoreColumn]]
            .groupby(by=groupColumns, as_index=False)
            .apply(
                lambda x: self.calculateZScores(
                    x[[scoreColumn]].values,
                    lowerLimit=lowerLimit,
                    upperLimit=upperLimit,
                    scaleInput=scaleInput,
                    logTransform=logTransform,
                    scaleOutput=scaleOutput,
                )
            )
        )
        zscores = [zs[0] for zsgroup in zscores for zs in zsgroup]
        df[outputColumn] = zscores
        
        return df

    def calculateColumnPercentiles(
        self,
        df: pd.DataFrame,
        groupColumns: list,
        scoreColumn: str,
        outputColumn: str = None,
    ) -> pd.DataFrame:
        if not isinstance(groupColumns, list):
            groupColumns = [groupColumns]
        if outputColumn is None:
            outputColumn = scoreColumn + "Pct"
        if self.utils.isNullDataFrame(df):
            return df
        
        df.sort_values(by=groupColumns + [scoreColumn], ascending=True, inplace=True)
        df[outputColumn] = df.groupby(groupColumns)[scoreColumn].rank(pct=True, method="average")
        return df

    # Function to normalize data and compute z-scores
    def calculateZScores(
        self,
        inputValues: list,
        lowerLimit: float = 0,
        upperLimit: float = 1,
        scaleInput: bool = False,
        logTransform: bool = False,
        scaleOutput: bool = False,
    ) -> list:
        # Transform the inputValues using the MinMaxScaler
        # This is required in case we are going to do a log transform
        # Using 1 and 2 as the limits, we can avoid log(0) and log(-1) errors
        if (scaleInput and logTransform and (lowerLimit <= 0)) or (
            (not scaleInput) and logTransform and (min(inputValues) <= 0)
        ):
            self.logger.error(
                "Invalid input values and/or lower limit provided for log transform."
            )
            return None

        self.logger.debug(inputValues)
        scaledValues = (
            self.applyMinMaxScaler(
                inputValues=inputValues,
                lowerLimit=lowerLimit,
                upperLimit=upperLimit,
            )
            if scaleInput
            else inputValues
        )
        # If input is one-sided, transform the data to a log scale
        transformedValues = np.log(scaledValues) if logTransform else scaledValues
        # Transform the scaled data using the StandardScaler
        normalValues = self.applyStandardScaler(inputValues=transformedValues)
        # Scale output if required
        outputValues = (
            self.applyMinMaxScaler(
                inputValues=normalValues,
                lowerLimit=lowerLimit,
                upperLimit=upperLimit,
            )
            if scaleOutput
            else normalValues
        )

        self.logger.debug(outputValues)

        return outputValues

    # Function to normalize the Velocity column for each question
    # grouped by ChapterId and compute ZScores for the questions
    # Create bins for questions within a content category (e.g. Chapters)
    # based on question difficulty - we will use ZScore of the global velocity metric
    # as an indicator of difficulty
    def categorizeQuestionsOnDifficulty(
        self,
        questions: pd.DataFrame,
        stdDevCuts: list = None,
        binLabels: list = None,
    ) -> pd.DataFrame:
        # By default we will create 5 difficulty levels of questions
        # Basic/ Easy/ Medium/ Tough/ Hard
        # Lower VelocityZScore implies higher difficulty
        if stdDevCuts is None:
            stdDevCuts = [-np.inf, -1.3, -0.3, 0.3, 1.3, np.inf]
        if binLabels is None:
            binLabels = [
                "5-Challenging",
                "4-Tough",
                "3-Intermediate",
                "2-Normal",
                "1-Easy",
            ]

        # Normalize the Velocity column for each question grouped by ChapterId
        categoryColumns = ["CourseChapterId", "QuestionId"]
        questionDifficulty = questions[categoryColumns + ["Velocity"]].copy()

        questionDifficulty.sort_values(
            by=["CourseChapterId", "Velocity"], ascending=[True, True], inplace=True
        )
        zscores = (
            questionDifficulty[["CourseChapterId", "Velocity"]]
            .groupby(by="CourseChapterId", as_index=False)
            .apply(
                lambda x: self.calculateZScores(
                    x[["Velocity"]].values, logTransform=True
                )
            )
        )

        zscores = [
            zs[0] for zsgroup in zscores for zs in zsgroup
        ]  # This returns a flattened 1-d array of scores

        # Assign question zscores to the dataframe
        questionDifficulty["VelocityZScore"] = zscores

        # Compute difficulty bins based on zscores
        questionDifficulty["DifficultyLevel"] = questionDifficulty.groupby(
            "CourseChapterId", as_index=False
        )[["VelocityZScore"]].transform(
            lambda x: pd.cut(
                x,
                bins=stdDevCuts,
                labels=binLabels,
            )
        )

        # Add Zscore and difficulty columns to the original dataframe
        questions = questions.join(
            questionDifficulty[
                categoryColumns + ["VelocityZScore", "DifficultyLevel"]
            ].set_index(categoryColumns),
            on=categoryColumns,
            how="left",
        )

        return questions

    # Function that takes as input a history of metrics for multiple users across
    # multiple dates and then fills the gaps for users who haven't practiced on a
    # given date and hence don't have an entry in the history table
    def fillMetricsHistoryGaps(
        self,
        metricsHistory: pd.DataFrame,
        categoryColumns: list,
        metricsColumns: list = None,
    ) -> pd.DataFrame:
        
        def cleanDates(df):
            df = df.sort_values(by=keyColumns, ascending=True)
            df = df.groupby(keyColumns + categoryColumns).head(1)
            df["UpdatedOn"] = pd.to_datetime(df["UpdatedOn"]).dt.date
            return df
        
        keyColumns = ["UserId", "UpdatedOn"]
        # If metricsColumns is None, we will use all the columns in the dataframe
        # that are not keyColumns and categoryColumns
        if metricsColumns is None:
            metricsColumns = [
                col
                for col in metricsHistory.columns.tolist()
                if col not in (keyColumns + categoryColumns)
            ]
        metricsHistory = cleanDates(df=metricsHistory)

        # Sort the dataframe by UserId and UpdatedOn and convert UpdatedOn to date
        historyDates = pd.DataFrame(
            pd.date_range(
                metricsHistory["UpdatedOn"].min(),
                metricsHistory["UpdatedOn"].max(),
                freq="d",
            ),
            columns=["UpdatedOn"],
        )
        
        historyUsers = metricsHistory[["UserId"] + categoryColumns].drop_duplicates()
        historyDates["key"] = 1
        historyUsers["key"] = 1

        # To fill the gaps, we will add a row for each user for each date in the history table
        completeHistory = pd.merge(historyUsers, historyDates, on="key")
        completeHistory.drop(["key"], axis=1, inplace=True)
        completeHistory = cleanDates(df=completeHistory)
        
        # For each date, we will join the metrics values by joining on the UserId and UpdatedOn
        completeHistory = completeHistory.join(
            metricsHistory[keyColumns + categoryColumns + metricsColumns].set_index(
                keyColumns + categoryColumns
            ),
            on=keyColumns + categoryColumns,
            how="left",
        )

        # Wherever there is a missing value, we will fill it with the previous available value
        # using pandas ffill function
        completeHistory[metricsColumns] = (
            completeHistory[["UserId"] + metricsColumns]
            .groupby(["UserId"])
            .fillna(method="ffill")
        )
        completeHistory.dropna(inplace=True)
        completeHistory.sort_values(
            by=["UserId", "UpdatedOn"], ascending=True, inplace=True
        )

        return completeHistory

    def computeScoreAndRank(
        self,
        metricsData: pd.DataFrame,
        metricsColumns: list,
        groupColumns: list,
        suffixConfig: dict,
    ) -> pd.DataFrame:

        for col in metricsColumns:
            # Add zscore
            metricsData = self.calculateColumnZScores(
                df=metricsData,
                groupColumns=groupColumns,
                scoreColumn=col,
                outputColumn=self.utils.scoreColumn(col, config=suffixConfig),
                scaleInput=False,
                logTransform=False,
                scaleOutput=False,
            )
            # Add percentile ranks
            metricsData = self.calculateColumnPercentiles(
                df=metricsData,
                groupColumns=groupColumns,
                scoreColumn=col,
                outputColumn=self.utils.rankColumn(col, config=suffixConfig),
            )

        return metricsData

    def computeRelativeUserMetrics(
        self,
        absoluteMetrics: pd.DataFrame,
        groupColumns: list,
        suffixConfig: dict,
        userMetrics: list,
    ) -> pd.DataFrame:

        relativeMetrics = absoluteMetrics.copy()
        # Keep only metrics which are not derived from parent category
        if "IsParentMetrics" in relativeMetrics:
            relativeMetrics = relativeMetrics[relativeMetrics["IsParentMetric"] == 0]
        # Keep the relevant columns
        relativeMetrics = relativeMetrics[["UserId"] + groupColumns + userMetrics]
        # Compute zscore and rank for each of the metrics
        relativeMetrics = self.computeScoreAndRank(
            metricsData=relativeMetrics,
            metricsColumns=userMetrics,
            groupColumns=groupColumns,
            suffixConfig=suffixConfig,
        )

        return relativeMetrics

    # Function to compute chapter relative metrics and weights
    # We will use total Number of KSCs as proxy indicators (Weight ~ # KSCs).
    # Ideally, this should be replaced with a weights created by subject matter
    # experts or previous exams' data
    def computeRelativeContentMetrics(
        self,
        absoluteMetrics: pd.DataFrame,
        groupColumns: list,
        suffixConfig: dict,
        contentMetrics: list,
    ) -> pd.DataFrame:
        # Reverse the values of Velocity and rename the column as Difficulty
        relativeMetrics = absoluteMetrics.rename(columns={"Velocity": "Difficulty"})
        relativeMetrics["Difficulty"] = -1 * relativeMetrics["Difficulty"]

        # Compute zscore and rank for each of the metrics
        relativeMetrics = self.computeScoreAndRank(
            metricsData=relativeMetrics,
            metricsColumns=contentMetrics,
            groupColumns=groupColumns,
            suffixConfig=suffixConfig,
        )

        return relativeMetrics

    # Function that converts relative numerical metric scores and ranks into named labels
    # using a predefined configuration for mapping values to respective labels
    def categorizeMetrics(
        self, metricsData: pd.DataFrame, inputsConfig: dict, suffixConfig: dict
    ) -> pd.DataFrame:
        # Iterate over each variable that is defined in the inputsConfig
        for inputVar in inputsConfig:
            # If the respective score or rank column of that variable is present in the
            # metrics data then add its label values
            if (
                self.utils.scoreColumn(inputVar, config=suffixConfig) in metricsData
            ) or (self.utils.rankColumn(inputVar, config=suffixConfig) in metricsData):
                for varType in inputsConfig[inputVar]:
                    outputColumn = self.utils.addColumnSuffix(
                        inputVar, varType=varType, config=suffixConfig, isCut=True
                    )
                    if (varType == "score") and (
                        self.utils.scoreColumn(inputVar, config=suffixConfig)
                        in metricsData
                    ):
                        metricsData[outputColumn] = metricsData[
                            self.utils.scoreColumn(inputVar, config=suffixConfig)
                        ]
                    else:
                        metricsData[outputColumn] = metricsData[
                            self.utils.rankColumn(inputVar, config=suffixConfig)
                        ]

                    metricsData[outputColumn] = pd.cut(
                        x=metricsData[outputColumn],
                        bins=inputsConfig[inputVar][varType]["cuts"],
                        labels=inputsConfig[inputVar][varType]["labels"],
                        right=True,
                        include_lowest=True,
                    )

        return metricsData

    # Function that uses the savgol_filter to return a smooth curve for a time series
    # over multiple time periods. The function also smoothens the data by reducing
    # granularity of the data - so if more than a certain number of data points are
    # available, then it will summarize at a weekly frequency from daily data.
    def smoothenTrendData(
        self,
        metricsData: pd.DataFrame,
        metricColumns: list,
        dateColumn: str,
        maxWindow: int = 31,
        durationForWeekly: int = 5,
    ) -> pd.DataFrame:

        if metricsData is None or metricsData.shape[0] < 3:
            self.logger.warning("Number of datapoints is too less for smoothening.")
            return metricsData

        smoothMetrics = metricsData[[dateColumn] + metricColumns].copy()
        if (
            metricsData[dateColumn].min() + timedelta(weeks=durationForWeekly)
            <= metricsData[dateColumn].max()
        ):
            smoothMetrics[dateColumn] = smoothMetrics[dateColumn].apply(
                lambda x: x + timedelta(days=(7 - x.weekday()))
            )
            smoothMetrics = smoothMetrics.groupby(dateColumn, as_index=False).mean()

        windowLength = min(max(int(smoothMetrics.shape[0] / 2), 1), maxWindow)
        if (windowLength % 2) == 0:
            windowLength += 1

        for metric in metricColumns:
            smoothMetrics[metric] = scipy.signal.savgol_filter(
                smoothMetrics[metric], window_length=windowLength, polyorder=1
            )

        return smoothMetrics
