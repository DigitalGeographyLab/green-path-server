# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 16:38:00 2019


DESCRIPTION
===========
This file contains utility functions to extract allPollutants netCDF files
downloaded from Enfuser AWS and converting them to georeferenced rasters.


NOTES
=====
The output path for extracting the zips doesn't need to exist before running
the function.

xarray and rioxarray automatically scale and offset each netCDF file opened
with proper values from the file itself. No manual scaling or adding offset
required.


@author: tuomvais
"""
import zipfile
import rioxarray
import xarray

def extract_zipped_aqi(zippedfile, outpath):
    
    # read zip file in
    archive = zipfile.ZipFile(zippedfile, 'r')
    
    # loop over files in zip archive
    for file in archive.namelist():
        
        # extract only files with allPollutants string match
        if 'allPollutants' in file:
            archive.extract(file, outpath)

def aqi_to_raster(inputfile, outputfile):
    
    # Read .nc file containing the AQI layer as multimensional array
    data = xarray.open_dataset(inputfile, 'r+', format='NETCDF4')
    
    # set crs for dataset to WGS84
    data.rio.set_crs('epsg:4326')
    
    # Retrieve AQI, AQI.data has shape (time, lat, lon)
    # the values are automatically scaled and offset AQI values
    AQI = data['AQI']
    
    # save AQI to raster
    AQI.rio.to_raster(outputfile)
