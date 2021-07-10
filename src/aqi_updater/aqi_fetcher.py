import logging
import os
import boto3
from datetime import datetime
from typing import Tuple
import aqi_updater.aq_processing as aq_processing


def get_current_aqi_tif_name() -> str:
    return fr"aqi_{datetime.utcnow().strftime('%Y-%m-%dT%H')}.tif"


def get_current_enfuser_key_filename() -> Tuple[str, str]:
    """Returns a key pointing to the current (expected) enfuser zip file in AWS S3
    bucket. Also returns a name for the zip file for exporting the file. The names of the key
    and the zip are based on the current UTC time string (e.g. 2019-11-08T11).
    """
    curdt = datetime.utcnow().strftime('%Y-%m-%dT%H')
    enfuser_data_key = fr'Finland/pks/allPollutants_{curdt}.zip'
    aqi_zip_name = fr'allPollutants_{curdt}.zip'
    return (enfuser_data_key, aqi_zip_name)


class AqiFetcher:
    """AqiFetcher handles download, extraction and post processing of air quality index (AQI) data
    from FMI's Enfuser modeling system.

    Notes:
        The required Python environment for using the class can be installed with:
        conda env create -f conda-env.yml.

        Essentially, AQI download workflow is composed of the following steps
        (executed by fetch_process_current_aqi_data()):
            1)	Create a key for fetching Enfuser data based on current UTC time
                (e.g. “allPollutants_2019-11-08T11.zip”).
            2)  Fetch a zip archive that contains Enfuser netCDF data from Amazon S3 bucket using
                the key, aws_access_key_id and aws_secret_access_key.
            3)  Extract Enfuser netCDF data (e.g. allPollutants_2019-09-11T15.nc) from the
                downloaded zip archive.
            4)  Extract AQI layer from the allPollutants*.nc file and export it as GeoTiff (WGS84).
            5)  Open the exported raster and fill nodata values with interpolated values.
                Value 1 is considered nodata in the data. This is an optional step.

    Attributes:
        log: An instance of Logger class for writing log messages.
        wip_aqi_tif: The name of an aqi tif file that is currently being produced
            (wip = work in progress).
        latest_aqi_tif: The name of the latest AQI tif file that was processed.
        __aqi_dir: A filepath pointing to a directory where all AQI files will be downloaded
            to and processed.
        __s3_bucketname: The name of the AWS s3 bucket from where the enfuser data will be
            fetched from.
        __s3_region: The name of the AWS s3 bucket from where the enfuser data will be fetched from.
        __AWS_ACCESS_KEY_ID: A secret AWS access key id to enfuser s3 bucket.
        __AWS_SECRET_ACCESS_KEY: A secret AWS access key to enfuser s3 bucket.
        __temp_files_to_rm (list): A list where names of created temporary files will be collected
            during processing.
        __status: The status of the aqi processor - has latest AQI data been processed or not.

    """

    def __init__(self, aqi_dir: str):
        self.log = logging.getLogger('aqi_fetcher')
        self.wip_aqi_tif: str = ''
        self.latest_aqi_tif: str = ''
        self.__aqi_dir = aqi_dir
        self.__s3_bucketname: str = 'enfusernow2'
        self.__s3_region: str = 'eu-central-1'
        self.__AWS_ACCESS_KEY_ID: str = os.getenv('ENFUSER_S3_ACCESS_KEY_ID', None)
        self.__AWS_SECRET_ACCESS_KEY: str = os.getenv('ENFUSER_S3_SECRET_ACCESS_KEY', None)
        self.__temp_files_to_rm: list = []
        self.__status: str = ''

    def new_aqi_available(self) -> bool:
        """Returns False if the expected latest aqi file is either already processed or being
        processed at the moment, else returns True.
        """
        b_available = True
        status = ''
        current_aqi_tif = get_current_aqi_tif_name()
        if self.latest_aqi_tif == current_aqi_tif:
            status = 'latest AQI data already fetched'
            b_available = False
        else:
            status = f'new AQI data available: {current_aqi_tif}'
            b_available = True

        if self.__status != status:
            self.log.info(f'AQI processor status changed to: {status}')
            self.__status = status

        return b_available

    def fetch_process_current_aqi_data(self) -> None:
        self.wip_aqi_tif = get_current_aqi_tif_name()
        enfuser_data_key, aqi_zip_name = get_current_enfuser_key_filename()
        self.log.info(f'Created key for current AQI: {enfuser_data_key}')
        self.log.info('Fetching enfuser data...')
        aqi_zip_name = self.__fetch_enfuser_data(enfuser_data_key, aqi_zip_name)
        self.log.info(f'Got aqi_zip: {aqi_zip_name}')
        aqi_nc_name = aq_processing.extract_zipped_aq_file(
            self.__aqi_dir, aqi_zip_name, 'allPollutants'
        )
        self.__temp_files_to_rm.append(aqi_nc_name)
        self.log.info(f'Extracted aqi_nc: {aqi_nc_name}')
        aqi_tif_name = aq_processing.convert_aq_nc_to_tif(self.__aqi_dir, aqi_nc_name)
        self.log.info(f'Extracted aqi_tif: {aqi_tif_name}')
        scaled = aq_processing.fix_aqi_tiff_scale_offset(self.__aqi_dir + aqi_tif_name)
        if scaled:
            self.log.info(f'Scaled AQI values to real AQI range')
        na_fill_success = aq_processing.fillna_in_raster(self.__aqi_dir, aqi_tif_name, na_val=1.0)
        if na_fill_success:
            self.latest_aqi_tif = aqi_tif_name

    def finish_aqi_fetch(self) -> None:
        self.__remove_temp_files()
        self.__remove_old_aqi_tif_files()
        self.wip_aqi_tif = ''

    def __fetch_enfuser_data(self, enfuser_data_key: str, aqi_zip_name: str) -> str:
        """Downloads the current enfuser data as a zip file containing multiple netcdf files to the
        aqi_cache directory.

        Returns:
            The name of the downloaded zip file (e.g. allPollutants_2019-11-08T14.zip).
        """
        # connect to S3
        s3 = boto3.client(
            's3',
            region_name=self.__s3_region,
            aws_access_key_id=self.__AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.__AWS_SECRET_ACCESS_KEY
        )

        # download the netcdf file to a specified location
        file_out = fr'{self.__aqi_dir}/{aqi_zip_name}'
        s3.download_file(self.__s3_bucketname, enfuser_data_key, file_out)
        self.__temp_files_to_rm.append(aqi_zip_name)
        return aqi_zip_name

    def __remove_temp_files(self) -> None:
        """Removes temporary files created during AQI processing to aqi_cache, i.e. files in
        attribute self.__temp_files_to_rm.
        """
        rm_count = 0
        not_removed = []
        for rm_filename in self.__temp_files_to_rm:
            try:
                os.remove(self.__aqi_dir + rm_filename)
                rm_count += 1
            except Exception:
                not_removed.append(rm_filename)
                pass
        self.log.info(f'Removed {rm_count} temp files')
        if len(not_removed) > 0:
            self.log.warning(f'Could not remove {len(not_removed)} files')
        self.__temp_files_to_rm = not_removed

    def __remove_old_aqi_tif_files(self) -> None:
        """Removes old aqi tif files from aqi_cache.
        """
        rm_count = 0
        error_count = 0
        for file_n in os.listdir(self.__aqi_dir):
            if file_n.endswith('.tif') and file_n != self.latest_aqi_tif:
                try:
                    os.remove(self.__aqi_dir + file_n)
                    rm_count += 1
                except Exception:
                    error_count += 1
                    pass
        self.log.info(f'Removed {rm_count} old edge aqi tif files')
        if error_count > 0:
            self.log.warning(f'Could not remove {error_count} old aqi tif files')
