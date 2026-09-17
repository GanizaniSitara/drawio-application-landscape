"""What comes out of the renderer for a given CSV."""
import os

import pytest

from conftest import (FULL_CSV, MINIMAL_CSV, cells_on_layer, labels, layer_names,
                      read_model)
from drawio_application_landscape import main as renderer
from drawio_application_landscape.config.config_diagram import DiagramConfig

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'examples')


def test_minimal_csv_renders(write_csv, tmp_path):
    """Level1, Level2 and AppName are the only columns anyone must supply."""
    output = renderer.main(write_csv(MINIMAL_CSV), output=str(tmp_path / 'out.drawio'))
    assert os.path.exists(output)


def test_every_application_appears(write_csv, tmp_path):
    output = renderer.main(write_csv(MINIMAL_CSV), output=str(tmp_path / 'out.drawio'))
    applications = labels(cells_on_layer(read_model(output), 'Applications'))
    assert sorted(applications) == ['Curve Service', 'Ledger', 'Quote Engine']


def test_the_expected_layers_are_present(write_csv, tmp_path):
    output = renderer.main(write_csv(MINIMAL_CSV), output=str(tmp_path / 'out.drawio'))
    assert {'Applications', 'Strategy', 'Resilience', 'Hosting', 'Metrics',
            'Controls', 'TransactionCycle'} <= set(layer_names(read_model(output)))


def test_rag_status_colours_the_strategy_layer(write_csv, tmp_path):
    csv = MINIMAL_CSV.replace(
        'Level1,Level2,AppName\n', 'Level1,Level2,AppName,StatusRAG\n').replace(
        'Trading,Pricing,Quote Engine\n', 'Trading,Pricing,Quote Engine,red\n').replace(
        'Trading,Pricing,Curve Service\n', 'Trading,Pricing,Curve Service,green\n').replace(
        'Ops,Settlement,Ledger\n', 'Ops,Settlement,Ledger,amber\n')
    output = renderer.main(write_csv(csv), output=str(tmp_path / 'out.drawio'))

    styles = {}
    for cell in cells_on_layer(read_model(output), 'Strategy'):
        styles[(cell.get('value') or '').replace('<br>', '')] = cell.get('style') or ''

    assert DiagramConfig.STATUS_COLORS['red']['fillColor'] in styles['Quote Engine']
    assert DiagramConfig.STATUS_COLORS['green']['fillColor'] in styles['Curve Service']
    assert DiagramConfig.STATUS_COLORS['amber']['fillColor'] in styles['Ledger']


def test_category_is_accepted_as_an_alias_for_resilience(write_csv, tmp_path):
    """The two bundled examples use one name each for the same idea."""
    resilience_csv = ('Level1,Level2,AppName,Resilience\n'
                      'Trading,Pricing,Quote Engine,2\n')
    category_csv = ('Level1,Level2,AppName,Category\n'
                    'Trading,Pricing,Quote Engine,2\n')

    by_resilience = renderer.main(write_csv(resilience_csv, 'a.csv'),
                                  output=str(tmp_path / 'a.drawio'))
    by_category = renderer.main(write_csv(category_csv, 'b.csv'),
                                output=str(tmp_path / 'b.drawio'))

    expected = DiagramConfig.RESILIENCE_COLORS[2]['fillColor']
    for output in (by_resilience, by_category):
        styles = [cell.get('style') or ''
                  for cell in cells_on_layer(read_model(output), 'Resilience')]
        assert any(expected in style for style in styles)


def test_pictograms_are_drawn_when_the_columns_exist(write_csv, tmp_path):
    output = renderer.main(write_csv(FULL_CSV), output=str(tmp_path / 'out.drawio'))
    model = read_model(output)
    assert cells_on_layer(model, 'Hosting'), 'expected hosting pictograms'
    assert cells_on_layer(model, 'Metrics'), 'expected trend arrows'
    assert cells_on_layer(model, 'Controls'), 'expected a controls overlay'


def test_pictogram_columns_are_optional(write_csv, tmp_path):
    """Rendering a CSV without the pictogram columns used to raise KeyError."""
    output = renderer.main(write_csv(MINIMAL_CSV), output=str(tmp_path / 'out.drawio'))
    assert cells_on_layer(read_model(output), 'Hosting') == []


def test_pictograms_can_be_turned_off(write_csv, tmp_path):
    DiagramConfig.SHOW_PICTOGRAMS = False
    output = renderer.main(write_csv(FULL_CSV), output=str(tmp_path / 'out.drawio'))
    assert cells_on_layer(read_model(output), 'Hosting') == []


def test_output_defaults_to_beside_the_input(write_csv, tmp_path):
    output = renderer.main(write_csv(MINIMAL_CSV))
    assert output == str(tmp_path / 'landscape.drawio')


def test_partial_views_write_one_file_per_grouping(write_csv, tmp_path):
    renderer.main(write_csv(MINIMAL_CSV), output=str(tmp_path / 'out.drawio'),
                  partial_views=True)
    written = sorted(p.name for p in tmp_path.glob('*.drawio'))
    assert written == ['out.drawio', 'out_Ops.drawio', 'out_Ops_Settlement.drawio',
                       'out_Trading.drawio', 'out_Trading_Pricing.drawio']


@pytest.mark.parametrize('example', ['Application_Diagram_Builder.csv',
                                     'Enterprise_Capabilities.csv'])
def test_bundled_examples_render(example, tmp_path):
    """Enterprise_Capabilities used to die with KeyError: 'Controls'."""
    output = renderer.main(os.path.join(EXAMPLES, example),
                           output=str(tmp_path / 'out.drawio'))
    assert cells_on_layer(read_model(output), 'Applications')
