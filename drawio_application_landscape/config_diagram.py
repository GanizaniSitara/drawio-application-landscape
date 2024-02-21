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


    MAX_PAGE_WIDTH = {
        # "L0": 1600,
        "L1": 1280,
    }


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

    RESILIENCE_COLORS = {
            0: {'fillColor': '#ECF3FD', 'strokeColor': '#6C8EBF'},
            1: {'fillColor': '#FFFFFF', 'strokeColor': '#10739E'},
            2: {'fillColor': '#b1ddf0', 'strokeColor': '#10739e'},
            3: {'fillColor': '#f9f7ed', 'strokeColor': '#36393d'},
            4: {'fillColor': '#dae8fc', 'strokeColor': '#6c8ebf'}
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
        # "L0": "#000000",
        "L1": "#FF0000",
        "L2": "#00FF00",
        "App": "#0000FF",
    }



