from difflib import Match
from tkinter import ALL
import numpy as np
import pandas as pd
from datetime import datetime
import logging

import dash
from dash import dcc, html, Input, Output, State,ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
# from localStoragePy import localStoragePy

from imports import importModules
from classes import Content, QuestionProps
QuestionKscText=[]
QuestionIsPrimaryKsc=[]

class Dashboard:

    app = None
    db = None
    data = None
    utils = None
    logger = None

    config: dict = None
    allCourseChapters: pd.DataFrame = None
    

    def __init__(self, app, config):
        self.app = app
        self.logger = logging.getLogger("dash.app")

        self.utils, self.db, self.data, self.calc, self.plotter = importModules(
            config=config
        )
        # Load config variables
        self.config = config["questionReview"]
        # Load course chapter data from DB
        self.loadCourseChapterData()

    def loadCourseChapterData(self):
        # Get active course ids
        activeCourseIds, _ = self.data.getActiveCourseIds()
        # Create a content object with active course ids
        content = Content(courseIds=activeCourseIds)
        # Get all course chapters from DB
        self.allCourseChapters, _ = self.data.getCourseChapters(
            content=content, includeNames=True
        )
        return

    def setAppLayout(self):
         
        self.app.layout = html.Div(
            children=[
                html.Div(
                    children=[
                        dcc.Store(id="allQuestionsId"),
                        dcc.Store(id="isBlankId"),
                        dcc.Store(id="questionPropsId"),
                        dcc.Store(id="QuestionFeedbackId"),
                        dcc.Store(id="allKscTextId"),
                        dcc.Store(id="currentKscdataId"),
                        dbc.Container(
                            fluid=True,
                            children=self.getContentInputLayout(),
                            className="bg-light  m-0",
                        ),
                        html.Div(
                            id="questionKSCContainerId",
                            children=[
                                dbc.Container(
                                    fluid=True,
                                    children=[ dbc.Row(
                                        children=[
                                            dbc.Col(
                                                children=self.getQuestionNavigations(),
                                                width=8,
                                                className="d-flex flex-wrap ms-4 mt-3"
                                            ),
                                            dbc.Col(
                                                children=self.getSaveCancelButtons(),
                                                className="d-flex flex-wrap mt-4"
                                            )
                                        ],
                                    ),]
                                ),
                                dbc.Container(
                                    fluid=True,
                                    id="ReviewButtonsId",
                                    children=[
                                        dbc.Row(
                                            children=[
                                               self.getReviewRadioButtons(type=reviewType)
                                               for reviewType in self.config["reviewTypes"]
                                            ],
                                            className="ps-1 ",
                                        ),
                                    ]  
                                ),
                                dbc.Container(
                                    fluid =True,
                                    id="imagesContainerId",
                                    children=[
                                        dbc.Row(
                                            children=[
                                                dbc.Col(
                                                    children=self.getQuestionImageLayout(),
                                                    className="flex wrap ps-1 block",
                                                ),
                                                dbc.Col(
                                                    children=[
                                                        dbc.Row(
                                                            children=self.getCurrentKSCLayout(),
                                                            className="flex wrap pe-1",
                                                            style={"height": "145px"}
                                                        ),
                                                        dbc.Row(
                                                            children=self.getMapNewKSCLayout(),
                                                            className="flex wrap pt-1",
                                                            style={"height": "65px"}
                                                        )
                                                    ]
                                                )
                                            ]
                                        ),
                                    ],
                                    className="d-flex align-items-center flex-wrap"
                                ),  
                                dbc.Container(
                                    fluid=True,
                                    children=[
                                        dbc.Row(
                                            children=[
                                                dbc.Col(
                                                    children=self.getSolutionLayout(),
                                                    className="ps-1 mt-0",
                                                ),
                                                dbc.Col(
                                                    children=self.getKSCImageLayout(),
                                                    className="ps-1 mt-0"
                                                )
                                            ]
                                        )
                                    ],
                                    className="d-flex align-items-center flex-wrap"
                                )  
                            ],
                            style={"display": "none"},
                            
                        ),
                    ]
                ),
            ]
        )
        self.addUserActionCallbacks()
        return

    # Get all layout elements to create the page
    def getContentInputLayout(self):
        contentInputChildren = [
            dbc.Row(
                    children=self.getnavbar(),
                    style={"height": "60px"}
            ),
            dbc.Row(
                children=[
                    dbc.Col(
                        children=self.getReviewedLayout(),
                        width=2,
                        style={"border-right": "3px solid #000000"}
                    ),
                    dbc.Col(
                        children=self.getAllContentDropdowns(),
                        width=6,
                        style={"border-right": "3px solid #000000"}
                    ),
                    dbc.Col(
                        children=self.getQuestionByIdLayout(),
                    ),
                    dbc.Col(
                        children=self.getLoadButton(),
                        width=1,
                    )
                ]
            ),
        ]
        return contentInputChildren

    def getnavbar(self):
        navbar=[
            html.Div(
                html.Div(
                    html.H4(html.Strong("Question - KSC Mapping")),
                    style={"margin-top":"14px"}
                ),
                className="d-flex m-0 ",
                style={"background-color":"#00004d","color":"white"},
            ),
        ]
        return navbar

    def getReviewedLayout(self):
        ReviewedButton = [
            dbc.Row(html.Div(
                html.H6("Load All Reviewed"),
                className="d-flex flex-shrink-0  justify-center-start mt-2",
            ),
            ),
            dbc.Row(html.Div(
                html.Button(
                    "Load Reviewed",
                    id="loadAllReviewdId",
                    n_clicks=0,
                    className="btn btn-outline-primary btn-sm rounded shadow-none",
                    style={"background-color":"#00004d","color":"white"}
                ),
                className="d-flex flex-shrink-0  justify-center-start ",
            ),
            ),
             dbc.Row(html.Div(
                html.H6("Or,Load All Unmapped"),
                className="d-flex flex-shrink-0  justify-center-start mt-2",
            ),
            ),
            dbc.Row(
            html.Div(
                html.Button(
                    "Load Unmapped",
                    id="loadAllUnmappedId",
                    n_clicks=0,
                    className="btn btn-outline-primary btn-sm rounded shadow-none mb-2",
                    style={"background-color":"#00004d","color":"white"}
                ),
                className="d-flex flex-shrink-0 justify-center-start",
            ),
            )
        ]
        return ReviewedButton

    def getAllContentDropdowns(self):
        allDropdowns = self.getContentDropdowns()
        contentDropdowns = [
            dbc.Row(html.Div(
                html.H6("Or, Load By Content"),
                className="d-flex flex-shrink-0  justify-center-start mt-2",
            ),
            ),
            dbc.Row(
                children=[
                    dbc.Col(allDropdowns["Course"],width=4 ,className="p-0 "),
                    dbc.Col(allDropdowns["Class"],width= 4 , className="p-0 "),
                ],
                className="ps-2 pb-1",
            ),
            dbc.Row(
                children=[
                    dbc.Col(allDropdowns["Subject"],width= 4, className="p-0"),
                    dbc.Col(allDropdowns["Chapter"],width= 4, className="p-0"),
                    dbc.Col(
                        children=[
                            html.Div(id="dummyContentChangeId"),
                            html.Button(
                                "Load Questions",
                                id="loadQuestionsButtonId",
                                n_clicks=0,
                                className="btn btn-outline-primary btn-sm rounded shadow-none",
                                style={"background-color":"#00004d","color":"white"}
                            ),
                        ],
                        className="d-flex align-items-center",
                    ),
                ],
                className="ps-2 pb-1",
            ),
        ]

        for idx, label in enumerate(self.config["contentLabels"][:-1]):
            childLabel = self.config["contentLabels"][idx + 1]
            self.addContentDropdownCallback(label=label, childLabel=childLabel)

        return contentDropdowns

    def getQuestionByIdLayout(self):
          QuestionById = [
              dbc.Row(html.Div(
                  html.H6("Or, Load Question"),
                  className="d-flex flex-shrink-0  justify-center-start mt-2"
              )),
              dbc.Row(
                  children=[
                      dbc.Col(html.Div(
                          html.H6("By Id"),
                          className="d-flex flex-shrink-0  justify-center-start mt-2",
                      ),
                      width=3,
                      ),
                      dbc.Col(html.Div(
                          dbc.Input(id="QuestionId", placeholder="Question Id", type="text")
                      ))
                  ],
                  className="ps-2 pb-1",
              ),
              dbc.Row(
                  children=[
                      dbc.Col(html.Div(
                          html.H6("By Code"),
                          className="d-flex flex-shrink-0  justify-center-start mt-2"
                      ),
                      width=3,
                      ),
                       dbc.Col(html.Div(
                          dbc.Input(id="QuestionCodeId", placeholder="Question Code", type="text"),
                          className="d-flex flex-shrink-0  justify-center-start mt-1"
                      )),
                  ],
                  className="ps-2 pb-1",
              )

          ]
          return QuestionById
           
    def getLoadButton(self):
        LoadButton=[ 
            dbc.Row(
                children=[
                    html.Div(
                        html.Button(
                        "Load",
                        id="loadQuestionsButtonById",
                        n_clicks=0,
                        className="btn btn-outline-primary btn-md rounded shadow-none ",
                        style={"background-color":"#00004d","color":"white","margin-top":"80px"}
                    ),
                    )
                    
                ],

            )
        ]
        return LoadButton

    def getReviewRadioButtons(self, type: str):
        return html.Div(
            children=[
                html.H5(html.Strong(f"{type}"), style={"display":"inline-block","margin-left":"14px","margin-top":"8px"}),
                html.Div(
                    children=[
                        dbc.RadioItems(
                            id=f"{type}CorrectRadioId",
                            className="btn-group",
                            inputClassName="btn-check bg:Primary",
                            labelClassName="btn btn-outline-primary btn-sm shadow-none",
                            labelStyle={
                                "width": "4.8em",
                                "margin-left": "-1.0em",
                                "border-radius": "0.6em",
                                
                            },
                            labelCheckedClassName="active",
                            options=[
                                {"label": "YES", "value": 1},
                                {"label": "NO", "value": 0},
                            ],
                        ),
                        html.Div(id=f"dummy{type}CorrectId"),
                    ],
                    className="radio-group",
                    style={ 'display': 'inline-block','min-width':'150px'}
                ),
               
            ],
            style={'width': '29%', 'display': 'inline-block'}
        )  


    def getContentDropdowns(self):
        allDropdowns = dict()
        for idx, label in enumerate(self.config["contentLabels"]):
            items = []
            if label == "Course":
                items = self.allCourseChapters["CourseName"].unique()
            allDropdowns[label] = html.Div(
                children=[
                    dcc.Dropdown(
                        id=f"{label}DropdownId",
                        placeholder=f"Select a {label}",
                        options=items,
                        optionHeight=40,
                        className="form-control-sm p-1",
                    ),
                ]
            )

        return allDropdowns

    # Accessing current dropdown state and values
    def getDropdownStates(self):
        return [
            State(f"{label}DropdownId", "value")
            for label in self.config["contentLabels"]
        ]
    #Accessing current states and value of Review
    def getReviewRadioButtonOutputs(self):
        return [
            Output(f"{label}CorrectRadioId", "value")
            for label in self.config["reviewTypes"]
        ]

    def getReviewRadioButtonStates(self):
        return [
            State(f"{label}CorrectRadioId", "value")
            for label in self.config["reviewTypes"]
        ]

    def getImageSrcOutputs(self):
        return [
            Output(f"{label.lower()}ImageId", "src")
            for label in self.config["imageTypes"]
        ]    

    def getDropdownValues(self, selectedValues):
        selectedContent = dict()
        for idx, label in enumerate(self.config["contentLabels"]):
            selectedContent[label] = selectedValues[idx]
        return selectedContent

    def addContentDropdownCallback(self, label: str, childLabel: str):
        @self.app.callback(
            [
                Output(f"{childLabel}DropdownId", "value"),
                Output(f"{childLabel}DropdownId", "options"),
            ],
            [Input(f"{label}DropdownId", "value")],
            self.getDropdownStates(),
        )
        def updateDropdownOptions(dropdownValue, *args):
            selectedContent = self.getDropdownValues(args)
            selectedCourseChapters = self.filterCourseChapters(
                selectedContent=selectedContent,
                sourceLabel=label,
            )
            childItems = []
            if dropdownValue is not None:
                # Update the items in the child dropdown
                colName = f"{childLabel}Name"
                childItems = selectedCourseChapters[colName].unique()
            return None, childItems
    
    # Layout for save cancel Button
    def getSaveCancelButtons(self):
        saveAlertDiv = [
            html.Div(
                children=[
                    dbc.Alert(
                        "Changes saved!",
                        id="savedAlertId",
                        class_name="mt-4",
                        dismissable=True,
                        duration=3000,
                        is_open=False,
                        color="success",
                    ),
                    dbc.Alert(
                        "Changes cancelled!",
                        id="revertAlertId",
                        class_name="mt-4",
                        dismissable=True,
                        duration=3000,
                        is_open=False,
                        color="danger",
                    ),
                ]
            )
        ]
        saveReturnChildren = [
            html.Div(
                [
                    html.Button(
                        "Save",
                        id="saveButtonId",
                        n_clicks=0,
                        className="btn btn-primary btn-xl rounded shadow-none",
                        style={"min-width":"150px","background-color":"#00004d"}
                    ),
                    html.Button(
                        "Revert",
                        id="revertButtonId",
                        n_clicks=0,
                        className="ms-4 btn btn-danger btn-xl rounded shadow-none",
                        style={"min-width":"150px"}
                    ),
                ]
            ),
        ]
        saveReturnChildren = saveAlertDiv + saveReturnChildren

        return saveReturnChildren

    def getQuestionNavigations(self):
        navigationChildren = [
            html.Div(
                children=[
                    html.Div(
                        html.Button(
                            html.I(className="fa fa-chevron-left fa-2x text-primary"),
                            id="prevQuestionButtonId",
                            className="btn shadow-none",
                        ),
                        className="flex-fill justify-center-start ms-8",
                    ),
                    html.H5(
                        [
                            html.Span(" Question Code"),
                            html.Span(" ["),
                            html.Span(id="currentQuestionId"),
                            html.Span(" / "),
                            html.Span(id="questionCountId"),
                            html.Span("]"),
                        ],
                        className="w-90%  text-center",
                        style={"margin-left":"220px"}
                    ),
                    html.Div(
                        html.Button(
                            html.I(className="fa fa-chevron-right fa-2x text-primary"),
                            id="nextQuestionButtonId",
                            className="btn shadow-none",
                        ),
                        className="flex-fill text-end",
                        style={"margin-left":"220px"}
                    ),
                ],
                className="d-flex align-items-center flex-wrap",
            ),
        ]
        return navigationChildren

    def getQuestionImageLayout(self):
        questionImgChildren = [
            html.Div(
                children=html.Img(
                    id="questionImageId",
                    src=None,
                    className="flex-fill img-fluid border border-dark rounded overflow-hidden ",
                    
                ),
                style={"background":"grey",  "height": "210px","width": "780px"},
                className="d-flex ms-4 mt-2 flex-wrap",
            ),
        ]
        return questionImgChildren

    # Getting row for current KSC
    def getContentForCurrentKSC(self, text : str , IsPrimary : int , index : int ):
        if IsPrimary:
            color="#006600"
        else:
            color="#c2c2d6"   
        return  html.Div(
                        children=[
                        html.Div(
                            html.H6(text,
                            id={
                                "type" : "currentKscText",
                                "index" : index
                            },
                            ),
                            style={"width":"500px"},
                            className="col-8"
                        ),
                        html.Div(
                            html.Button(
                            html.I(className="fa fa-star fa-2x"),
                            id={
                                "type" : "currentKscPrimaryKey",
                                "index" : index
                            },
                            n_clicks=0,
                            className="btn shadow-none pt-0 ps-0",
                            style={"color" : color},
                        ),
                            className="col-1"
                        ),
                        html.Div(
                            html.Button(
                            html.I(className="fa fa-trash fa-2x "),
                            id={
                                "type" : "currentKscDeleteButton",
                                "index" : index
                            },  
                            n_clicks=0, 
                            className="btn shadow-none pt-0 ps-0",
                        ),
                            className="col-1"
                        ),
                        ],
                        style={"height":"40px"},
                        className="row"
                    )
         
    
    def getCurrentKSCLayout(self):
        return html.Div(
            children=[
                html.H5(html.Strong("Current KSCs")),
                html.Div(
                    id="currentKscId",
                    style={"height":"120px","overflow-x":"hidden","overflow-y":"auto"},
                    className="pr-1 "
                )
            ],
        )           

    def getMapNewKSCLayout(self):   
        items=[]
        currentksc=[
            html.Div(
                children=[
                    html.Div(
                        html.H5(html.Strong("Map New KSC"),className="ps-0"),
                        className="row ",
                        ),
                    html.Div(
                        children=[
                            html.Div(
                            dcc.Dropdown(
                            id="allKscMapppedId",
                            placeholder="Select New KSC",
                            options=items,
                            optionHeight=40,
                            className="form-control-md d-block pl-0",
                            ),
                              style={"width":"490px","padding-left":"0px","margin-left":"0px"},
                              className="d-felx flex-wrap mt-0 "
                            ),
                            html.Div(
                            html.Button(
                               html.I(className="fa fa-search fa-2x mt-0  "),
                               id="searchNewKscId",
                               className="btn shadow-none pt-0 ps-0",
                           ),
                           style={ "width": "20px"},
                           className="d-flex flex-wrap pt-0 pb-2",
                           ),
                           html.Div(
                            html.Button(
                               html.I(className="fa fa-plus-square fa-2x mt-0 ",style={"min-width":"80px"}),
                               id="addNewKscId",
                               className="btn shadow-none pt-0 ps-0",
                           ),
                           style={ "width": "20px"},
                           ),
                        ],
                        className="row",
                    ),
                ],
                style={ "width": "600px"},
            className="container  flex-wrap",
        ),
        ]   
        return currentksc

        
    def getSolutionLayout(self):
        solutionlayout=[
             html.Div(
                children=html.Img(
                    id="fullsolutionImageId",
                    src=None,
                    className="flex-fill img-fluid border border-dark rounded overflow-hidden ",
                ),
                style={"background":"yellow",  "height": "220px","width": "780px"},
                className="d-flex ms-4 mt-1 flex-wrap",
            ),
        ]  
        return solutionlayout

    def getKSCImageLayout(self):
        kscLayoutChildren = [
            html.Div(
                children=html.Img(
                    id="kscImageId",
                    src=None,
                    className="img-fluid border border-dark rounded overflow-hidden ",
                ),
                style={"background":"red",  "height": "220px","width": "600px"},
                className="d-flex ms-0 mt-1 flex-wrap",
            ),
        ]
        return kscLayoutChildren 

    def filterCourseChapters(
        self, selectedContent: dict, sourceLabel: str = None
    ) -> pd.DataFrame:
        # Recompute the selected course chapters
        selectedCourseChapters = self.allCourseChapters.copy()
        selectConditions = []
        for idx, label in enumerate(self.config["contentLabels"]):
            colName = f"{label}Name"
            if selectedContent[label] is not None:
                selectConditions.append(
                    selectedCourseChapters[colName] == selectedContent[label]
                )
                # Only filter courses till the currently changed dropdown
                # because child dropdowns will be set to None later
                if sourceLabel and (label == sourceLabel):
                    break

        selectedCourseChapters = selectedCourseChapters.iloc[
            np.where(np.all(selectConditions, axis=0))
        ]

        return selectedCourseChapters

    def loadNewQuestionsAndKsc(self, selectedContent: dict):
        if selectedContent["Chapter"] is None:
            return None, None
        selectedCourseChapters = self.filterCourseChapters(
            selectedContent=selectedContent
        )
        allKsc=self.data.getKSCsForCourseChapters(
            courseChapters=selectedCourseChapters,
            includeKSCDetails=True
        )

        allQuestions = self.data.getQuestionsForCourseChapters(
            courseChapters=selectedCourseChapters,
            columnList=[
                "QuestionId",
                "QuestionCode",
                "AnswerOption",
                "QuestionDiagramURL",
                "FullSolutionURL",
                "QuestionLatex",
            ],
            includeMetrics=True,
            metricsColumns=[
                "Attempted",
                "Correct",
                "TimeTaken",
            ],
        )
        if self.utils.isNullDataFrame(allQuestions):
            return None, None

        allQuestions["Accuracy"] = allQuestions["Correct"] / allQuestions["Attempted"]
        allQuestions["AvgTimeTaken"] = (
            allQuestions["TimeTaken"] / allQuestions["Attempted"]
        )

        allQuestions.rename(
            columns={"FullSolutionURL": "FullSolutionDiagramURL"}, inplace=True
        )
        allQuestions.reset_index(inplace=True, drop=True)
        
        return allQuestions,allKsc

    # Create callbacks
    def addUserActionCallbacks(self):
        @self.app.callback(
            Output("savedAlertId", "is_open"),
            Output("revertAlertId", "is_open"),
            Output("allQuestionsId", "data"),
            Output("isBlankId", "data"),
            Output("questionCountId", "children"),
            Output("questionKSCContainerId", "style"),
            Output("currentQuestionId", "children"),
            Output("questionPropsId", "data"),
            Output("allKscMapppedId","options"),
            Output("allKscTextId","data"),
            Output("currentKscId","children"),
            Output("allKscMapppedId","value"),
            Output("currentKscdataId","data"),

            self.getImageSrcOutputs(),
            self.getReviewRadioButtonOutputs(),

            Input("loadQuestionsButtonId", "n_clicks"),
            Input("prevQuestionButtonId", "n_clicks"),
            Input("nextQuestionButtonId", "n_clicks"),
            Input("saveButtonId", "n_clicks"),
            Input("revertButtonId", "n_clicks"),
            Input("addNewKscId","n_clicks"),

            Input({ "type" : "currentKscDeleteButton" , "index" : ALL }, "n_clicks"),
            Input({ "type" : "currentKscPrimaryKey", "index" : ALL},"n_clicks"),
            State({ "type" : "currentKscPrimaryKey", "index" : ALL}, "style"),
            State({ "type" : "currentKscText" , "index" : ALL} ,"children"),

            State("allQuestionsId", "data"),
            State("questionPropsId", "data"),
            State("allKscTextId","data"),
            State("isBlankId", "data"),
            State("allKscMapppedId","value"),
            State("allKscMapppedId","options"),
            State("currentKscdataId","data"),
            self.getDropdownStates(),
            prevent_initial_call=True
        )
        def manageUserActions(
            loadQuestionClick, 
            prevQuestionClick,
            nextQuestionClick,
            saveButtonClick,
            revertButtonClick,
            addnewKscClick,
            deleteKscClick,
            primaryKscClick,
            primaryKeyValue,
            currentKscText,
            allQuestionsJson,
            questionPropsJson, 
            allKscJson,
            isPrevBlank, 
            newKscText,
            allKscMappedText,
            currentKscData,
            *args):

            changedId = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
            contentStates = args[0 : len(self.config["contentLabels"])]
            selectedContent = self.getDropdownValues(contentStates)

            items=currentKscData
           
            allQuestions = self.utils.jsonToDataFrame(
                jsonString=allQuestionsJson
            )

            allKsc= self.utils.jsonToDataFrame(
                jsonString=allKscJson
            )

            questionProps = (
                QuestionProps()
                if (questionPropsJson is None)
                else QuestionProps(**questionPropsJson)
            )

            isBlank = True if isPrevBlank is None else isPrevBlank
            isQuestionsLoaded = False
            isQuestionNavigation=False
            showSavedAlert = False
            showRevertedAlert = False
            moveTo = 0

            if "ChapterDropdownId" in changedId:
                isBlank = True
                questionProps = QuestionProps()
            elif "loadQuestionsButtonId" in changedId:
                if not isBlank:
                    raise PreventUpdate()
                else:
                    isQuestionsLoaded = True
                    isQuestionNavigation=True
                    allQuestions,allKsc = self.loadNewQuestionsAndKsc(
                        selectedContent=selectedContent
                    )
                    allKscMappedText=allKsc["KSCText"].tolist()
            elif "prevQuestionButtonId" in changedId:
                isQuestionNavigation = True
                moveTo = -1
            elif "nextQuestionButtonId" in changedId:
                isQuestionNavigation = True
                moveTo = 1  
            elif ("saveButtonId" in changedId) :
                showSavedAlert = True
            elif ("revertButtonId" in changedId) :
                showRevertedAlert = True 
                       
            # Updating current Question in questionProps
            if isQuestionNavigation:
                questionProps.updateCurrentQuestion(
                    moveTo=moveTo,
                    allQuestions=allQuestions,
                    imageTypes=self.config["imageTypes"],
                    imageBaseURL=self.config["imageBaseURL"],
                )

            # Getting images URL from questionProps 
            imageURLs = (
            [None] * len(self.config["imageTypes"])
            if questionProps.imageURLs is None
            else questionProps.imageURLs
            )

            #Updating allKscMapped list when load or navigation button clicked
            if isQuestionNavigation or isQuestionsLoaded:    
                allKscMappedText=allKsc["KSCText"].tolist()
            
            #Taking list of QuestionKscText and QuestionKscIsPrimary from questionProps
            QuestionKscText=questionProps.kscText
            QuestionKscIsPrimary=questionProps.isPrimaryKSC

            # Getting all Current KSC with delete button in a list 
            if isQuestionsLoaded or isQuestionNavigation:
                if items is None:
                   items=[]
                else:
                    items.clear()        
                for i in range(len(QuestionKscText)):
                    allKscMappedText.remove(QuestionKscText[i])
                    items.append(
                        self.getContentForCurrentKSC(
                            text=QuestionKscText[i],
                            IsPrimary=QuestionKscIsPrimary[i],
                            index=i+1
                        )
                    )

            # Appending New KSC to current KSC and updating imageURLs
            if "addNewKscId" in changedId:
                if newKscText is not None:
                    allKscMappedText.remove(newKscText)
                    if newKscText in QuestionKscText :
                        PrimaryKey = QuestionKscIsPrimary[QuestionKscText.index(newKscText)]
                    else:
                        PrimaryKey = 0    
                    items.append(
                    self.getContentForCurrentKSC(
                            text=newKscText,
                            IsPrimary=PrimaryKey,
                            index=len(items)+1
                        )
                    )
                    imageURLs[0]=allKsc.loc[allKsc['KSCText']==newKscText,'KSCDiagramURL'].iloc[0]
                
                
            # Action  for delete button clicked and primaryKsc button
            if changedId[2:7] == "index":
                splittedchangedId=changedId.split(",")
                indexchangedId=splittedchangedId[0].split(":")
                typechangedId=splittedchangedId[1].split(":")
                typechangedId[1]=typechangedId[1][1:-2]
                if typechangedId[1]=="currentKscDeleteButton":
                    cnt=0
                    for i in range(len(items)):
                        if items[i] !="":
                            cnt+=1
                        if str(i+1)==indexchangedId[1]:
                            items[i]=""
                            allKscMappedText.append(currentKscText[cnt-1]) 
                else:
                    cnt=0
                    for i in range(0,int(indexchangedId[1])):
                        if items[i] !="":
                           cnt+=1
                    for i in range(len(primaryKeyValue)):
                        if (i+1)==cnt:
                            key=0
                            if primaryKeyValue[i]=={"color" : "#c2c2d6"}:
                                key=1
                            #Updating items list with current primaryKSC value    
                            items[int(indexchangedId[1])-1]= self.getContentForCurrentKSC(
                            text=currentKscText[i],
                            IsPrimary=key,
                            index=int(indexchangedId[1])
                        )
                                 
            # Store all Ksc of a coursechapter
            allKscJson=(
                self.utils.dataFrameToJson(allKsc)
                if isQuestionsLoaded
                else dash.no_update
            )

            # Store all Questions of a coursechapter
            allQuestionsJson = (
                self.utils.dataFrameToJson(allQuestions)
                if isQuestionsLoaded
                else dash.no_update
            )

            currentKscData=items
            allKscMappedText.sort()

            reviewValues = [np.nan for reviewType in self.config["reviewTypes"]]

            if isBlank:
                return(
                    [
                        showSavedAlert,
                        showRevertedAlert,
                        allQuestionsJson,
                        isBlank,
                        questionProps.totalQuestions,
                        {"display": "block"},
                        questionProps.currentNumber,
                        questionProps.getJson(),
                        allKscMappedText,
                        allKscJson,
                        items,
                        None,
                        currentKscData
                    ]
                    +imageURLs
                    +reviewValues
                )
            return(
                   [
                        showSavedAlert,
                        showRevertedAlert,
                        allQuestionsJson,
                        isBlank,
                        None,
                        {"display": "none"},
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None
                    ]
                    +imageURLs
                    +reviewValues
            )    
