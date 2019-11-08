import zipfile
import rioxarray
import xarray
import boto3
import pandas as pd
import datetime
import rasterio
import numpy as np
from rasterio import fill
from datetime import datetime
import utils.geometry as geom_utils
from utils.graph_handler import GraphHandler
from typing import List, Set, Dict, Tuple, Optional

class AqiProcessor:
    """
    An instance of this class can download, extract and convert air quality index (AQI) data from 
    FMI's Enfuser model. Specifically, it can download the data as a zip archive file, extract a netCDF 
    file containing the air quality index layer and convert it into a GeoTIFF raster.

    Args:
        aqi_dif: The name of a directory where AQI files will be downloaded to and processed in.

    Notes:
        The required python environment for using the class can be installed with: conda env create -f env_aqi_processing.yml
        Add file credentials.csv containing the required aws secrets to src/
    """

    def __init__(self, aqi_dir: str = ''):
        self.aqi_dir = aqi_dir
        self.bucketname = 'enfusernow2'
        self.region = 'eu-central-1'
        self.AWS_ACCESS_KEY_ID: str = ''
        self.AWS_SECRET_ACCESS_KEY: str = ''

    def set_aws_secrets(self) -> None:
        creds = pd.read_csv('credentials.csv', sep=',', encoding='utf-8')
        self.AWS_ACCESS_KEY_ID = creds['Access key ID'][0]
        self.AWS_SECRET_ACCESS_KEY = creds['Secret access key'][0]

    def get_current_enfuser_key_filename(self) -> Tuple[str, str]:
        # define a filename and a key based on the current UTC time e.g. 2019-11-08T11
        curdt = datetime.utcnow().strftime('%Y-%m-%dT%H')
        key = 'Finland/pks/allPollutants_' + curdt + '.zip'
        filename = 'allPollutants_' + curdt + '.zip'
        return (key, filename)

    def fetch_enfuser_data(self, key: str, filename: str) -> str:
        """Downloads the current zip file containing multiple netcdf files to a directory. 
        
        Note:
            Filename for the exported zip file is defined by the function - only a folder name is needed as the outpath.
        Returns:
            The name of the extracted enfuser zip file.
        """
        # connect to S3
        s3 = boto3.client('s3',
                        region_name=self.region,
                        aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)
        
        key, aqi_zip = self.get_current_enfuser_key_filename()
        
        # download the netcdf file to a specified location
        file_out = self.aqi_dir + '/' + aqi_zip
        s3.download_file(key, file_out, Bucket=self.bucketname)
        return aqi_zip

    def extract_zipped_aqi(self, aqi_zip: str) -> str:
        """Extracts the contents of a zip file containing netcdf files. 

        Args:
            aqi_zip: The name of the zip file to be extracted from.

        Returns:
            The name of the extracted aqi nc file.
        """
        # read zip file in
        archive = zipfile.ZipFile(self.aqi_dir + aqi_zip, 'r')
        
        # loop over files in zip archive
        for file_name in archive.namelist():
            # extract only files with allPollutants string match
            if ('allPollutants' in file_name):
                # extract selected file to aqi_dir directory
                archive.extract(file_name, self.aqi_dir)
                aqi_nc = file_name
        
        return aqi_nc

    def convert_aqi_nc_to_raster(self, aqi_nc: str) -> str:
        """Converts a netCDF file to a georeferenced raster file. xarray and rioxarray automatically scale  and offset 
        each netCDF file opened with proper values from the file itself. No manual scaling or adding offset required.
        CRS of the exported GeoTiff is set to WGS84.

        Args:
            aqi_nc: e.g. allPollutants_2019-09-11T15.nc
        Returns:
            Name of the exported tiff file (e.g. allPollutants_2019-09-11T15.tif)
        """
        # read .nc file containing the AQI layer as a multidimensional array
        data = xarray.open_dataset(self.aqi_dir + aqi_nc)
                
        # retrieve AQI, AQI.data has shape (time, lat, lon)
        # the values are automatically scaled and offset AQI values
        aqi = data['AQI']

        # save AQI to raster (.tif geotiff file recommended)
        aqi = aqi.rio.set_crs('epsg:4326')

        raster_name = aqi_nc[:-3] +'.tif'
        aqi.rio.to_raster(self.aqi_dir + raster_name)
        return raster_name

    def fillna_in_raster(self, aqi_file: str, na_val: float = 1.0) -> None:
        """Fills nodata values in a raster by interpolating values from surrounding cells. 
        
        Args:
            aqi_file: The name of the raster file to be processed.
            na_val: A value that represents nodata in the raster.
        """
        # open AQI band from AQI raster file
        aqi_filepath = self.aqi_dir + aqi_file
        aqi_raster = rasterio.open(aqi_filepath)
        aqi_band = aqi_raster.read(1)

        # create a nodata mask (map nodata values to 0)
        aqi_nodata_mask = np.where(aqi_band==na_val, 0, aqi_band) 
        # fill nodata in aqi_band using nodata mask
        aqi_band_fillna = fill.fillnodata(aqi_band, mask=aqi_nodata_mask)

        # write raster with filled nodata
        aqi_raster_fillna = rasterio.open(
            aqi_filepath,
            'w',
            driver='GTiff',
            height=aqi_raster.shape[0],
            width=aqi_raster.shape[1],
            count=1,
            dtype='float32',
            transform=aqi_raster.transform,
            crs=aqi_raster.crs
        )

        aqi_raster_fillna.write(aqi_band_fillna, 1)
        aqi_raster_fillna.close()
    
    def create_edge_aqi_update_csv(self, G: GraphHandler, aqi_raster_file: str) -> None:
        """Joins AQI values from an AQI raster file to edges (edge_gdf) of a graph by spatial sampling. 
        Column 'aqi' will be added to the G.edge_gdf. Center points of the edges are used in the spatial join. 
        Exports a csv file of ege keys and corresponding AQI values to use for updating AQI values to a graph.

        Args:
            G: A GraphHandler object that has edge_gdf and graph as properties.
            aqi_raster_file: The filename of an AQI raster (GeoTiff) file. 

        Todo:
            Implement more precise join for longer edges. 
        """
        aqi_filepath = self.aqi_dir + aqi_raster_file
        aqi_raster = rasterio.open(aqi_filepath)
        # get coordinates of edge centers as list of tuples
        coords = [(x,y) for x, y in zip([point.x for point in G.edge_gdf['center_wgs']], [point.y for point in G.edge_gdf['center_wgs']])]
        coords = geom_utils.round_coordinates(coords)
        # extract aqi values at coordinates from raster using sample method from rasterio
        G.edge_gdf['aqi'] = [round(x.item(),2) for x in aqi_raster.sample(coords)]
        
        # save edge keys and corresponding aqi values as csv for later use
        edge_aqi_updates_df = pd.DataFrame(G.edge_gdf[['uvkey', 'aqi']].copy())
        aqi_edge_updates_csv = aqi_raster_file[:-4] + '.csv'
        print('saving edge aqi updates to file:', self.aqi_dir + aqi_edge_updates_csv)
        edge_aqi_updates_df.to_csv(self.aqi_dir + aqi_edge_updates_csv, index=False)

        return aqi_edge_updates_csv
