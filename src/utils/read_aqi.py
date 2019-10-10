# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 16:38:00 2019


DESCRIPTION
===========
This file contains utility functions to extract allPollutants netCDF files
downloaded from Enfuser AWS and converting them to georeferenced rasters.


NOTES
=====
fetch_enfuser downloads a current zip file containing multiple netcdf files.

The output path for extract_zip_aqi doesn't need to exist before running
the function.

xarray and rioxarray automatically scale and offset each netCDF file opened
with proper values from the file itself. No manual scaling or adding offset
required.


@author: tuomvais
"""
import zipfile
import rioxarray
import xarray
import boto3

# set bucket's name
bucketname = 'enfusernow2'

def fetch_enfuser(outpath):
    # set up the connection to S3
    s3 = boto3.client('s3',
                      region_name=region,
                      aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    # get current time
    curdt = datetime.now.strftime('%Y-%m-%dT%H')
    
    # define key of current time
    key = 'Finland/pks/allPollutants_' + curdt + '.zip'
    
    # set save name for file
    filename = 'allPollutants_' + curdt + '.zip'
    
    # finalize save path
    outpath = outpath + '/' + filename
    
    # download file to current directory
    s3.download_file(Bucket=bucketname, key, outpath)

def extract_zipped_aqi(zippedfile, outpath):
    
    # read zip file in
    archive = zipfile.ZipFile(zippedfile, 'r')
    
    # loop over files in zip archive
    for file in archive.namelist():
        
        # extract only files with allPollutants string match
        if 'allPollutants' in file:
            archive.extract(file, outpath)

def aqi_to_raster(inputfile, outputfile):
    
    # Read .nc file containing the AQI layer as multidimensional array
    data = xarray.open_dataset(inputfile, 'r+', format='NETCDF4')
    
    # set crs for dataset to WGS84
    data.rio.set_crs('epsg:4326')
    
    # Retrieve AQI, AQI.data has shape (time, lat, lon)
    # the values are automatically scaled and offset AQI values
    AQI = data['AQI']
    
    # save AQI to raster
    AQI.rio.to_raster(outputfile)
