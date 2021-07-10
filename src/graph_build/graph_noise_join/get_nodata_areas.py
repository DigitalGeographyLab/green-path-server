from pyproj import CRS
from shapely.ops import unary_union
from shapely.geometry import Polygon
import geopandas as gpd
from requests import Request
import common.geometry as geom_utils


def get_wfs_feature(
    url: str,
    layer: str,
    version: str = '1.0.0',
    request: str = 'GetFeature'
) -> gpd.GeoDataFrame:
    params = dict(
        service='WFS',
        version=version,
        request=request,
        typeName=layer,
        outputFormat='json'
        )
    q = Request('GET', url, params=params).prepare().url
    return gpd.read_file(q)


def get_nodata_zones(wfs_hsy_url: str, layer: str, hma_mask: str, export_gpkg: str):
    """1) Downloads polygon layer of municipalities of Helsinki Metropolitan Area, 2) Creates buffered polygons from the boundary lines of these polygons,
    3) Exports the boundary-buffers to geopackage. 
    """
    mask_poly: Polygon = geom_utils.project_geom(gpd.read_file(hma_mask)['geometry'][0]).buffer(500)

    municipalities = get_wfs_feature(wfs_hsy_url, layer)
    municipalities.to_file(export_gpkg, layer='hma_municipalities', driver='GPKG')
    boundaries = []
    for municipality in municipalities.itertuples():
        for poly in municipality.geometry.geoms:
            poly = municipality.geometry
            boundaries.append(poly.boundary.buffer(22))

    dissolved_buffer: Polygon = unary_union(boundaries)
    intersected_buffer = dissolved_buffer.intersection(mask_poly)

    boundary_gdf = gpd.GeoDataFrame(data=[{'nodata_zone': 1}], geometry=[intersected_buffer], crs=CRS.from_epsg(3879))
    boundary_gdf.to_file(export_gpkg, layer='municipal_boundaries', driver='GPKG')


if __name__ == '__main__':
    get_nodata_zones(
        wfs_hsy_url = 'https://kartta.hsy.fi/geoserver/wfs',
        layer = 'seutukartta_kunta_2018',
        hma_mask = 'data/HMA.geojson',
        export_gpkg = 'data/extents.gpkg'
    )
