import zipfile
import rioxarray
import xarray
import boto3
import pandas as pd
import datetime
import rasterio
from datetime import datetime
import utils.geometry as geom_utils
from utils.graph_handler import GraphHandler

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
        """Downloads the current zip file containing multiple netcdf files to a directory. 
        Note:
            Filename for the exported zip file is defined by the function - only a folder name is needed as the outpath.
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
        """Converts a netCDF file to a georeferenced raster file. xarray and rioxarray automatically scale  and offset 
        each netCDF file opened with proper values from the file itself. No manual scaling or adding offset required.
        CRS of the exported GeoTiff is set to WGS84.
        """        
        # Read .nc file containing the AQI layer as a multidimensional array
        data = xarray.open_dataset(inputfile)
                
        # Retrieve AQI, AQI.data has shape (time, lat, lon)
        # the values are automatically scaled and offset AQI values
        AQI = data['AQI']

        # save AQI to raster (.tif geotiff file recommended)
        AQI = AQI.rio.set_crs('epsg:4326')
        AQI.rio.to_raster(outputfile)
    def fillna_in_raster(self, filename: str, na_val: float = 1.0) -> None:
        """Fills nodata values in a raster by interpolating values from surrounding cells. 
        
        Args:
            filename: The path to a raster file to be processed.
            na_val: A value that represents nodata in the raster.
        """
        # open AQI band from AQI raster file
        aqi_raster = rasterio.open(filename)
        aqi_band = aqi_raster.read(1)

        # create a nodata mask (map nodata values to 0)
        aqi_nodata_mask = np.where(aqi_band==na_val, 0, aqi_band) 
        # fill nodata in aqi_band using nodata mask
        aqi_band_fillna = fill.fillnodata(aqi_band, mask=aqi_nodata_mask)

        # write raster with filled nodata
        aqi_raster_fillna = rasterio.open(
            filename,
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
    
    def aqi_sjoin_aqi_to_edges(self, G: GraphHandler, aqi_file: str) -> None:
        """Joins aqi values from an AQI raster file to edges on a graph by spatial sampling. 
        Center points of the edges are used in the spatial join.

        Args:
            G: A GraphHandler object that has edge_gdf and graph as properties.
            aqi_file: The filename of an AQI raster (GeoTiff) file. 

        Todo:
            Implement more precise join for longer edges. 
        """
        aqi_raster = rasterio.open(aqi_file)
        # get coordinates of edge centers as list of tuples
        coords = [(x,y) for x, y in zip([point.x for point in G.edge_gdf['center_wgs']], [point.y for point in G.edge_gdf['center_wgs']])]
        coords = geom_utils.round_coordinates(coords)
        # extract aqi values at coordinates from raster using sample method from rasterio
        G.edge_gdf['aqi'] = [x.item() for x in aqi_raster.sample(coords)]
        G.update_edge_attr_to_graph(df_attr='aqi', edge_attr='aqi')
