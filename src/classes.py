from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from data import Data


@dataclass
class Content:
    courseIds: list = None
    classIds: list = None
    subjectIds: list = None
    chapterIds: list = None

    def __post_init__(self):
        if (self.courseIds is not None) and (not isinstance(self.courseIds, list)):
            self.courseIds = [self.courseIds]
        if (self.classIds is not None) and (not isinstance(self.classIds, list)):
            self.classIds = [self.classIds]
        if (self.subjectIds is not None) and (not isinstance(self.subjectIds, list)):
            self.subjectIds = [self.subjectIds]
        if (self.chapterIds is not None) and (not isinstance(self.chapterIds, list)):
            self.chapterIds = [self.chapterIds]

    def filterActiveCourses(self, data: object):
        activeCourseIds, _ = data.getActiveCourseIds(onlyQuery=False)
        self.courseIds = (
            activeCourseIds
            if (self.courseIds is None)
            else [id for id in self.courseIds if id in activeCourseIds]
        )

    def copyContent(self):
        newContent = Content(
            courseIds=self.courseIds,
            classIds=self.classIds,
            subjectIds=self.subjectIds,
            chapterIds=self.chapterIds,
        )
        return newContent


@dataclass
class QuestionProps:
    qIndex: int = None
    qId: int = None
    qCode: str = None
    currentNumber: int = None
    totalQuestions: int = None
    answerOption: str = None
    accuracy: str = None
    avgTimeTaken: str = None
    metricsColorClass: str = None
    qLatex: str = None
    kscId: list = None
    isPrimaryKSC: list = None
    kscText: list = None
    kscStartIndex: int = None
    kscTotalQuestions: int = None
    totalKSCs: int = None
    imageURLs: list = None

    def updateCurrentQuestion(
        self,
        moveTo: int,
        allQuestions: pd.DataFrame,
        imageTypes: list,
        imageBaseURL: str,
    ):
        if self.qIndex is None:
            self.qIndex=0
        maxQuestionIdx = 0 if allQuestions is None else (len(pd.unique(allQuestions["QuestionId"]))- 1)
        if (moveTo < 0 and self.currentNumber == 1) or (
            moveTo > 0 and self.currentNumber >= maxQuestionIdx
        ):
            return
        if moveTo == 0:
            self.qIndex = 0
            self.currentNumber=1
        elif moveTo < 0:
            currentQuestionId = allQuestions[["QuestionId"]].iloc[self.qIndex][0]
            cnt=0
            while cnt<2:
                self.qIndex-=1
                newQuestionId=allQuestions[["QuestionId"]].iloc[self.qIndex][0]
                if currentQuestionId != newQuestionId:
                    cnt+=1
                    currentQuestionId=newQuestionId
            self.qIndex += 1    
            self.qIndex = max(0, min(maxQuestionIdx, self.qIndex))  
        else:
            self.qIndex+=moveTo      
            self.qIndex = max(0, min(maxQuestionIdx, self.qIndex))  
        self.updateProperties(
            allQuestions=allQuestions, imageTypes=imageTypes, imageBaseURL=imageBaseURL,moveTo=moveTo
        )
        return

    def updateProperties(
        self, allQuestions: pd.DataFrame, imageTypes: list, imageBaseURL: str,moveTo:int
    ):
        oldQuestionCount = self.totalQuestions
        self.currentNumber = 0 if (self.currentNumber is None) else (self.currentNumber + moveTo)
        self.totalQuestions = 0 if (allQuestions is None) else len(pd.unique(allQuestions["QuestionId"]))
        self.qId = allQuestions[["QuestionId"]].iloc[self.qIndex][0]
        self.qCode = allQuestions[["QuestionCode"]].iloc[self.qIndex][0]
        self.answerOption = allQuestions[["AnswerOption"]].iloc[self.qIndex][0]
        self.qLatex = allQuestions[["QuestionLatex"]].iloc[self.qIndex][0]
        
        # Update question metrics
        self.updateQuestionMetrics(allQuestions=allQuestions)
        
        self.imageURLs = list()
        self.kscId = list()
        self.kscText = list()
        self.isPrimaryKSC = list()
        # Update KSC properties 
        newQuestionId = allQuestions[["QuestionId"]].iloc[self.qIndex][0]

        flag=0
        # With this loop, Updating the list of all ksc text and Isprimary of a Question
        while newQuestionId==self.qId:
            self.kscId.append(allQuestions[["KSCId"]].iloc[self.qIndex][0])
            self.kscText.append(allQuestions[["KSCText"]].iloc[self.qIndex][0])
            self.isPrimaryKSC.append(allQuestions[["IsPrimaryKSC"]].iloc[self.qIndex][0])
            if allQuestions[["IsPrimaryKSC"]].iloc[self.qIndex][0]==1:
                flag=1
                partialURL = allQuestions[["KSCDiagramURL"]].iloc[self.qIndex][0]
                self.imageURLs.append(imageBaseURL + partialURL.replace("~", ""))
            self.qIndex=self.qIndex+1
            newQuestionId=allQuestions[["QuestionId"]].iloc[self.qIndex][0]    


        self.qIndex -= 1  

        #If question has no Primary KSC, add url of any non-primaryKSC
        for imageType in imageTypes:
            if imageType != "KSC":
                urlColumn = f"{imageType}DiagramURL"
                partialURL = allQuestions[[urlColumn]].iloc[self.qIndex][0]
                self.imageURLs.append(imageBaseURL + partialURL.replace("~", ""))
            elif flag==0:
                urlColumn = "KSCDiagramURL"
                partialURL = allQuestions[[urlColumn]].iloc[self.qIndex][0]
                self.imageURLs.append(imageBaseURL + partialURL.replace("~", ""))
        return

    def updateQuestionMetrics(self, allQuestions: pd.DataFrame):
        missingString = "Insufficient data"
        accuracy = allQuestions[["Accuracy"]].iloc[self.qIndex][0]
        attempts = allQuestions[["Attempted"]].iloc[self.qIndex][0]
        avgTimeTaken = allQuestions[["AvgTimeTaken"]].iloc[self.qIndex][0]
        self.accuracy = (
            missingString
            if np.isnan(accuracy)
            else f"{int(100 * accuracy)}% @ {int(attempts)} attempts"
        )
        self.avgTimeTaken = (
            missingString if np.isnan(avgTimeTaken) else f"{int(avgTimeTaken)} sec"
        )
        self.metricsColorClass = "text-light"
        if not np.isnan(accuracy):
            self.metricsColorClass = (
                "text-danger"
                if accuracy < 0.33
                or accuracy > 0.90
                or avgTimeTaken < 10
                or avgTimeTaken > 180
                else "text-success"
            )

        return

    def getJson(self):
        return asdict(self)
