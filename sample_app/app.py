import sys
import os
import pathlib

sys.path.append(os.path.join(pathlib.Path(__file__).parent.parent, "src"))

import json
import dash
import dash_bootstrap_components as dbc
from layout import Dashboard

app = dash.Dash(
    "SampleApp",
    external_stylesheets=[
        dbc.themes.FLATLY,
        dbc.icons.FONT_AWESOME,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css",
        
    ],
    external_scripts=[
        "https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/latest.js?config=TeX-AMS-MML_SVG",
    ],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)

configDir = os.path.join(pathlib.Path(__file__).parent.parent, "config")
# Load config
with open(os.path.join(configDir, "config.json")) as configFile:
    config = json.load(configFile)
with open(os.path.join(configDir, config["secretsJson"])) as secretsJson:
    config["secrets"] = json.load(secretsJson)

# Create the layout for the app
appLayout = Dashboard(app=app, config=config)
appLayout.setAppLayout()
app.run_server(debug=True)
