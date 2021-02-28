[![API tests status](https://github.com/DigitalGeographyLab/hope-green-path-server/workflows/API%20tests/badge.svg)](https://github.com/DigitalGeographyLab/hope-green-path-server/actions)

# hope-green-path-server

This project is used as a backend for the web map application of the Green Paths route planner: [green-paths.web.app](https://green-paths.web.app/) / [DigitalGeographyLab/hope-green-path-ui](https://github.com/DigitalGeographyLab/hope-green-path-ui).

Green Paths is an open source route planner being developed by Digital Geography Lab, University of Helsinki, for the project [UIA HOPE](https://ilmanlaatu.eu/briefly-in-english/) – Healthy Outdoor Premises for Everyone funded by [Urban Innovative Action](https://www.uia-initiative.eu/en/uia-cities/helsinki). Its goal is to inform people on fresh air and quiet routes for walking and cycling in Helsinki region. It utilizes Air Quality Index (AQI) data from the [FMI-ENFUSER](https://en.ilmatieteenlaitos.fi/environmental-information-fusion-service) modelling system (by the Finnish Meteorological Institute) and modelled [traffic noise data](www.syke.fi/en-US/Open_information/Spatial_datasets/Downloadable_spatial_dataset#E) from the Helsinki capital region. AQI is based on real-time hourly data as a composite measure of NO2, PM2.5, PM10, SO2 and O3. 

Currently implemented features include calculation of unpolluted, green and quiet paths for walking or cycling (separately) with respect to real-time air quality, street level green view index and typical (day-evening-night time) noise levels from road and rail traffic. The exposure-based routing method (and application) is based on [an MSc thesis](https://github.com/hellej/quiet-paths-msc). 

## Green paths routing API
See [docs/green_paths_api.md](docs/green_paths_api.md) for detailed documentation of the green paths routing API. 

## Related projects
- [hope-green-path-ui](https://github.com/DigitalGeographyLab/hope-green-path-ui)
- [hope-graph-updater](https://github.com/DigitalGeographyLab/hope-graph-updater)
- [hope-graph-builder](https://github.com/DigitalGeographyLab/hope-graph-builder)

## Materials
* [Green Paths project website](https://www.helsinki.fi/en/researchgroups/digital-geography-lab/green-paths)
* [UIA HOPE project](https://ilmanlaatu.eu/briefly-in-english/)
* [FMI-Enfuser model](https://en.ilmatieteenlaitos.fi/environmental-information-fusion-service)
* [SYKE - Traffic noise modelling data from Helsinki urban region](https://www.syke.fi/en-US/Open_information/Spatial_datasets/Downloadable_spatial_dataset#E)
* [Traffic noise zones in Helsinki 2017](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017)
* [OpenStreetMap](https://www.openstreetmap.org/about/) 

## Contributing
* See also [CONTRIBUTING.md](CONTRIBUTING.md)
* Please bear in mind that the current objective of the project is to develop a proof-of-concept of a green path route planner rather than a production ready service
* You are most welcome to add feature requests or bug reports in the issue tracker
* When contributing to this repository, please first discuss the change you wish to make via issue,
email, or any other method with the owners of this repository before making a change (firstname.lastname@helsinki.fi)
* Simple typo fixes etc. can be sent as PRs directly, but for features or more complex bug fixes please add a corresponding issue first for discussion

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

[Download graph data](https://drive.google.com/file/d/1jM-CPjBZdIXjKnPMwB7k8NV3hGC63VkI/view?usp=sharing) and place the downloaded file (`hma.graphml`) in the directory `src/graphs`. 

The `hma.graphml` street network graph covers the Helsinki Metropolitan Area (i.e. Helsinki, Espoo, Vantaa & Kauniainen). The other graph file (`kumpula.graphml`) is a small subset of the full graph and can be used for development and testing purposes. 

## Running the server locally (linux/osx)
```
$ cd src
$ conda activate gp-env

$ export GRAPH_SUBSET=True
$ gunicorn --workers=1 --bind=0.0.0.0:5000 --log-level=info --timeout 450 gp_server_main:app

# or
$ sh start-gp-server.sh
```

## Running the server locally (win)
In order to run the app on Windows, you must serve it with Flask as instructed in this chapter (Gunicorn cannot be installed on Windows).

For testing and development purposes, you can set the graph file as `kumpula.graphml` in [conf.py](src/gp_server_conf.py)

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
$ python -m pytest gp_server/tests -v
$ python -m pytest aqi_updater/tests -v
```
