# hope-green-path-server

## Tech
* Python (3.6)
* Shapely
* GeoPandas
* NetworkX (+ OSMnx)
* Flask

## Materials
* [Traffic noise zones in Helsinki 2017](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017)
* [OpenStreetMap](https://www.openstreetmap.org/about/)

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
