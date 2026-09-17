"""Command line interface for the application landscape renderer."""
import argparse
import logging
import os
import sys

from drawio_application_landscape import main as renderer
from drawio_application_landscape.config.config_diagram import DiagramConfig
from drawio_application_landscape.config.config_script import ScriptConfig

EXIT_OK = 0
EXIT_RENDER_FAILED = 1
EXIT_INVALID_INPUT = 2


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(
        prog='landscape',
        description='Render an application landscape diagram from a CSV.')
    parser.add_argument('input', help='CSV describing the landscape')
    parser.add_argument(
        '-o', '--output',
        help='output .drawio file (default: alongside the input)')
    parser.add_argument(
        '--no-pictograms', action='store_true',
        help='omit the hosting, control and metric pictograms')
    parser.add_argument(
        '--partial-views', action='store_true',
        help='also write a diagram per level 1 and level 2 grouping')
    parser.add_argument(
        '--open', action='store_true', dest='open_output',
        help='open the result in draw.io')
    parser.add_argument(
        '--drawio-path', default=ScriptConfig.DRAWIO_EXECUTABLE,
        help='path to the draw.io executable, used by --open')
    parser.add_argument(
        '--no-experimental', action='store_true',
        help='disable the page width packing that restacks wide groupings')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose logging')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_arguments(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s %(message)s')

    if args.no_pictograms:
        DiagramConfig.SHOW_PICTOGRAMS = False
    if args.no_experimental:
        ScriptConfig.EXPERIMENTAL = False
        renderer.EXPERIMENTAL = False
    ScriptConfig.OPEN_IN_DRAWIO = args.open_output
    ScriptConfig.DRAWIO_EXECUTABLE = args.drawio_path

    try:
        output = renderer.main(args.input, output=args.output,
                               partial_views=args.partial_views)
    except renderer.InvalidInput as exc:
        print(f'error: {exc}', file=sys.stderr)
        return EXIT_INVALID_INPUT
    except Exception as exc:  # a layout or serialisation failure
        print(f'error: could not render {args.input}: {exc}', file=sys.stderr)
        return EXIT_RENDER_FAILED

    print(os.path.relpath(output))
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
