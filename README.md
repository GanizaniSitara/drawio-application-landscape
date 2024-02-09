# Drawio Application Landscape Builder

Creates and application landscape map with commonly used enterpriseapplication metadata, 
such as Resilience Category, Cease Date, Transaction Cycle and others.

### Usage

Clone the repo then:

1) Update the DRAWIO_EXECUTABLE in the pyMX.py file to point to your drawio executable
2) Run the following command to generate the application landscape map

```bash
python pyMX.py examples\Application_Diagram_Builder.csv
```

### Experiments

1. Try toggling the SHOW_PICTOGRAMS flag in config.py to bring in the Harvey Balls, Arrows and Hosting Platform Icons
2. In Drawio, open layers and toggle visbility to show RAG status in addition to Resilience Category colourization

### Notes
Only L1 is tested at the moment. L0 would create a map one level higher than L1, but the data is not in the example file.
  