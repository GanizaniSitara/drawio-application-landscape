# Capability and Application Landscape in Draw.io

Takes a CSV of applications and renders it as a Draw.io landscape diagram, for embedding
in Confluence or standalone use.

Landscape maps are usually drawn by hand, which means they are stale the week after the
workshop and nobody can tell you what changed. Generating them from a CSV makes the data
the artefact and the diagram a view of it, so the map can be regenerated whenever the
underlying list moves.

Features:

* Colourisation by strategy (RAG)
* Colourisation by category (for example resilience category)
* Metrics, hosting and Harvey ball pictograms
* Three layers
* Self-adjusting to page width
* Optionally opens Draw.io automatically after each render

![Enterprise Capabilities](https://ganizanisitara.github.io/drawio-application-landscape/Enterprise_Capabilities.drawio.png)

![Application Diagram Builder](https://ganizanisitara.github.io/drawio-application-landscape/Application_Diagram_Builder.drawio.png)

### Usage

Clone the repo, install `pandas` and `lxml`, then run from the package directory:

```bash
cd drawio_application_landscape
python main.py ../examples/Application_Diagram_Builder.csv
```

The rendered `.drawio` file is written to the repository root, named after the input
file. To open it in Draw.io automatically, set `OPEN_IN_DRAWIO = True` and point
`DRAWIO_EXECUTABLE` at your installation, both in `config/config_script.py`.

`Enterprise_Capabilities.csv` is the other example. It has no pictogram columns, so it
needs `SHOW_PICTOGRAMS = False` in `config/config_diagram.py` to render.

The input columns are whatever the two example CSVs in `examples/` use — level 1 and
level 2 grouping, application name, a RAG status, and the optional pictogram columns
(hosting, arrows, Harvey ball percentage, links).

### Experiments

1. Try toggling the `SHOW_PICTOGRAMS` flag in `config/config_diagram.py` to bring in the
   Harvey balls, arrows and hosting platform icons
2. In Draw.io, open layers and toggle visibility to show RAG status in addition to
   resilience category colourisation

### Notes

Only L1 is tested at the moment. L0 would create a map one level higher than L1, but the
data is not in the example file.

### Licence

BSD 3-Clause. See [LICENSE](LICENSE).
