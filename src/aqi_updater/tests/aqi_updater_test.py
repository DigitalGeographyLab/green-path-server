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


def test_extract_rt_aqi_from_zip():
    zip_file = 'allPollutants_2021-02-26T14.zip'
    aq_file = aq_processing.extract_zipped_aq_file(test_data_dir, zip_file)
    assert aq_file == 'allPollutants_2021-02-26T14.nc'


def test_convert_aqi_nc_to_tif():
    aq_nc_file = 'allPollutants_2021-02-26T14.nc'
    aq_tif = aq_processing.convert_aq_nc_to_tif(test_data_dir, aq_nc_file)
    assert aq_tif == 'aqi_2021-02-26T14.tif'


def test_fillna_in_aqi_raster():
    aq_tif = 'aqi_2021-02-26T14.tif'
    aqi_filepath = test_data_dir + aq_tif

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


def test_create_aqi_update_csv(aqi_updater):
    assert aqi_updater.latest_aqi_csv == 'aqi_2020-10-10T08.csv'
    aqi_update_df = pd.read_csv(fr'{aqi_updates_dir}aqi_2020-10-10T08.csv')
    assert len(aqi_update_df) == 16469


def test_aqi_update_csv_data_ok():
    aqi_update_df = pd.read_csv(fr'{aqi_updates_dir}aqi_2020-10-10T08.csv')
    assert aqi_update_df[E.id_ig.name].nunique() == 16469
    assert round(aqi_update_df[E.aqi.name].mean(), 3) == 1.684
    assert aqi_update_df[E.aqi.name].median() == 1.67
    assert aqi_update_df[E.aqi.name].min() == 1.63
    assert aqi_update_df[E.aqi.name].max() == 2.04
    assert aqi_update_df[E.id_ig.name].nunique() == 16469
    not_null_aqis = aqi_update_df[aqi_update_df[E.aqi.name].notnull()]
    assert len(not_null_aqis) == 16469


def test_aqi_map_json():
    with open(fr'{aqi_updates_dir}aqi_map.json') as f:
        aqi_map = json.load(f)
        assert len(aqi_map) == 1
        assert len(aqi_map['data']) == 8162
        for id_aqi_pair in aqi_map['data']:
            assert isinstance(id_aqi_pair[0], int) 
            assert isinstance(id_aqi_pair[1], int)
