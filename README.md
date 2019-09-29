# hope-green-path-server

## General
Green Path is an open source route planner being developed for [Urban Innovative Action](https://www.uia-initiative.eu/en), [HOPE](https://www.uia-initiative.eu/en/uia-cities/helsinki) – Healthy Outdoor Premises for Everyone. Its goal is to inform people on clean routes for walking and cycling in Helsinki region. It utilizes Air Quality Index (AQI) from the Enfuser model (by the Finnish Meteorological Institute) and modelled traffic noise data. AQI is based on hourly updated and combined information on NO2, PM2.5, PM10 and O3. 

Currently implemented features include calculation of walkable quiet paths with respect to typical daytime traffic noise levels ([Live demo](https://quietpath.web.app/)). The quiet path optimization method (and application) is based on [an MSc thesis](https://github.com/hellej/quiet-paths-msc). 

## Materials
* [FMI Enfuser model](https://en.ilmatieteenlaitos.fi/environmental-information-fusion-service)
* [HOPE project](https://ilmanlaatu.eu/briefly-in-english/)
* [OpenStreetMap](https://www.openstreetmap.org/about/) 
* [Traffic noise zones in Helsinki 2017](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017)

## Tech
* Python (3.6)
* NetworkX
* GeoPandas
* Shapely
* Flask & Gunicorn

## Installation
```
$ git clone git@github.com:DigitalGeographyLab/hope-green-path-server.git
$ cd hope-green-path-server/src

$ conda env create -f env-gis-flask.yml
$ conda activate gis-flask
```

## Running the tests
```
$ cd hope-green-path-server/src
$ conda activate gis-flask
$ python -m pytest test_utils.py
$ python test_quiet_paths_app.py
```
