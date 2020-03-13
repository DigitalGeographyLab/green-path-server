# hope-green-path-server

## General
This project is used as a backend for the web map application of the Green Paths route planner: [green-paths.web.app](https://green-paths.web.app/) / [github.com/DigitalGeographyLab/hope-green-path-ui](https://github.com/DigitalGeographyLab/hope-green-path-ui).

Green Paths is an open source route planner being developed by Digital Geography Lab, University of Helsinki, for the project [HOPE](https://ilmanlaatu.eu/briefly-in-english/) – Healthy Outdoor Premises for Everyone funded by [Urban Innovative Action](https://www.uia-initiative.eu/en). Its goal is to inform people on clean air and quite routes for walking and cycling in Helsinki region. It utilizes Air Quality Index (AQI) data from the [FMI-ENFUSER](https://en.ilmatieteenlaitos.fi/environmental-information-fusion-service) modelling system (by the Finnish Meteorological Institute) and modelled [traffic noise data](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017) from the city of Helsinki. AQI is based on real-time hourly data as a composite measure of NO2, PM2.5, PM10 and O3. 

Currently implemented features include calculation of walkable unpolluted and quiet paths with respect to real-time air quality and typical traffic noise levels. The exposure-based routing method (and application) is based on [an MSc thesis](https://github.com/hellej/quiet-paths-msc). 

## Green paths routing API
See [docs/green_paths_api.md](docs/green_paths_api.md) for detailed documentation of the green paths routing API and the schema of the paths. 

## Materials
* [Green Paths project website](https://www.helsinki.fi/en/researchgroups/digital-geography-lab/green-paths)
* [UIA HOPE project](https://ilmanlaatu.eu/briefly-in-english/)
* [FMI-Enfuser model](https://en.ilmatieteenlaitos.fi/environmental-information-fusion-service)
* [SYKE - Traffic noise modelling data from Helsinki urban region](https://www.syke.fi/en-US/Open_information/Spatial_datasets/Downloadable_spatial_dataset#E)
* [Traffic noise zones in Helsinki 2017](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017)
* [OpenStreetMap](https://www.openstreetmap.org/about/) 

## Tech
* Python 3.6
* igraph
* NetworkX
* GeoPandas
* Shapely
* Flask & Gunicorn

## Installation
```
$ git clone git@github.com:DigitalGeographyLab/hope-green-path-server.git
$ cd hope-green-path-server/src

# create an environment for graph construction
$ conda env create -f env_graph_construction.yml

# create an environment for aqi processor
$ conda env create -f env_aqi_processing.yml

# create an environment for green path server
$ conda env create -f env_gp_server.yml
```

## Running the server locally
```
$ conda activate gp-server

# run with gunicorn (recommended)
$ gunicorn --workers=1 --bind=0.0.0.0:5000 --log-level=info --timeout 160 green_paths_app:app

# or with python as a simple flask application
$ python green_paths_app.py
```

## Running the tests
```
$ cd hope-green-path-server/src
$ conda activate gp-server

$ python test_green_paths_app.py -b
$ python test_utils.py -b

$ conda activate aqi-processing
$ python test_aqi_processor.py -b
```
