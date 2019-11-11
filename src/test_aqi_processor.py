from os import listdir
import unittest
import pytest
import rasterio
import numpy as np
import pandas as pd
from utils.aqi_processor import AqiProcessor
from utils.graph_handler import GraphHandler
from utils.graph_aqi_updater import GraphAqiUpdater
import utils.graphs as graph_utils

AQI = AqiProcessor(aqi_dir='data/tests/aqi_cache/', set_aws_secrets=False)
G = GraphHandler(subset=True, add_wgs_center=True)

class TestAqiProcessing(unittest.TestCase):

    # def test_aqi_fetch_from_aws(self):
    #     AQI.set_aws_secrets()
    #     enfuser_data_key, aqi_zip_name = AQI.get_current_enfuser_key_filename()
    #     aqi_zip_name = AQI.fetch_enfuser_data(enfuser_data_key, aqi_zip_name)
    #     filelist = listdir(AQI.aqi_dir)
    #     self.assertIn(aqi_zip_name, filelist, msg='zip file not present in directory aqi_dir')

    def test_edge_aqi_file_checks(self):
        current_edge_aqi_csv_name = AQI.get_current_edge_aqi_csv_name()
        AQI.set_wip_edge_aqi_csv_name()
        self.assertEqual(len(AQI.wip_edge_aqi_csv), 21)
        self.assertEqual(AQI.new_aqi_available(), False)
        AQI.latest_edge_aqi_csv = current_edge_aqi_csv_name
        AQI.reset_wip_edge_aqi_csv_name()
        self.assertEqual(AQI.new_aqi_available(), False)
        AQI.latest_edge_aqi_csv = ''
        self.assertEqual(AQI.new_aqi_available(), True)

    def test_extract_aqi_from_enfuser(self):
        AQI.extract_zipped_aqi('allPollutants_2019-11-08T14.zip')
        filelist = listdir(AQI.aqi_dir)
        self.assertIn('allPollutants_2019-11-08T14.nc', filelist)

    def test_aqi_nc_to_geotiff_conversion(self):
        nc_file = 'allPollutants_2019-11-08T14.nc'
        tiff_file = AQI.convert_aqi_nc_to_raster(nc_file)
        # validate metadata of aqi raster
        aqi_raster = rasterio.open(AQI.aqi_dir + tiff_file)
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
        AQI.fillna_in_raster(aqi_file, na_val=1.0)
        aqi_raster = rasterio.open(AQI.aqi_dir + aqi_file)
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
        aqi_edge_updates_csv = AQI.create_edge_aqi_csv(G, aqi_test_tif)
        # get & validate joined aqi values
        aqi_max = G.edge_gdf['aqi'].max()
        aqi_mean = G.edge_gdf['aqi'].mean()
        print('aqi mean:', aqi_mean)
        self.assertAlmostEqual(aqi_max, 2.51, places=2)
        self.assertAlmostEqual(aqi_mean, 1.88, places=2)
        edge_updates = pd.read_csv(AQI.aqi_dir + aqi_edge_updates_csv)
        self.assertAlmostEqual(edge_updates['aqi'].max(), 2.51, places=2)
        self.assertAlmostEqual(edge_updates['aqi'].mean(), 1.88, places=2)

    def test_aqi_graph_join(self):
        aqi_edge_updates_csv = 'aqi_2019-11-08T14.csv'
        G.update_aqi_to_graph(AQI.aqi_dir + aqi_edge_updates_csv)
        # test that all edges in the graph got aqi value
        edge_dicts = graph_utils.get_all_edge_dicts(G.graph)
        all_edges_have_aqi = True
        for edge in edge_dicts:
            if ('aqi' not in edge):
                all_edges_have_aqi = False
        self.assertEqual(all_edges_have_aqi, True, msg='One or more edges did not get aqi')
        eg_edge = edge_dicts[0]
        eg_aqi = eg_edge['aqi']
        self.assertAlmostEqual(eg_aqi, 1.87, places=2)

    def test_aqi_updater(self):
        aqi_updater = GraphAqiUpdater(G, aqi_dir='data/tests/aqi_cache/', start=False)
        expected_aqi_csv = aqi_updater.get_expected_aqi_data_name()
        # test expected aqi data file name
        self.assertEqual(len(expected_aqi_csv), 21)
        self.assertEqual(expected_aqi_csv, AQI.get_current_edge_aqi_csv_name())

if __name__ == '__main__':
    unittest.main()
