# hope-green-path-server

## General
Green Path is an open source route planner developed in Urban Innovative Action **HOPE** – Healthy Outdoor Premises for Everyone. It informs people on clean routes for walking and cycling in the Greater Helsinki urban region. It is based on Air Quality Index (AQI) of the Enfuser model that is developed by the Finnish Meteorological Institute. AQI involves hourly updated and combined information on NO2, PM2.5, PM10 and O3. 

Currently implemented features include calculation of quiet paths with respect to typical daytime traffic noise levels. [Live demo](https://quietpath.web.app/)

## Materials
* [FMI Enfuser model](https://en.ilmatieteenlaitos.fi/environmental-information-fusion-service)
* [HOPE project](https://ilmanlaatu.eu/briefly-in-english/)
* [OpenStreetMap](https://www.openstreetmap.org/about/) 
* [Traffic noise zones in Helsinki 2017](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017)

## Tech
* Python (3.6)
* Shapely
* GeoPandas
* NetworkX (+ OSMnx)
* Flask

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
