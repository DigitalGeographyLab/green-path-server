import zipfile
import rioxarray
import xarray
import boto3
import pandas as pd
import datetime
import rasterio
from datetime import datetime

class AqiProcessor:
    """
    An instance of this class can download, extract and convert air quality index (AQI) data from 
    FMI's Enfuser model. Specifically, it can download the data as a zip archive file, extract a netCDF 
    file containing the air quality index layer and convert it into a GeoTIFF raster.

    Notes:
        The required python environment for using the class can be installed with: conda env create -f env_aqi_processing.yml
        Add file credentials.csv containing the required aws secrets to src/.
    """

    def _init_(self):
        self.bucketname = 'enfusernow2'
        self.region = 'eu-central-1'
        self.AWS_ACCESS_KEY_ID: str = ''
        self.AWS_SECRET_ACCESS_KEY: str = ''

    def set_aws_secrets(self):
        creds = pd.read_csv('credentials.csv', sep=',', encoding='utf-8')
        self.AWS_ACCESS_KEY_ID = creds['Access key ID'][0]
        self.AWS_SECRET_ACCESS_KEY = creds['Secret access key'][0]

    def fetch_enfuser(self, outpath):
        """Downloads a current zip file containing multiple netcdf files to a directory. 
        Do not type a filename for the output as the filename is automatically defined by the function.
        """
        # connect to S3
        s3 = boto3.client('s3',
                        region_name=self.region,
                        aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)
        
        # define a key based on the current time
        curdt = datetime.now().strftime('%Y-%m-%dT%H')
        key = 'Finland/pks/allPollutants_' + curdt + '.zip'
        
        # download the netcdf file to a specified location
        filename = 'allPollutants_' + curdt + '.zip'
        file_out = outpath + '/' + filename
        s3.download_file(key, file_out, Bucket=self.bucketname)

    def extract_zipped_aqi(self, zippedfile, outpath):
        """Extracts the contents of a zip file containing netcdf files. 
        """
        # read zip file in
        archive = zipfile.ZipFile(zippedfile, 'r')
        
        # loop over files in zip archive
        for file in archive.namelist():
            # extract only files with allPollutants string match
            if 'allPollutants' in file:
                # extract selected file to outpath directory
                archive.extract(file, outpath)

    def aqi_to_raster(self, inputfile, outputfile):
        """Converts the netCDF file to a georeferenced raster file. xarray and rioxarray automatically scale  and offset 
        each netCDF file opened with proper values from the file itself. No manual scaling or adding offset required.
        CRS of the exported GeoTiff is set to WGS84.
        """
        
        # Read .nc file containing the AQI layer as multidimensional array
        data = xarray.open_dataset(inputfile)
                
        # Retrieve AQI, AQI.data has shape (time, lat, lon)
        # the values are automatically scaled and offset AQI values
        AQI = data['AQI']
        AQI = AQI.rio.set_crs('epsg:4326')
        print('AQI crs', AQI.rio.crs)
        
        # save AQI to raster (.tif geotiff file recommended)
        AQI.rio.to_raster(outputfile)
