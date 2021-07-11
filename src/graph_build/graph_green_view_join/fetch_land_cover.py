from graph_build.graph_green_view_join.conf import GraphGreenViewJoinConf
from typing import Dict
import fiona
import logging
from geopandas import GeoDataFrame
from dataclasses import dataclass
import geopandas as gpd
from enum import Enum
from requests import Request
from functools import partial
from graph_build.graph_green_view_join.db import get_db_writer


hsy_wfs_url = 'https://kartta.hsy.fi/geoserver/wfs'

log = logging.getLogger('fetch_land_cover')


@dataclass
class VegetationLayers:
    low_vegetation: GeoDataFrame
    low_vegetation_parks: GeoDataFrame = None
    trees_2_10m: GeoDataFrame = None
    trees_10_15m: GeoDataFrame = None
    trees_15_20m: GeoDataFrame = None
    trees_20m: GeoDataFrame = None


class HsyWfsLayerName(Enum):
    low_vegetation = 'matala_kasvillisuus'
    low_vegetation_parks = 'maanpeite_muu_avoin_matala_kasvillisuus_2018'
    trees_2_10m = 'maanpeite_puusto_2_10m_2018'
    trees_10_15m = 'maanpeite_puusto_10_15m_2018'
    trees_15_20m = 'maanpeite_puusto_15_20m_2018'
    trees_20m = 'maanpeite_puusto_yli20m_2018'


def __fetch_wfs_layer(
    url: str,
    layer: str,
    version: str = '1.0.0', 
    request: str = 'GetFeature',
) -> GeoDataFrame:
    params = dict(
        service = 'WFS',
        version = version,
        request = request,
        typeName = layer,
        outputFormat = 'json'
        )
    q = Request('GET', url, params=params).prepare().url
    return gpd.read_file(q)


def fetch_hsy_vegetation_layers(land_cover_cache_gpkg: str) -> VegetationLayers:
    fetch_wfs_layer = partial(__fetch_wfs_layer, hsy_wfs_url)
    fetched_layers = fiona.listlayers(land_cover_cache_gpkg)
    log.info(f'Previously fetched layers: {fetched_layers}')

    layers: Dict[HsyWfsLayerName, GeoDataFrame] = {}

    for idx, layer_name in enumerate(HsyWfsLayerName):

        if layer_name.name in fetched_layers:
            log.info(f'Loading layer {idx+1}/{len(HsyWfsLayerName)}: {layer_name.name} from cache')
            gdf = gpd.read_file(land_cover_cache_gpkg, layer=layer_name.name)
            layers[layer_name.name] = gdf
        else:
            log.info(f'Fetching WFS layer {idx+1}/{len(HsyWfsLayerName)}: {layer_name.name} from "{layer_name.value}"')
            gdf = fetch_wfs_layer(layer_name.value)
            gdf.drop(gdf.columns.difference(['geometry']), 1, inplace=True)
            gdf.to_file(land_cover_cache_gpkg, layer=layer_name.name, driver='GPKG')
            layers[layer_name.name] = gdf

    log.info('Loaded all land cover layers')
    return VegetationLayers(**layers)


def explode_geometries(veg_layers: VegetationLayers) -> None:
    log.info('Exploding geometries of low_vegetation')
    veg_layers.low_vegetation = veg_layers.low_vegetation.explode()
    log.info('Exploding geometries of low_vegetation_parks')
    veg_layers.low_vegetation_parks = veg_layers.low_vegetation_parks.explode()
    log.info('Exploding geometries of trees_2_10m')
    veg_layers.trees_2_10m = veg_layers.trees_2_10m.explode()
    log.info('Exploding geometries of trees_10_15m')
    veg_layers.trees_10_15m = veg_layers.trees_10_15m.explode()
    log.info('Exploding geometries of trees_15_20m')
    veg_layers.trees_15_20m = veg_layers.trees_15_20m.explode()
    log.info('Exploding geometries of trees_20m')
    veg_layers.trees_20m = veg_layers.trees_20m.explode()


def main(conf: GraphGreenViewJoinConf):
    vegetation_layers = fetch_hsy_vegetation_layers(conf.lc_wfs_cache_gpkg_fp)
    explode_geometries(vegetation_layers)

    write_to_postgis = get_db_writer(log)
    write_to_postgis(vegetation_layers.low_vegetation, 'low_vegetation')
    write_to_postgis(vegetation_layers.low_vegetation_parks, 'low_vegetation_parks')
    write_to_postgis(vegetation_layers.trees_2_10m, 'trees_2_10m')
    write_to_postgis(vegetation_layers.trees_10_15m, 'trees_10_15m')
    write_to_postgis(vegetation_layers.trees_15_20m, 'trees_15_20m')
    write_to_postgis(vegetation_layers.trees_20m, 'trees_20m')
