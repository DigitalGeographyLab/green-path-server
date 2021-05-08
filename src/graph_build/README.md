## Prerequisites
- Java Development Kit, preferably version 8 (AKA version 1.8)

## How to generate street network graph data from OSM with OpenTripPlanner?

1. Place your OSM data file (*.pbf) to directory `graph_import/graph_data_in/`
2. `cd graph_import`
3. `sh osm_2_otp_2_csv.sh`

This should produce two files to the folder graph_import/graph_data_in: `edges.csv` and `nodes.csv`.
