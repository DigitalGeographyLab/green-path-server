import os
from os import listdir
import zipfile
import rioxarray
import xarray
import boto3
import numpy as np
import pandas as pd
import datetime
import rasterio
from rasterio import fill
from datetime import datetime
import utils.geometry as geom_utils
from utils.graph_handler import GraphHandler
from typing import List, Set, Dict, Tuple, Optional

class AqiProcessor:
    """AqiProcessor can download, extract and convert air quality index (AQI) data from FMI's Enfuser model. 
    
    Specifically, it can download the data as a zip archive file, extract a netCDF file containing the air quality 
    index layer and convert it into a GeoTIFF raster. Also, it can delete created temporary and old aqi files.

    Attributes:
        wip_edge_aqi_csv: The name of an edge_aqi_csv file that is currently being produced (wip = work in progress).
        latest_edge_aqi_csv: The name of the latest edge_aqi_csv file that was produced.
        latest_aqi_tif: The name of the latest aqi tif file that was processed.
        aqi_dir: A filepath pointing to a directory where AQI files will be downloaded to and processed.
        s3_bucketname: The name of an AWS s3 bucket from where the enfuser data will be fetched from.
        s3_region: The name of an AWS s3 bucket from where the enfuser data will be fetched from.
        AWS_ACCESS_KEY_ID: The name of a "secret" aws access key id to enfuser s3 bucket.
        AWS_SECRET_ACCESS_KEY: The name of a "secret" aws access key to enfuser s3 bucket.
        temp_files_to_rm (list): A list where names of created temporary files will be collected during processing.

    Notes:
        The required python environment for using the class can be installed with: conda env create -f env_aqi_processing.yml.
        Add file credentials.csv containing the required aws secrets to src/.
    """

    def __init__(self, aqi_dir: str = 'aqi_cache/', set_aws_secrets: bool = False):
        self.wip_edge_aqi_csv: str = ''
        self.latest_edge_aqi_csv: str = ''
        self.latest_aqi_tif: str = ''
        self.aqi_dir = aqi_dir
        self.s3_bucketname: str = 'enfusernow2'
        self.s3_region: str = 'eu-central-1'
        self.AWS_ACCESS_KEY_ID: str = ''
        self.AWS_SECRET_ACCESS_KEY: str = ''
        self.temp_files_to_rm: list = []
        if (set_aws_secrets == True): self.set_aws_secrets()

    def set_aws_secrets(self) -> None:
        creds = pd.read_csv('credentials.csv', sep=',', encoding='utf-8')
        self.AWS_ACCESS_KEY_ID = creds['Access key ID'][0]
        self.AWS_SECRET_ACCESS_KEY = creds['Secret access key'][0]

    def get_current_edge_aqi_csv_name(self) -> str:
        """Returns the name of the current edge aqi updates csv file. Note: it might not exist.
        """
        curdt = datetime.utcnow().strftime('%Y-%m-%dT%H')
        return 'aqi_'+ curdt +'.csv'

    def set_wip_edge_aqi_csv_name(self) -> None:
        """Sets the excpected latest edge_aqi_csv filename to attribute wip_edge_aqi_csv.
        """
        self.wip_edge_aqi_csv = self.get_current_edge_aqi_csv_name()

    def reset_wip_edge_aqi_csv_name(self) -> None:
        self.wip_edge_aqi_csv = ''

    def new_aqi_available(self) -> bool:
        """Returns False if the expected latest aqi file is either already processed or being processed at the moment, 
        else returns True.
        """
        current_edge_aqi_csv = self.get_current_edge_aqi_csv_name()
        if (self.latest_edge_aqi_csv == current_edge_aqi_csv):
            return False
        elif (self.wip_edge_aqi_csv == current_edge_aqi_csv):
            return False
        else:
            return True

    def get_current_enfuser_key_filename(self) -> Tuple[str, str]:
        """Returns a key pointing to the expected current enfuser zip file in aws s3 bucket. 
        Also returns a name for the zip file for exporting the file. The names of the key and the zip file contain
        the current UTC time (e.g. 2019-11-08T11).
        """
        curdt = datetime.utcnow().strftime('%Y-%m-%dT%H')
        enfuser_data_key = 'Finland/pks/allPollutants_' + curdt + '.zip'
        aqi_zip_name = 'allPollutants_' + curdt + '.zip'
        return (enfuser_data_key, aqi_zip_name)

    def fetch_enfuser_data(self, enfuser_data_key: str, aqi_zip_name: str) -> str:
        """Downloads the current enfuser data as a zip file containing multiple netcdf files to the aqi_cache directory. 
        
        Returns:
            The name of the downloaded zip file (e.g. allPollutants_2019-11-08T14.zip).
        """
        # connect to S3
        s3 = boto3.client('s3',
                        region_name=self.s3_region,
                        aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)
                
        # download the netcdf file to a specified location
        file_out = self.aqi_dir + '/' + aqi_zip_name
        s3.download_file(self.s3_bucketname, enfuser_data_key, file_out)
        self.temp_files_to_rm.append(aqi_zip_name)
        return aqi_zip_name

    def extract_zipped_aqi(self, aqi_zip_name: str) -> str:
        """Extracts the contents of a zip file containing enfuser netcdf files. 

        Args:
            aqi_zip_name: The name of the zip file to be extracted from (in aqi_cache directory).
        Returns:
            The name of the extracted aqi nc file.
        """
        # read zip file in
        archive = zipfile.ZipFile(self.aqi_dir + aqi_zip_name, 'r')
        
        # loop over files in zip archive
        for file_name in archive.namelist():
            # extract only files with allPollutants string match
            if ('allPollutants' in file_name):
                # extract selected file to aqi_dir directory
                archive.extract(file_name, self.aqi_dir)
                aqi_nc_name = file_name
        
        self.temp_files_to_rm.append(aqi_nc_name)
        return aqi_nc_name

    def convert_aqi_nc_to_raster(self, aqi_nc_name: str) -> str:
        """Converts a netCDF file to a georeferenced raster file. xarray and rioxarray automatically scale and offset 
        each netCDF file opened with proper values from the file itself. No manual scaling or adding offset required.
        CRS of the exported GeoTiff is set to WGS84.

        Args:
            aqi_nc_name: The filename of an nc file to be processed (in aqi_cache directory).
                e.g. allPollutants_2019-09-11T15.nc
        Returns:
            The name of the exported tif file (e.g. aqi_2019-11-08T14.tif).
        """
        # read .nc file containing the AQI layer as a multidimensional array
        data = xarray.open_dataset(self.aqi_dir + aqi_nc_name)
                
        # retrieve AQI, AQI.data has shape (time, lat, lon)
        # the values are automatically scaled and offset AQI values
        aqi = data['AQI']

        # save AQI to raster (.tif geotiff file recommended)
        aqi = aqi.rio.set_crs('epsg:4326')
        
        # parse date & time from nc filename and export raster
        aqi_date_str = aqi_nc_name[:-3][-13:]
        aqi_tif_name = 'aqi_'+ aqi_date_str +'.tif'
        aqi.rio.to_raster(self.aqi_dir + aqi_tif_name)
        self.latest_aqi_tif = aqi_tif_name
        return aqi_tif_name

    def fillna_in_raster(self, aqi_tif_name: str, na_val: float = 1.0) -> None:
        """Fills nodata values in a raster by interpolating values from surrounding cells. 
        
        Args:
            aqi_tif_name: The name of a raster file to be processed (in aqi_cache directory).
            na_val: A value that represents nodata in the raster.
        """
        # open AQI band from AQI raster file
        aqi_filepath = self.aqi_dir + aqi_tif_name
        aqi_raster = rasterio.open(aqi_filepath)
        aqi_band = aqi_raster.read(1)

        # create a nodata mask (map nodata values to 0)
        # nodata value may be slightly higher than 1.0, hence try different offsets
        na_offset = 0
        for offset in [0.0, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12]:
            na_offset = na_val + offset
            nodata_count = np.sum(aqi_band <= na_offset)
            print('nodata offset:', offset, 'nodata count:', nodata_count)
            # check if nodata values can be mapped with the current offset
            if (nodata_count > 180000):
                break
        if (nodata_count < 180000):
            print('failed to set nodata values in the aqi tif, nodata count:', nodata_count)

        aqi_nodata_mask = np.where(aqi_band <= na_offset, 0, aqi_band)
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
    
    def create_edge_aqi_csv(self, G: GraphHandler, aqi_tif_name: str) -> str:
        """Joins AQI values from an AQI raster file to edges (edge_gdf) of a graph by spatial sampling. 
        Column 'aqi' will be added to the G.edge_gdf. Center points of the edges are used in the spatial join. 
        Exports a csv file of ege keys and corresponding AQI values to use for updating AQI values to a graph.

        Args:
            G: A GraphHandler object that has edge_gdf and graph as properties.
            aqi_tif_name: The filename of an AQI raster (GeoTiff) file (in aqi_cache directory).
        Todo:
            Implement more precise join for longer edges. 
        Returns:
            The name of the exported csv file (e.g. aqi_2019-11-08T14.csv).
        """
        aqi_filepath = self.aqi_dir + aqi_tif_name
        aqi_raster = rasterio.open(aqi_filepath)
        # get coordinates of edge centers as list of tuples
        coords = [(x,y) for x, y in zip([point.x for point in G.edge_gdf['center_wgs']], [point.y for point in G.edge_gdf['center_wgs']])]
        coords = geom_utils.round_coordinates(coords)
        # extract aqi values at coordinates from raster using sample method from rasterio
        G.edge_gdf['aqi'] = [round(x.item(), 2) for x in aqi_raster.sample(coords)]
        
        # save edge keys and corresponding aqi values as csv for later use
        edge_aqi_updates_df = pd.DataFrame(G.edge_gdf[['uvkey', 'aqi', 'length']].copy())
        edge_aqi_updates_df['exp_aqi'] = edge_aqi_updates_df.apply(lambda row: { round(row['length'], 2): row['aqi'] }, axis=1)
        edge_aqi_csv_name = aqi_tif_name[:-4] + '.csv'
        edge_aqi_updates_df[['uvkey', 'aqi', 'exp_aqi']].to_csv(self.aqi_dir + edge_aqi_csv_name, index=False)
        self.latest_edge_aqi_csv = edge_aqi_csv_name
        self.reset_wip_edge_aqi_csv_name()
        return edge_aqi_csv_name

    def remove_temp_files(self) -> None:
        """Removes temporary files created during AQI processing to aqi_cache, i.e. files in attribute self.temp_files_to_rm.
        """
        rm_count = 0
        not_removed = []
        for rm_filename in self.temp_files_to_rm:
            try:
                os.remove(self.aqi_dir + rm_filename)
                rm_count += 1
            except Exception:
                not_removed.append(rm_filename)
                pass
        print('removed', rm_count, 'temp files')
        if (len(not_removed) > 0):
            print('could not remove', len(not_removed), 'files')
        self.temp_files_to_rm = not_removed

    def remove_old_aqi_files(self) -> None:
        """Removes all edge_aqi_csv files older than the latest from from aqi_cache.
        """
        rm_count = 0
        error_count = 0
        for file_n in listdir(self.aqi_dir):
            if (file_n.endswith('.csv') and file_n != self.latest_edge_aqi_csv):
                try:
                    os.remove(self.aqi_dir + file_n)
                    rm_count += 1
                except Exception:
                    error_count += 1
                    pass
            if (file_n.endswith('.tif') and file_n != self.latest_aqi_tif):
                try:
                    os.remove(self.aqi_dir + file_n)
                    rm_count += 1
                except Exception:
                    error_count += 1
                    pass
        print('removed', rm_count, 'old edge aqi csv & tif files')
        if (error_count > 0):
            print('could not remove', error_count, 'old edge aqi csv files')
