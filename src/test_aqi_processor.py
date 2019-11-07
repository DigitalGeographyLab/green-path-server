import unittest
import pytest
import rasterio
from utils.aqi_processor import AqiProcessor
from utils.graph_handler import GraphHandler
import utils.graphs as graph_utils

class TestAqiProcessing(unittest.TestCase):

    def test_aqi_nc_to_geotiff_conversion(self):
        AQI = AqiProcessor()
        nc_file = 'data/tests/allPollutants_2019-09-11T15.nc'
        tiff_out = 'data/tests/allPollutants_2019-09-11T15.tif'
        AQI.aqi_to_raster(nc_file, tiff_out)
        # read raster and validate it
        aqi_raster = rasterio.open(tiff_out)
        self.assertEqual(aqi_raster.driver, 'GTiff', msg='wrong driver in the exported raster')
        self.assertEqual(aqi_raster.meta['dtype'], 'float32', msg='wrong data type')
        self.assertEqual(aqi_raster.crs, rasterio.crs.CRS.from_epsg(4326), msg='CRS should be WGS84')

    def test_aqi_edge_gdf_sjoin(self):
        AQI = AqiProcessor()
        G = GraphHandler(subset=True)
        aqi_test_tif = 'data/tests/allPollutants_2019-09-11T15_test.tif'
        AQI.aqi_sjoin_aqi_to_edges(G, aqi_test_tif)
        # get & validate joined aqi values
        aqi_max = G.edge_gdf['aqi'].max()
        aqi_mean = G.edge_gdf['aqi'].mean()
        print('aqi mean:', aqi_mean)
        self.assertAlmostEqual(aqi_max, 2.375, places=3)
        self.assertAlmostEqual(aqi_mean, 1.676, places=3)
        edge_dicts = graph_utils.get_all_edge_dicts(G.graph)
        eg_edge = edge_dicts[0]
        eg_aqi = eg_edge['aqi']
        print('eg_aqi', eg_aqi)
        print('eg_aqi', type(eg_aqi))
        self.assertAlmostEqual(eg_aqi, 1.751, places=3)

if __name__ == '__main__':
    unittest.main()
