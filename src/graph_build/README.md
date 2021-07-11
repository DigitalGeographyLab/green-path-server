# Graph build

## Graph format and attributes
For a graph file to be usable in Green Paths, it needs to be in the GraphML file format and feature at least the required edge and node attributes listed in the tables below. All possible edge and node attributes are defined (and described) in [common/igraph.py](../common/igraph.py).

### Node attributes
| Alias | Name | Type | Nullable | Description  |
| ------------- | ---- | ---- | --- | ----------- |
| geometry | geom | Shapely point geometry / WKT | no | Location of the node as a Shapely Point geometry (e.g. POINT (25498747.97 6676644.78)). |

### Edge attributes
| Alias | Name | Type | Nullable | Nodata value | Description  |
| ------------- | ---- | ---- | --- | --- | ----------- |
| id_ig | ii | int | no | | Unique ID of the edge |
| id_way | iw | string | no | | ID of the geometry of the edge (not all geometries are unique) |
| uv | uv | tuple | no | | IDs of the start and end nodes of the edge (e.g. (2046, 4576)) |
| geometry | geom | Shapely LineString geometry / WKT | yes | GEOMETRYCOLLECTION EMPTY | Projected geometry of the edge (e.g. LINESTRING (25498199 6677347, 25498191 6677339)). GP uses EPSG:3879 by default.|
| geom_wgs | geom_wgs | Shapely LineString geometry / WKT | yes | GEOMETRYCOLLECTION EMPTY | Geometry of the edge in WGS (EPSG:4326) coordinates (e.g. LINESTRING (24.967528 60.208895, 24.967381 60.208826)). |
| length | l | float | no | | Length of the edge in meters. |
| is_stairs | b_st | boolean | no | | A boolean variable indicating whether the edge represents stairs. |
| allows_biking | b_aw | boolean | no | | A boolean variable indicating whether the edge allows biking. |
| bike_safety_factor | bsf | float | no | | Biking safety factor of the edge (calculated by OTP based on OpenStreetMap tags of the edge) |
| noises | n | dictionary | yes | None | Exposures to different noise levels on the edge. Keys of the dictionary represent the lower boundaries of 5-dB noise level ranges (45-70 dB) and values exposures as meters. This attribute is not needed if quiet path routing is disabled from the configuration. |
| gvi | g | float | yes | None | Green view index  (GVI) of the edge (0-1). This attribute is not needed if green path routing is disabled from the configuration. |

```
// sample GraphML data
...
<node id="n1905">
  <data key="v_geom">POINT (25497688.29600531 6678110.889221223)</data>
</node>
...
<edge source="n2952" target="n4368">
  <data key="e_ii">1444</data>
  <data key="e_geom">LINESTRING (25497712.53494933 6677892.654694145, 25497714.36057202 6677921.944805327)</data>
  <data key="e_geom_wgs">LINESTRING (24.9587395 60.21378910000001, 24.9587721 60.214052)</data>
  <data key="e_l">29.347</data>
  <data key="e_b_st">0</data>
  <data key="e_b_ab">1</data>
  <data key="e_bsf">1.5</data>
  <data key="e_n">{65: 14.67348, 70: 14.67348}</data>
  <data key="e_uv">(2952, 4368)</data>
  <data key="e_iw">1095</data>
  <data key="e_g">0.23</data>
</edge>
...
```

## Building a custom graph: overview / demo
The scripts for building a custom graph are not generic enough to work for any geographical extent without modifications.
Localization is needed for adapting to available data sources, file types, nodata areas, projections etc.

However, it should be possible to construct a graph without noise and greenery data with considerably smaller effort by running just steps 1, 2 and 5. The package-level configurations (`config.py` files) need to be adjusted to match the local programming environment and data files/directories. Also the scripts may need some minor adjustments, such as setting an appropriate EPSG code for a local projected coordinate reference system.

### Running the tests
```
$ cd src
$ python -m pytest graph_build/tests/otp_graph_import/ -vv
$ python -m pytest graph_build/tests/graph_noise_join/ -vv
$ python -m pytest graph_build/tests/graph_green_view_join/ -vv
$ python -m pytest graph_build/tests/graph_export/ -vv
```

### Prerequisites
- Java Development Kit, preferably version 8 (AKA version 1.8)
- OpenStreetMap (OSM) data file for the area of interest in pbf file format
- Python environment defined in [env/conda-env.yml](../env/conda-env.yml)

### 1. Create initial street network graph from OSM with OpenTripPlanner

1. Place your OSM data file (*.pbf) to directory `graph_import/graph_data_in/`
2. `cd graph_import`
3. `sh osm_2_otp_2_csv.sh`

This should produce two files to the folder graph_import/graph_data_in: `edges.csv` and `nodes.csv`.

### 2. Import & re-build street network graph for Green Paths from CSV files
Demo: [otp_graph_import/otp_graph_import.py](./otp_graph_import/otp_graph_import.py)

### 3. Join noise data to street network graph (optional)
Demo: [graph_noise_join/noise_graph_join.py](./graph_noise_join/noise_graph_join.py)
(uses traffic noise data for HMA)

### 4. Join greenery data to street network graph (optional)
Demo: [graph_green_view_join/graph_green_view_join.py](./graph_green_view_join/graph_green_view_join.py)
(requires PostGIS, uses land cover and green view index data for HMA)

### 5. Export graph to GraphML file with only required attributes
Demo: [graph_export/main.py](./graph_export/main.py)

## Environmental data for Helsinki Metropolitan Area (HMA)
* [SYKE - Traffic noise modelling data from Helsinki urban region](https://www.syke.fi/en-US/Open_information/Spatial_datasets/Downloadable_spatial_dataset#E)
* [Traffic noise zones in Helsinki 2017](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017)
* [OpenStreetMap](https://www.openstreetmap.org/about/)
* [Green View Index (GVI) point data](https://doi.org/10.1016/j.dib.2020.105601)
* [Land cover data](https://hri.fi/data/fi/dataset/paakaupunkiseudun-maanpeiteaineisto)
