from os import listdir
import ast
import unittest
import pytest
import rasterio
import numpy as np
import pandas as pd
from app.aqi_processor import AqiProcessor
from app.graph_handler import GraphHandler
from app.graph_aqi_updater import GraphAqiUpdater
from app.logger import Logger

logger = Logger(b_printing=True, log_file='test_aqi_processor.log')
aqi_processor = AqiProcessor(logger, aqi_dir='data/tests/aqi_cache/', set_aws_secrets=False)
G = GraphHandler(logger, subset=True, add_wgs_center=True, gdf_attrs=['length'])

class TestAqiProcessing(unittest.TestCase):

    # def test_aqi_fetch_from_aws(self):
    #     aqi_processor.set_aws_secrets()
    #     enfuser_data_key, aqi_zip_name = aqi_processor.get_current_enfuser_key_filename()
    #     aqi_zip_name = aqi_processor.fetch_enfuser_data(enfuser_data_key, aqi_zip_name)
    #     filelist = listdir(aqi_processor.aqi_dir)
    #     self.assertIn(aqi_zip_name, filelist, msg='zip file not present in directory aqi_dir')

    def test_edge_aqi_file_checks(self):
        current_edge_aqi_csv_name = aqi_processor.get_current_edge_aqi_csv_name()
        aqi_processor.set_wip_edge_aqi_csv_name()
        self.assertEqual(len(aqi_processor.wip_edge_aqi_csv), 21)
        self.assertEqual(aqi_processor.new_aqi_available(), False)
        aqi_processor.latest_edge_aqi_csv = current_edge_aqi_csv_name
        aqi_processor.reset_wip_edge_aqi_csv_name()
        self.assertEqual(aqi_processor.new_aqi_available(), False)
        aqi_processor.latest_edge_aqi_csv = ''
        self.assertEqual(aqi_processor.new_aqi_available(), True)

    def test_extract_aqi_from_enfuser(self):
        aqi_processor.extract_zipped_aqi('allPollutants_2019-11-08T14.zip')
        filelist = listdir(aqi_processor.aqi_dir)
        self.assertIn('allPollutants_2019-11-08T14.nc', filelist)

    def test_aqi_nc_to_geotiff_conversion(self):
        nc_file = 'allPollutants_2019-11-08T14.nc'
        tiff_file = aqi_processor.convert_aqi_nc_to_raster(nc_file)
        # validate metadata of aqi raster
        aqi_raster = rasterio.open(aqi_processor.aqi_dir + tiff_file)
        self.assertEqual(aqi_raster.driver, 'GTiff', msg='wrong driver in the exported raster')
        self.assertEqual(aqi_raster.meta['dtype'], 'float32', msg='wrong data type')
        self.assertEqual(aqi_raster.crs, rasterio.crs.CRS.from_epsg(4326), msg='CRS should be WGS84')
        # validate aqi stats
        aqi_band = aqi_raster.read(1)
        self.assertAlmostEqual(np.mean(aqi_band), 1.89, 2)
        self.assertEqual(np.sum(aqi_band == 1.0), 282986)
        self.assertEqual(np.sum(aqi_band == 0.0), 0)

    def test_aqi_raster_fillna(self):
        aqi_file = 'aqi_2019-11-08T14.tif'
        aqi_processor.fillna_in_raster(aqi_file, na_val=1.0)
        aqi_raster = rasterio.open(aqi_processor.aqi_dir + aqi_file)
        aqi_band = aqi_raster.read(1)
        # validate metadata of aqi raster
        self.assertEqual(aqi_raster.driver, 'GTiff', msg='wrong driver in the exported raster')
        self.assertEqual(aqi_raster.meta['dtype'], 'float32', msg='wrong data type')
        self.assertEqual(aqi_raster.crs, rasterio.crs.CRS.from_epsg(4326), msg='CRS should be WGS84')
        # validate aqi stats after fillna
        self.assertAlmostEqual(np.mean(aqi_band), 1.94, 2)
        # check that there is no nodata values (1.0 or 0.0) anymore in the raster
        self.assertEqual(np.sum(aqi_band == 1.0), 0)
        self.assertEqual(np.sum(aqi_band == 0.0), 0)

    def test_aqi_edge_gdf_sjoin_to_csv(self):
        aqi_test_tif = 'aqi_2019-11-08T14.tif'
        aqi_updates_csv = aqi_processor.create_edge_aqi_csv(G, aqi_test_tif)
        # get & validate joined aqi values
        aqi_min = G.edge_gdf['aqi'].min()
        aqi_max = G.edge_gdf['aqi'].max()
        aqi_mean = G.edge_gdf['aqi'].mean()
        logger.info('aqi mean: '+ str(round(aqi_mean, 3)))
        self.assertGreater(aqi_min, 0.9)
        self.assertAlmostEqual(aqi_max, 2.51, places=2)
        self.assertAlmostEqual(aqi_mean, 1.88, places=2)
        field_type_converters = { 'uvkey': ast.literal_eval, 'aqi_exp': ast.literal_eval }
        edge_aqi_updates = pd.read_csv(aqi_processor.aqi_dir + aqi_updates_csv, converters=field_type_converters, index_col='index')
        edge_aqi_updates['aqi'] = [aqi_exp[0] for aqi_exp in edge_aqi_updates['aqi_exp']]
        self.assertAlmostEqual(edge_aqi_updates['aqi'].max(), 2.51, places=2)
        self.assertAlmostEqual(edge_aqi_updates['aqi'].mean(), 1.88, places=2)

if __name__ == '__main__':
    unittest.main()
