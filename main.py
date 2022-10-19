import os
import sys
import pathlib

sys.path.append(os.path.join(pathlib.Path(__file__).parent, "src"))

import json
import imports


def main() -> None:
    # Load config from json
    configDir = os.path.join(pathlib.Path(__file__).parent, "config")
    with open(os.path.join(configDir, "config.json")) as configJson:
        config = json.load(configJson)
    # Add secrets to config dictionary
    with open(os.path.join(configDir, config["secretsJson"])) as secretsJson:
        config["secrets"] = json.load(secretsJson)

    
    # Initialize logging
    imports.initializeLogger()

    # Import the basic modules
    utils, db, data, calc, plotter = imports.importModules(config=config)
    
    # DO SOMETHING HERE 
    plotter.bubblePlot()
    return


if __name__ == "__main__":
    main()
