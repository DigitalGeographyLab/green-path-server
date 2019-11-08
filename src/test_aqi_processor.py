import unittest
import pytest
import rasterio
import numpy as np
import pandas as pd
from utils.aqi_processor import AqiProcessor
from utils.graph_handler import GraphHandler
import utils.graphs as graph_utils

AQI = AqiProcessor(aqi_dir='data/tests/aqi_cache/')
G = GraphHandler(subset=True, aqi_dir='data/tests/aqi_cache/')

class TestAqiProcessing(unittest.TestCase):

    def test_aqi_nc_to_geotiff_conversion(self):
        nc_file = 'allPollutants_2019-09-11T15.nc'
        tiff_file = AQI.convert_aqi_nc_to_raster(nc_file)
        # validate metadata of aqi raster
        aqi_raster = rasterio.open(AQI.aqi_dir + tiff_file)
        self.assertEqual(aqi_raster.driver, 'GTiff', msg='wrong driver in the exported raster')
        self.assertEqual(aqi_raster.meta['dtype'], 'float32', msg='wrong data type')
        self.assertEqual(aqi_raster.crs, rasterio.crs.CRS.from_epsg(4326), msg='CRS should be WGS84')
        # validate aqi stats
        aqi_band = aqi_raster.read(1)
        self.assertAlmostEqual(np.mean(aqi_band), 1.58, 2)
        self.assertEqual(np.sum(aqi_band == 1.0), 282986)
        self.assertEqual(np.sum(aqi_band == 0.0), 0)

    def test_aqi_raster_fillna(self):
        aqi_file = 'aqi_2019-09-11T15.tif'
        AQI.fillna_in_raster(aqi_file, na_val=1.0)
        aqi_raster = rasterio.open(AQI.aqi_dir + aqi_file)
        aqi_band = aqi_raster.read(1)
        # validate metadata of aqi raster
        self.assertEqual(aqi_raster.driver, 'GTiff', msg='wrong driver in the exported raster')
        self.assertEqual(aqi_raster.meta['dtype'], 'float32', msg='wrong data type')
        self.assertEqual(aqi_raster.crs, rasterio.crs.CRS.from_epsg(4326), msg='CRS should be WGS84')
        # validate aqi stats after fillna
        self.assertAlmostEqual(np.mean(aqi_band), 1.61, 2)
        # check that there is no nodata values (1.0 or 0.0) anymore in the raster
        self.assertEqual(np.sum(aqi_band == 1.0), 0)
        self.assertEqual(np.sum(aqi_band == 0.0), 0)

    def test_aqi_edge_gdf_sjoin_to_csv(self):
        aqi_test_tif = 'const_aqi_2019-09-11T15_fillnodata.tif'
        aqi_edge_updates_csv = AQI.create_edge_aqi_update_csv(G, aqi_test_tif)
        # get & validate joined aqi values
        aqi_max = G.edge_gdf['aqi'].max()
        aqi_mean = G.edge_gdf['aqi'].mean()
        print('aqi mean:', aqi_mean)
        self.assertAlmostEqual(aqi_max, 2.38, places=2)
        self.assertAlmostEqual(aqi_mean, 1.708, places=3)
        edge_updates = pd.read_csv(AQI.aqi_dir + aqi_edge_updates_csv)
        self.assertAlmostEqual(edge_updates['aqi'].max(), 2.38, places=2)
        self.assertAlmostEqual(edge_updates['aqi'].mean(), 1.708, places=3)

    def test_aqi_graph_join(self):
        aqi_edge_updates_csv = 'const_aqi_2019-09-11T15.csv'
        G.set_aqi_to_edges(aqi_edge_updates_csv)
        # test that all edges in the graph got aqi value
        edge_dicts = graph_utils.get_all_edge_dicts(G.graph)
        all_edges_have_aqi = True
        for edge in edge_dicts:
            if ('aqi' not in edge):
                all_edges_have_aqi = False
        self.assertEqual(all_edges_have_aqi, True, msg='One or more edges did not get aqi')
        eg_edge = edge_dicts[0]
        eg_aqi = eg_edge['aqi']
        self.assertAlmostEqual(eg_aqi, 1.75, places=2)

if __name__ == '__main__':
    unittest.main()
