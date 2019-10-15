# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 16:38:00 2019


DESCRIPTION
===========
This file contains utility functions to download, extract and convert air quality
data from FMI's Enfuser model. Specifically, there is a function to download a
zip archive file, extract a netCDF file containing an air quality index layer
and converting the layer into a GeoTIFF.

REQUIREMENTS
============
Libraries:
    zipfile
    rioxarray
    xarray
    boto3
    
Other:
    AWS credentials
    Access/download privileges to your AWS S3 bucket

NOTES
=====
fetch_enfuser downloads a current zip file containing multiple netcdf files to
a directory. Do not type a filename for the output as the filename is
automatically defined by the function.

extract_zip_aqi opens the downloaded zip file from fetch_enfuser and extracts
only the AllPollutants netCDF file. The output path for extract_zip_aqi doesn't
need to exist before running the function.

aqi_to_raster converts the netCDF file to a georeferenced raster file.
xarray and rioxarray automatically scale and offset each netCDF file opened
with proper values from the file itself. No manual scaling or adding offset
required.


@author: tuomvais
"""
import zipfile
import rioxarray
import xarray
import boto3

# set bucket parameters
bucketname = 'enfusernow2'
region = 'eu-central-1'
wgs84wkt = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,' \
'AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]], PRIMEM["Greenwich",0,' \
'AUTHORITY["EPSG","8901"]],UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],' \
'AUTHORITY["EPSG","4326"]]'

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
            
            # extract selected file to outpath directory
            archive.extract(file, outpath)

def aqi_to_raster(inputfile, outputfile):
    
    # Read .nc file containing the AQI layer as multidimensional array
    data = xarray.open_dataset(inputfile)
    
    # set crs for dataset to WGS84
    data.rio.set_crs(wgs84wkt)
    
    # Retrieve AQI, AQI.data has shape (time, lat, lon)
    # the values are automatically scaled and offset AQI values
    AQI = data['AQI']
    
    # save AQI to raster (.tif geotiff file recommended)
    AQI.rio.to_raster(outputfile)
