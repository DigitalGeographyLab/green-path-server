# hope-green-path-server

This project is used as a backend for the web map application of the Green Paths route planner: [green-paths.web.app](https://green-paths.web.app/) / [DigitalGeographyLab/hope-green-path-ui](https://github.com/DigitalGeographyLab/hope-green-path-ui).

Green Paths is an open source route planner being developed by Digital Geography Lab, University of Helsinki, for the project [HOPE](https://ilmanlaatu.eu/briefly-in-english/) – Healthy Outdoor Premises for Everyone funded by [Urban Innovative Action](https://www.uia-initiative.eu/en). Its goal is to inform people on clean air and quite routes for walking and cycling in Helsinki region. It utilizes Air Quality Index (AQI) data from the [FMI-ENFUSER](https://en.ilmatieteenlaitos.fi/environmental-information-fusion-service) modelling system (by the Finnish Meteorological Institute) and modelled [traffic noise data](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017) from the city of Helsinki. AQI is based on real-time hourly data as a composite measure of NO2, PM2.5, PM10 and O3. 

Currently implemented features include calculation of walkable unpolluted and quiet paths with respect to real-time air quality and typical traffic noise levels. The exposure-based routing method (and application) is based on [an MSc thesis](https://github.com/hellej/quiet-paths-msc). 

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
$ git clone git@github.com:DigitalGeographyLab/hope-green-path-server.git
$ cd hope-green-path-server/src

# create Python environment with Conda
$ conda env create -f conda-env.yml
```

## Running the server locally
```
$ conda activate gp-env

$ export GRAPH_SUBSET=True
$ gunicorn --workers=1 --bind=0.0.0.0:5000 --log-level=info --timeout 450 green_paths_app:app

# or
$ sh start-application.sh
```

## Running the tests
```
WIP
```
