import unittest
import pytest
import rasterio
from utils.aqi_processor import AqiProcessor

AQI = AqiProcessor()
# AQI.set_aws_secrets()

class TestAqiProcessing(unittest.TestCase):

    def test_aqi_nc_to_geotiff_conversion(self):
        nc_file = 'data/tests/allPollutants_2019-09-11T15.nc'
        tiff_out = 'data/tests/allPollutants_2019-09-11T15.tif'
        AQI.aqi_to_raster(nc_file, tiff_out)
        aqi_raster = rasterio.open(tiff_out)
        self.assertEqual(aqi_raster.driver, 'GTiff', msg='wrong driver in the exported raster')
        self.assertEqual(aqi_raster.meta['dtype'], 'float32', msg='wrong data type')
        self.assertEqual(aqi_raster.crs, rasterio.crs.CRS.from_epsg(4326), msg='CRS should be WGS84')

if __name__ == '__main__':
    unittest.main()
