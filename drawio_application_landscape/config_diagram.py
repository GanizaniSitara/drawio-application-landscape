#
# Description: This file contains the configuration for the application landscape diagram.
#
# Usage:
#
# color_level1 = DiagramConfig.COLORS["L1"]



class DiagramConfig:
    def __init__(self):
        pass

    SHOW_PICTOGRAMS = False

    CONFIG = {
        "DEFAULT": {
            "fontFamily": "Arial",
            "fontSize": "12",
            "fontColor": "#333333",
            "strokeColor": "none",
            "fillColor": "#D6D6D6",
            "verticalAlign": "top",
            "align": "center",
            "spacingTop": "0",
            "spacingLeft": "0",
            "fontStyle": "0",
        },
        "L1": {
            "fontFamily": "Helvetica",
            "fontSize": "24",
            "fontStyle": "3",
            "align": "left",
            "spacingLeft": "10",
            "spacingTop": "3",
            "whiteSpace": "wrap",
        },
        "L2": {
            "fontSize": "18",
        },
        "App": {
            "fontSize": "14",
        },

    }

    HEADER_HEIGHT = {
        "L1": 50,
        "L2": 50,
    }

    @staticmethod
    def get_style(level):
        default_style = DiagramConfig.CONFIG.get("DEFAULT", {})
        level_style = DiagramConfig.CONFIG.get(level, {})
        combined_style = {**default_style, **level_style}
        return  ';'.join(f"{k}={v}" for k, v in combined_style.items())


    COLORS = {
        "L0": "#000000",
        "L1": "#FF0000",
        "L2": "#00FF00",
        "App": "#0000FF",
    }

    MAX_PAGE_WIDTH = {
        "L0": 1600,
        "L1": 1600,
    }



