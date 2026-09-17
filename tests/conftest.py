import xml.etree.ElementTree as ET

import pytest
from lxml import etree

from drawio_application_landscape import drawio_tools
from drawio_application_landscape.config.config_diagram import DiagramConfig
from drawio_application_landscape.config.config_script import ScriptConfig

MINIMAL_CSV = (
    "Level1,Level2,AppName\n"
    "Trading,Pricing,Quote Engine\n"
    "Trading,Pricing,Curve Service\n"
    "Ops,Settlement,Ledger\n"
)

FULL_CSV = (
    "Level1,Level2,AppName,TC,StatusRAG,Resilience,HostingPercent,"
    "HostingPattern1,HostingPattern2,Arrow1,Arrow2,Link,Controls,DecommDate\n"
    "Trading,Pricing,Quote Engine,25,green,4,50,Azure,Linux,up,down,"
    "http://example.com/app,http://example.com/controls,2030-01\n"
)


@pytest.fixture(autouse=True)
def restore_config():
    """The renderer reads module level config, so put it back between tests."""
    pictograms = DiagramConfig.SHOW_PICTOGRAMS
    experimental = ScriptConfig.EXPERIMENTAL
    open_in_drawio = ScriptConfig.OPEN_IN_DRAWIO
    yield
    DiagramConfig.SHOW_PICTOGRAMS = pictograms
    ScriptConfig.EXPERIMENTAL = experimental
    ScriptConfig.OPEN_IN_DRAWIO = open_in_drawio


@pytest.fixture
def write_csv(tmp_path):
    def _write(content, name="landscape.csv"):
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return str(path)
    return _write


def read_model(drawio_path):
    """Decode a written .drawio back into its mxGraphModel."""
    tree = etree.parse(str(drawio_path))
    data = tree.findall(".//diagram")[0].text
    return ET.fromstring(drawio_tools.decode_diagram_data(data))


def layer_names(model):
    return [cell.get("value") for cell in model.findall('.//mxCell[@parent="0"]')
            if cell.get("value")]


def cells_on_layer(model, layer):
    layer_id = next(cell.get("id") for cell in model.findall('.//mxCell[@parent="0"]')
                    if cell.get("value") == layer)
    return model.findall(f'.//mxCell[@parent="{layer_id}"]')


def labels(cells):
    """Cell labels with the layout markup the renderer adds stripped off."""
    return [(cell.get("value") or "").replace("<br>", "") for cell in cells]
