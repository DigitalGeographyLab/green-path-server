from logging import Logger
from typing import Union
import zipfile
import rioxarray
import xarray
import rasterio
import numpy as np
from rasterio import fill


def extract_zipped_aq_file(
    dir: str,
    aq_zip_name: str,
    aq_file_name: str = 'allPollutants'
) -> Union[str, None]:
    """Extracts AQ file from zip archive.
    Returns the name of the extracted file (if found) or None.
    """
    zip_archive = zipfile.ZipFile(fr'{dir}{aq_zip_name}', 'r')

    # loop over files in zip archive
    for file_name in zip_archive.namelist():
        if aq_file_name in file_name:
            zip_archive.extract(file_name, dir)
            return file_name


def convert_aq_nc_to_tif(
    dir: str,
    aqi_nc_name: str
) -> str:
    """Converts a netCDF file to a georeferenced raster file. xarray and rioxarray automatically
    scale and offset each netCDF file opened with proper values from the file itself. No manual
    scaling or adding offset required. CRS of the exported GeoTiff is set to WGS84.

    Args:
        aqi_nc_name: The filename of an nc file to be processed (in aqi_cache directory).
            e.g. allPollutants_2019-09-11T15.nc
    Returns:
        The name of the exported tif file (e.g. aqi_2019-11-08T14.tif).
    """
    # read .nc file containing the AQI layer as a multidimensional array
    data = xarray.open_dataset(dir + aqi_nc_name)

    # retrieve AQI, AQI.data has shape (time, lat, lon)
    # the values are automatically scaled and offset AQI values
    aqi = data['AQI']

    # save AQI to raster (.tif geotiff file recommended)
    aqi = aqi.rio.set_crs('epsg:4326')

    # parse date & time from nc filename and export raster
    aqi_date_str = aqi_nc_name[:-3][-13:]
    aqi_tif_name = f'aqi_{aqi_date_str}.tif'
    aqi.rio.to_raster(fr'{dir}{aqi_tif_name}')
    return aqi_tif_name


def fillna_in_raster(
    dir: str,
    aqi_tif_name: str,
    na_val: float = 1.0,
    log: Logger = None
) -> bool:
    """Fills nodata values in a raster by interpolating values from surrounding cells.
    Value 1.0 is considered as nodata. If no nodata is found with that value, a small offset
    will be applied, as sometimes the nodata value is slightly higher than 1.0 (assumably
    due to inaccuracy in netcdf to geotiff conversion).

    Args:
        aqi_tif_name: The name of a raster file to be processed (in aqi_cache directory).
        na_val: A value that represents nodata in the raster.
    """
    # open AQI band from AQI raster file
    aqi_filepath = dir + aqi_tif_name
    aqi_raster = rasterio.open(aqi_filepath)
    aqi_band = aqi_raster.read(1)

    # create a nodata mask (map nodata values to 0)
    # nodata value may be slightly higher than 1.0, hence try different offsets
    na_offset = 0
    for offset in [0.0, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12]:
        na_offset = na_val + offset
        nodata_count = np.sum(aqi_band <= na_offset)
        if log:
            log.info(f'Nodata offset: {offset} / nodata count: {nodata_count}')
        # check if nodata values can be mapped with the current offset
        if (nodata_count > 180000):
            break
    if (nodata_count < 180000):
        if log:
            log.info(f'Failed to set nodata values in the AQI tif, nodata count: {nodata_count}')

    aqi_nodata_mask = np.where(aqi_band <= na_offset, 0, aqi_band)
    # fill nodata in aqi_band using nodata mask
    aqi_band_fillna = fill.fillnodata(aqi_band, mask=aqi_nodata_mask)

    # validate AQI values after na fill
    invalid_count = np.sum(aqi_band_fillna < 1.0)
    if (invalid_count > 0):
        if log:
            log.warning(f'AQI band has {invalid_count} below 1 aqi values after na fill')

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

    return True
