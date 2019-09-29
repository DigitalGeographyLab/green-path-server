"""
This module provides various functions for manipulating objects and data frames with geometry.
Supported features include e.g. reprojection, finding nearest point on a line and transforming geometries.

"""

from typing import List, Set, Dict, Tuple
import pandas as pd
import geopandas as gpd
import pyproj
import shapely
from shapely.geometry import mapping, Point, LineString, MultiPolygon, MultiLineString, MultiPoint
from shapely.ops import split, snap, transform
from functools import partial
from fiona.crs import from_epsg

def get_lat_lon_from_coords(coords: List[int]) -> Dict[str, float]:
    return { 'lat': coords[1], 'lon': coords[0] }

def get_lat_lon_from_geom(geom: Point) -> Dict[str, float]:
    return { 'lat': round(geom.y, 6), 'lon': round(geom.x,6) }

def get_xy_from_lat_lon(latLon: Dict[str, float]) -> Dict[str, float]:
    point = get_point_from_lat_lon(latLon)
    point_proj = project_geom(point, from_epsg=4326, to_epsg=3879)
    return get_xy_from_geom(point_proj)

def get_xy_from_geom(geom: Point) -> Dict[str, float]:
    return { 'x': geom.x, 'y': geom.y }

def get_coords_from_lat_lon(latLon: Dict[str, float]) -> List[float]:
    return [latLon['lon'], latLon['lat']]

def get_coords_from_xy(xy: Dict[str, float]) -> List[float]:
    return (xy['x'], xy['y'])

def get_point_from_lat_lon(latLon: Dict[str, float]) -> Point:
    return Point(get_coords_from_lat_lon(latLon))

def get_point_from_xy(xy: Dict[str, float]) -> Point:
    return Point(get_coords_from_xy(xy))

def project_geom(geom, from_epsg: int = 4326, to_epsg: int = 3879):
    """Projects Shapely geometry object (e.g. Point or LineString) to another CRS. 
    The default conversion is from EPSG 4326 to 3879.
    Returns:
        The projected geometry.
    """
    from_epsg_str = 'epsg:'+ str(from_epsg)
    to_epsg_str = 'epsg:'+ str(to_epsg)
    project = partial(
        pyproj.transform,
        pyproj.Proj(init=from_epsg_str),
        pyproj.Proj(init=to_epsg_str))
    geom_proj = transform(project, geom)
    return geom_proj

def get_closest_point_on_line(line: LineString, point: Point) -> Point:
    """Finds the closest point on a line to given point and returns it as Point.
    """
    projected = line.project(point)
    closest_point = line.interpolate(projected)
    return closest_point

def split_line_at_point(line: LineString, point: Point) -> List[LineString]:
    """Splits a line at nearest intersecting point.
    Returns:
        A list containing two LineString objects.
    """
    snap_line = snap(line,point,0.01)
    result = split(snap_line, point)
    if (len(result) < 2): print('Error in splitting line at point: only one line in the result') 
    return result

def get_polygons_under_line(line_geom: LineString, polygons: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Returns polygons that intersect the [line_geom] as GeoDataFrame.
    """
    polygons_sindex = polygons.sindex
    close_polygons_idxs = list(polygons_sindex.intersection(line_geom.buffer(200).bounds))
    close_polygons = polygons.iloc[close_polygons_idxs].copy()
    intersects_mask = close_polygons.intersects(line_geom)
    polygons_under_line = close_polygons.loc[intersects_mask]
    return polygons_under_line

def get_multipolygon_under_line(line_geom: LineString, polygons: gpd.GeoDataFrame) -> MultiPolygon:
    """Returns polygons that intersect the [line_geom] as MultiPolygon.
    """
    polys = get_polygons_under_line(line_geom, polygons)
    geoms = list(polys['geometry'])
    if (len(geoms) == 0):
        return None
    return MultiPolygon(geoms)

def get_split_lines_list(line_geom: LineString, polygons: gpd.GeoDataFrame) -> List[LineString]:
    """Splits a line geometry at boundaries of polygons.
    Returns:
        A list of split lines as LineString objects.
    """
    multi_polygon = get_multipolygon_under_line(line_geom, polygons)
    if (multi_polygon == None):
        return [line_geom]
    split_line_geom = split(line_geom, multi_polygon)
    return list(split_line_geom)

def get_split_lines_gdf(line_geom: LineString, polygons: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Splits a line geometry at boundaries of polygons.
    Returns:
        A GeoDataFrame containing the split lines with LineString geometry.
    """
    multi_polygon = get_multipolygon_under_line(line_geom, polygons)
    if (multi_polygon == None):
        # print('no line-polygon-intersection')
        return gpd.GeoDataFrame()
    split_line_geom = split(line_geom, multi_polygon)
    line_geoms = list(split_line_geom.geoms)
    lengths = [round(line_geom.length, 3) for line_geom in line_geoms]
    all_split_lines_gdf = gpd.GeoDataFrame(data={'length': lengths}, geometry=line_geoms, crs=from_epsg(3879))
    return all_split_lines_gdf

def explode_multipolygons_to_polygons(polygons_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Explodes new rows to GeoDataFrame from found MultiPolygon geometries.
    """
    all_polygons = []
    db_lows = []
    db_highs = []
    for row in polygons_gdf.itertuples():
        geom = getattr(row, 'geometry') 
        db_low = getattr(row, 'db_lo') 
        db_high = getattr(row, 'db_hi') 
        if (geom.geom_type == 'MultiPolygon'):
            polygons = list(geom.geoms)
            all_polygons += polygons
            db_lows += [db_low] * len(polygons)
            db_highs += [db_high] * len(polygons)
        else:
            all_polygons.append(geom)
            db_lows.append(db_low)
            db_highs.append(db_high)
    data = {'db_lo': db_lows, 'db_hi': db_highs}
    all_polygons_gdf = gpd.GeoDataFrame(data=data, geometry=all_polygons, crs=from_epsg(3879))
    return all_polygons_gdf

def explode_lines_to_split_lines(line_df: pd.DataFrame, uniq_id: str = 'uvkey') -> gpd.GeoDataFrame:
    """Explodes more rows to DataFrame from list values in column split_lines.
    """
    row_accumulator = []
    def split_list_to_rows(row):
        for line_geom in row['split_lines']:
            new_row = row.to_dict()
            new_row['geometry'] = line_geom
            row_accumulator.append(new_row)
    
    line_df.apply(split_list_to_rows, axis=1)
    new_gdf = gpd.GeoDataFrame(row_accumulator, crs=from_epsg(3879))
    new_gdf['length'] = [round(geom.length,3) for geom in new_gdf['geometry']]
    new_gdf['mid_point'] = [get_line_middle_point(geom) for geom in new_gdf['geometry']]
    return new_gdf[[uniq_id, 'geometry', 'length', 'mid_point']]

def get_line_middle_point(line_geom: LineString) -> Point:
    """Returns the middle point of a line geometry as Point.
    """
    return line_geom.interpolate(0.5, normalized = True)

def get_geojson_from_geom(geom, from_epsg: int = 3879) -> dict:
    """Returns a dictionary with GeoJSON schema and geometry based on the given geometry. The returned dictionary can be used as a
    feature inside a GeoJSON feature collection. The given geometry is projected to EPSG:4326. 
    """
    geom_wgs = project_geom(geom, from_epsg=from_epsg, to_epsg=4326)
    feature = { 
        'type': 'Feature', 
        'properties': {}, 
        'geometry': mapping(geom_wgs)
        }
    return feature

def lines_overlap(geom1: LineString, geom2: LineString, tolerance: int = 2, min_intersect: float = None) -> bool:
    """Tests if two lines overlap.

    Note: 
        A partial overlap can be accepted - line lengths don't need to match.
    Args:
        geom1: (LineString).
        geom2: (LineString).
        tolerance (int): A tolerance in meters - the geometries will be buffered with the tolerance.
        min_intersect: A minimum instersecton between the buffered geometries (1=full, 0.5=half).
    Returns:
        A boolean value indicating whether the two geometries overlap with respect to the specified requirements.
    """
    buffer1 = geom1.buffer(tolerance)
    buffer2 = geom2.buffer(tolerance)
    match = False
    if ((geom1.within(buffer2) == True) or (geom2.within(buffer1) == True)):
        match = True
    if (min_intersect is not None):
        inters_area = buffer1.intersection(buffer2).area
        inters_ratio = inters_area/buffer2.area
        if (inters_ratio < min_intersect):
            match = False
    return match
