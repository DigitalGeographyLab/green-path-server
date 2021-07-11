import pytest
from aqi_updater import aq_processing
from aqi_updater.aqi_updater import AqiUpdater
from common.igraph import Edge as E
from aqi_updater.tests.conftest import test_data_dir, aqi_updates_dir
import common.igraph as ig_utils
import rasterio
import numpy as np
import pandas as pd
import json


@pytest.fixture(scope='module')
def graph():
    graph = ig_utils.read_graphml(fr'{test_data_dir}kumpula.graphml')
    yield graph


@pytest.fixture(scope='module', autouse=True)
def aqi_updater(graph):
    aqi_updater = AqiUpdater(graph, test_data_dir, aqi_updates_dir)
    aqi_updater.create_aqi_update_csv('aqi_2020-10-10T08.tif')
    aqi_updater.finish_aqi_update()
    yield aqi_updater


def test_extracts_aqi_nc_from_zip():
    zip_file = 'allPollutants_2021-02-26T14.zip'
    aq_file = aq_processing.extract_zipped_aq_file(test_data_dir, zip_file)
    assert aq_file == 'allPollutants_2021-02-26T14.nc'


def test_converts_aqi_nc_to_tif():
    aq_nc_file = 'allPollutants_2021-02-26T14.nc'
    aq_tif = aq_processing.convert_aq_nc_to_tif(test_data_dir, aq_nc_file)
    assert aq_tif == 'aqi_2021-02-26T14.tif'


def test_converted_aqi_tif_has_valid_unscaled_aqi():
    aq_tif = 'aqi_2021-02-26T14.tif'
    aqi_filepath = test_data_dir + aq_tif
    aqi_raster = rasterio.open(aqi_filepath)
    assert aq_processing._has_unscaled_aqi(aqi_raster)
    aqi_band = aqi_raster.read(1)
    scale = aq_processing._get_scale(aqi_raster)
    offset = aq_processing._get_offset(aqi_raster)
    aqi_band_scaled = aqi_band * scale + offset
    assert round(float(np.min(aqi_band_scaled)), 2) == 1.0
    assert round(float(np.max(aqi_band_scaled)), 2) == 2.89
    assert round(float(np.median(aqi_band_scaled)), 2) == 1.72
    aqi_raster.close()


def test_scales_and_offsets_raster_values_to_aqi():
    aq_tif = 'aqi_2021-02-26T14.tif'
    aqi_filepath = test_data_dir + aq_tif
    aqi_raster = rasterio.open(aqi_filepath)
    assert aq_processing._has_unscaled_aqi(aqi_raster)
    assert aq_processing.fix_aqi_tiff_scale_offset(aqi_filepath)
    aqi_raster = rasterio.open(aqi_filepath)
    assert not aq_processing._has_unscaled_aqi(aqi_raster)
    aqi_band = aqi_raster.read(1)
    assert round(float(np.min(aqi_band)), 2) == 1.0
    assert round(float(np.max(aqi_band)), 2) == 2.89
    aqi_raster.close()


def test_fills_na_values_in_aqi_raster():
    aq_tif = 'aqi_2021-02-26T14.tif'
    aqi_filepath = test_data_dir + aq_tif
    aq_processing.fix_aqi_tiff_scale_offset(aqi_filepath)
    aqi_raster = rasterio.open(aqi_filepath)
    aqi_band = aqi_raster.read(1)
    nodata_count = np.sum(aqi_band <= 1.0)
    aqi_raster.close()
    assert nodata_count == 297150
    assert aq_processing.fillna_in_raster(test_data_dir, aq_tif, na_val=1.0)
    aqi_raster = rasterio.open(aqi_filepath)
    aqi_band = aqi_raster.read(1)
    nodata_count = np.sum(aqi_band <= 1.0)
    aqi_raster.close()
    assert nodata_count == 0


def test_creates_aqi_update_csv(aqi_updater):
    assert aqi_updater.latest_aqi_csv == 'aqi_2020-10-10T08.csv'
    aqi_update_df = pd.read_csv(fr'{aqi_updates_dir}aqi_2020-10-10T08.csv')
    assert len(aqi_update_df) == 16469


def test_aqi_update_csv_aqi_values_are_valid():
    aqi_update_df = pd.read_csv(fr'{aqi_updates_dir}aqi_2020-10-10T08.csv')
    assert aqi_update_df[E.id_ig.name].nunique() == 16469
    assert round(aqi_update_df[E.aqi.name].mean(), 3) == 1.684
    assert aqi_update_df[E.aqi.name].median() == 1.67
    assert aqi_update_df[E.aqi.name].min() == 1.63
    assert aqi_update_df[E.aqi.name].max() == 2.04
    assert aqi_update_df[E.id_ig.name].nunique() == 16469
    not_null_aqis = aqi_update_df[aqi_update_df[E.aqi.name].notnull()]
    assert len(not_null_aqis) == 16469


def test_creates_aqi_map_json():
    with open(fr'{aqi_updates_dir}aqi_map.json') as f:
        aqi_map = json.load(f)
        assert len(aqi_map) == 1
        assert len(aqi_map['data']) == 8162
        for id_aqi_pair in aqi_map['data']:
            assert isinstance(id_aqi_pair[0], int) 
            assert isinstance(id_aqi_pair[1], int)
