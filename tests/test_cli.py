"""The command line contract: what it accepts, and what it exits with."""
import os

from conftest import MINIMAL_CSV, read_model
from drawio_application_landscape.cli import (EXIT_INVALID_INPUT, EXIT_OK, main)
from drawio_application_landscape.config.config_diagram import DiagramConfig


def test_renders_and_exits_zero(write_csv, tmp_path):
    csv = write_csv(MINIMAL_CSV)
    assert main([csv, '-o', str(tmp_path / 'out.drawio')]) == EXIT_OK
    assert (tmp_path / 'out.drawio').exists()


def test_missing_required_column_exits_two(write_csv, capsys):
    csv = write_csv('Level1,AppName\nTrading,Quote Engine\n')
    assert main([csv]) == EXIT_INVALID_INPUT
    assert 'Level2' in capsys.readouterr().err


def test_missing_file_exits_two(capsys):
    assert main(['no-such-file.csv']) == EXIT_INVALID_INPUT
    assert 'no such file' in capsys.readouterr().err


def test_empty_csv_exits_two(write_csv):
    assert main([write_csv('Level1,Level2,AppName\n')]) == EXIT_INVALID_INPUT


def test_out_of_range_resilience_names_the_application(write_csv, capsys):
    csv = write_csv('Level1,Level2,AppName,Resilience\nTrading,Pricing,Quote Engine,9\n')
    assert main([csv]) == EXIT_INVALID_INPUT
    assert 'Quote Engine' in capsys.readouterr().err


def test_duplicate_application_names_the_row(write_csv, capsys):
    csv = write_csv('Level1,Level2,AppName\nTrading,Pricing,Quote Engine\n'
                    'Trading,Pricing,Quote Engine\n')
    assert main([csv]) == EXIT_INVALID_INPUT
    error = capsys.readouterr().err
    assert 'row 3' in error and 'Quote Engine' in error


def test_unknown_columns_are_ignored_not_fatal(write_csv, tmp_path):
    csv = write_csv('Level1,Level2,AppName,Whatever\nTrading,Pricing,Quote Engine,x\n')
    assert main([csv, '-o', str(tmp_path / 'out.drawio')]) == EXIT_OK


def test_no_pictograms_flag(write_csv, tmp_path):
    csv = write_csv(MINIMAL_CSV)
    main([csv, '-o', str(tmp_path / 'out.drawio'), '--no-pictograms'])
    assert DiagramConfig.SHOW_PICTOGRAMS is False


def test_does_not_launch_drawio_unless_asked(write_csv, tmp_path, monkeypatch):
    """The renderer used to shell out to draw.io on every run."""
    launched = []
    monkeypatch.setattr(os, 'system', lambda command: launched.append(command))
    main([write_csv(MINIMAL_CSV), '-o', str(tmp_path / 'out.drawio')])
    assert launched == []


def test_output_path_is_reported_on_stdout(write_csv, tmp_path, capsys):
    main([write_csv(MINIMAL_CSV), '-o', str(tmp_path / 'out.drawio')])
    assert 'out.drawio' in capsys.readouterr().out
