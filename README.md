# Capability and Application Landscape in Draw.io

Takes a CSV of applications and renders it as a layered Draw.io landscape diagram, for
embedding in Confluence or standalone use.

Landscape maps are usually drawn by hand, which means they are stale the week after the
workshop and nobody can say what changed. Generating them from a CSV makes the data the
artefact and the diagram a view of it: the spreadsheet is what people argue about and
maintain, and the map is regenerated from it.

The output is layered, which is the part that makes it useful in a review. The same
applications are drawn once and coloured several ways — strategy RAG, resilience
category, hosting, controls, trend — each on its own Draw.io layer. Turning layers on and
off answers a different question from the same picture.

![Enterprise Capabilities](https://ganizanisitara.github.io/drawio-application-landscape/Enterprise_Capabilities.drawio.png)

![Application Diagram Builder](https://ganizanisitara.github.io/drawio-application-landscape/Application_Diagram_Builder.drawio.png)

## Installation

```
pip install -e .
```

That puts a `landscape` command on the path.

## Usage

```
landscape examples/Application_Diagram_Builder.csv
```

The diagram is written next to the input file unless `-o` says otherwise. Exit codes are
`0` when a diagram was written, `2` when the CSV cannot be used, and `1` when rendering
itself fails, so this can run unattended.

| Option | Effect |
|---|---|
| `-o`, `--output` | Where to write the `.drawio` file |
| `--no-pictograms` | Omit the hosting, control and metric pictograms, giving a plainer map |
| `--partial-views` | Also write one diagram per level 1 and per level 2 grouping, for slides |
| `--open` | Open the result in draw.io when done |
| `--drawio-path` | Where draw.io is installed, used by `--open` |
| `--no-experimental` | Disable the page width packing that restacks groupings too wide for a page |
| `-v`, `--verbose` | Verbose logging |

## The CSV

Three columns are required. They are the grouping and the identity of each row:

| Column | Meaning |
|---|---|
| `Level1` | Outer grouping, for example a business area |
| `Level2` | Inner grouping within the level 1 |
| `AppName` | The application, one row each |

Everything else is optional, and each optional column switches on one layer or one
pictogram. A CSV with only the three required columns renders a plain grouped map.

| Column | Drives |
|---|---|
| `StatusRAG` | `red`, `amber` or `green` — colours the application on the Strategy layer |
| `Resilience` | `0`-`4` — colours it on the Resilience layer. `Category` is accepted as an alias |
| `TC` | A transaction cycle label, shown on the TransactionCycle layer |
| `Link` | Hyperlink on the application box |
| `Controls` | Hyperlink, and draws the padlock pictogram on the Controls layer |
| `HostingPercent` | `0`-`100` — Harvey ball on the Hosting layer |
| `HostingPattern1`, `HostingPattern2` | Hosting icons, for example `Azure`, `AWS`, `Linux`, `WindowsVM`, `OpenShift` |
| `Arrow1`, `Arrow2` | `up` or `down` — trend arrows on the Metrics layer |
| `DecommDate` | `YYYY-MM` — drawn as a cease date, coloured by how close it is |

Columns the renderer does not know about are reported and ignored, so extra data can live
in the same spreadsheet.

The two files in `examples/` show both ends of this: `Application_Diagram_Builder.csv`
uses every optional column, `Enterprise_Capabilities.csv` uses a handful.

## Reading it in draw.io

Open the output and use the layers panel. `Applications` is the base map; `Strategy`,
`Resilience`, `Hosting`, `Metrics` and `Controls` each recolour or annotate it. Showing
`Strategy` and `Resilience` together is the usual starting point — it puts investment
intent next to resilience posture on one page.

## Using it as a library

```python
from drawio_application_landscape import main as renderer

output = renderer.main("landscape.csv", output="landscape.drawio")
```

`renderer.main` raises `InvalidInput` with a message naming the file, column or row when
the CSV cannot be rendered.

## Tests

```
pip install -e ".[dev]"
python -m pytest tests -q
```

The suite renders CSVs, decodes the `.drawio` back into its model and asserts on what is
on each layer, rather than comparing files — element ids are random, so a golden file
would only ever test the random number generator.

## Limitations

- Only L1 is supported. L0 would add a further level of aggregation above it; the
  renderer was never finished and no example data carries the extra level.
- Layout is packing-based, not a graph layout: it places groupings left to right and
  wraps at the page width. Very uneven group sizes produce whitespace.
- Application names must be unique within a level 2 grouping.

## Licence

BSD 3-Clause. See [LICENSE](LICENSE).
