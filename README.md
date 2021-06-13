[![tests & build status](https://github.com/DigitalGeographyLab/hope-green-path-server/workflows/Tests%20%26%20Build/badge.svg)](https://github.com/DigitalGeographyLab/hope-green-path-server/actions) [![Graph building](https://github.com/DigitalGeographyLab/hope-green-path-server/actions/workflows/test-graph-building.yml/badge.svg)](https://github.com/DigitalGeographyLab/hope-green-path-server/actions/workflows/test-graph-building.yml)

# hope-green-path-server

Green path server is the routing service of the Green Paths route planner: [green-paths.web.app](https://green-paths.web.app/) / [DigitalGeographyLab/hope-green-path-ui](https://github.com/DigitalGeographyLab/hope-green-path-ui). Its goal is to help people find routes of fresh air, less noise and more greenery for walking and cycling in the Helsinki capital region. Also, it provides means for researchers to study citizens travel-time exposure to environmental qualities and to assess presence of healthier routes in different areas. 

The route planner is being developed by Digital Geography Lab, University of Helsinki, currently within the project [UIA HOPE](https://ilmanlaatu.eu/briefly-in-english/) – Healthy Outdoor Premises for Everyone funded by [Urban Innovative Action](https://www.uia-initiative.eu/en/uia-cities/helsinki). It utilizes the experimental air quality index data, AQI 2.0, from the [FMI-ENFUSER](https://en.ilmatieteenlaitos.fi/environmental-information-fusion-service) modelling system developed by the Finnish Meteorological Institute. AQI 2.0 is based on real-time hourly data as a composite measure of NO2, PM2.5, PM10, O3, black carbon and lung deposit surface area. The route planner applies modelled [noise data from road and rail traffic](www.syke.fi/en-US/Open_information/Spatial_datasets/Downloadable_spatial_dataset#E) according to the EU Environmental Noise Directive. Street level green view (i.e. greenery) data is derived from [analyzing Google Street View images](https://www.sciencedirect.com/science/article/pii/S2352340920304959?via%3Dihub) and openly available [land cover data by HRI](https://hri.fi/data/en_GB/dataset/paakaupunkiseudun-maanpeiteaineisto). 

Currently implemented features include calculation of unpolluted, green and quiet paths for walking or cycling (separately) with respect to real-time air quality, street level green view index and typical (day-evening-night) traffic noise levels. The exposure-based routing method (and application) is based on [an MSc thesis](https://github.com/hellej/quiet-paths-msc). 

## Content
- [Green paths routing API](#Green-paths-routing-API)
- [Related projects](#Related-projects)
- [Materials](#Materials)
- [Tech](#Tech)
- [Installation](#Installation)
- [Graph data](#Graph-data)
  - [Helsinki Metropolitan Area (HMA)](#Helsinki-Metropolitan-Area-HMA)
  - [Format & attributes](#format--attributes)
  - [Other geographical extents (graph building)](#Other-geographical-extents-graph-building)
- [Configuration](#Configuration)
- [Running the server locally: linux/osx](#Running-the-server-locally-linuxosx)
- [Running the server locally: win](#Running-the-server-locally-win)
- [Running the tests](#Running-the-tests)
- [Links](#Links)
- [Contributing](#Contributing)
- [License](#License)

## Green paths routing API
See [docs/green_paths_api.md](docs/green_paths_api.md) for documentation of the green paths routing API (endpoints and data types). 

## Related projects
- [hope-green-path-ui](https://github.com/DigitalGeographyLab/hope-green-path-ui)
- [hope-graph-builder](https://github.com/DigitalGeographyLab/hope-graph-builder)

## Materials
* [OpenStreetMap](https://www.openstreetmap.org/about/) 
* [FMI-Enfuser modeling system](https://en.ilmatieteenlaitos.fi/environmental-information-fusion-service)
* [SYKE - Traffic noise modeling data from Helsinki urban region](https://www.syke.fi/en-US/Open_information/Spatial_datasets/Downloadable_spatial_dataset#E)
* [Traffic noise zones in Helsinki 2017](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017)
* [Street-level green view index by Google Street View images](https://www.sciencedirect.com/science/article/pii/S2352340920304959?via%3Dihub)
* [Land cover data (low & high vegetation)](https://hri.fi/data/en_GB/dataset/paakaupunkiseudun-maanpeiteaineisto)

## Tech
* Python 3.8
* igraph
* GeoPandas
* Shapely
* Flask & Gunicorn

## Installation
```
$ git clone https://github.com/DigitalGeographyLab/hope-green-path-server.git
$ cd hope-green-path-server/src/env
```
**unix/osx**
```
$ conda env create -f conda-env.yml
```
**Windows**
```
> conda env create -f conda-env-win.yml
```
## Graph data

### Helsinki Metropolitan Area (HMA)
To run the server, download one or more of the following graph files to the folder `src/graphs`:
- [hma.graphml](https://a3s.fi/swift/v1/AUTH_c1dfd63531fb4a63a3927b1f237b547f/gp-data/hma.graphml)
- [hma_r.graphml](https://a3s.fi/swift/v1/AUTH_c1dfd63531fb4a63a3927b1f237b547f/gp-data/hma_r.graphml) (for research)
- [hma_r_hel-clip.graphml](https://a3s.fi/swift/v1/AUTH_c1dfd63531fb4a63a3927b1f237b547f/gp-data/hma_r_hel-clip.graphml) (for research)

The file `hma.graphml` covers the extent of the HMA (i.e. Helsinki, Espoo, Vantaa & Kauniainen), whereas `kumpula.graphml` is a small subset of the full graph intended for development and testing purposes (it is included in this repository).

### Format & attributes
To use street network graph data with Green Paths, it needs to be in the GraphML format and feature required node & edge attributes. The format and attributes of the graph data are described in [the documentation of the module graph_build](src/graph_build#Graph-format-and-attributes).

### Other geographical extents (graph building)
It is possible to construct a routing graph for any area from raw OpenStreetMap data (*.pbf). However, since data on traffic noise, greenery and air quality may not be available in the same format for other areas, some customized data processing and sampling are likely needed. See the module [graph_build](src/graph_build#Building-a-custom-graph) for more documentation on graph building.

## Configuration
A number of settings of the routing software can be adjusted from the configuration file: [src/gp_server/conf.py](src/gp_server/conf.py). The routing workflow and response schema are described in [docs/green_paths_api.md](docs/green_paths_api.md), including the differences in research mode. 

## Running the server locally: linux/osx
```
$ cd src
$ conda activate gp-env

$ export GRAPH_SUBSET=True
$ gunicorn --workers=1 --bind=0.0.0.0:5000 --log-level=info --timeout 450 gp_server_main:app

# or
$ sh start-gp-server.sh
```

## Running the server locally: win
In order to run the app on Windows, you must serve it with Flask as instructed in this chapter (Gunicorn cannot be installed on Windows).

For testing and development purposes, you can set the graph file as `kumpula.graphml` in [conf.py](src/gp_server/conf.py)

Start the application:
```
> cd src
> conda activate gp-env
> python gp_server_main.py
```

Now for example the following request should return some (quiet) paths as GeoJSON:
[http://localhost:5000/paths/walk/quiet/60.20772,24.96716/60.2037,24.9653](http://localhost:5000/paths/walk/quiet/60.20772,24.96716/60.2037,24.9653)

Learn how to use the API by reading [the documentation](docs/green_paths_api.md). 

## Running the tests
```
$ cd src
$ python -m pytest gp_server/tests_unit -v
$ python -m pytest gp_server/tests_api -v
$ python -m pytest aqi_updater/tests -v
```
## Links
* [Green Paths project website](https://www.helsinki.fi/en/researchgroups/digital-geography-lab/green-paths)
* [UIA HOPE project](https://ilmanlaatu.eu/briefly-in-english/)

## Contributing
* See also [CONTRIBUTING.md](CONTRIBUTING.md)
* Please bear in mind that the current objective of the project is to develop a proof-of-concept of a green path route planner rather than a production ready service
* You are most welcome to add feature requests or bug reports in the issue tracker
* When contributing to this repository, please first discuss the change you wish to make via issue,
email, or any other method with the owners of this repository before making a change (firstname.lastname@helsinki.fi)
* Simple typo fixes etc. can be sent as PRs directly, but for features or more complex bug fixes please add a corresponding issue first for discussion

## License
[MIT](LICENSE)
