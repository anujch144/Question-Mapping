import os
import json
import logging.config

from utils import Utils
from db import DBConnection
from data import Data
from calculations import Calculations
from plotter import PlotlyPlotter

# Function that imports all the basic modules in one go
def importModules(config):
    utils = Utils()
    db = DBConnection(utils=utils, config=config)
    data = Data(db=db, utils=utils)
    calc = Calculations(utils=utils)
    plotter = PlotlyPlotter(plotterConfig=config["plotter"])
    
    return utils, db, data, calc, plotter


# Function that initializes the logging configuration
def initializeLogger(
    logConfigPath: str = "./config/log_config.json",
    defaultLogLevel=logging.INFO,
):
    if os.path.exists(logConfigPath):
        with open(logConfigPath, "rt") as logConfigJson:
            logConfig = json.load(logConfigJson)
        logging.config.dictConfig(logConfig)
    else:
        logging.basicConfig(level=defaultLogLevel)
