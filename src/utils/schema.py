from enum import Enum
from typing import Dict, Tuple
from shapely import wkt
from shapely.geometry import LineString
import ast

version = 1.0

class NoiseSource(Enum):
    road = 'road'
    train = 'train'
    metro = 'metro'
    tram = 'tram'

class Node(Enum):
   id_ig = 'ii'
   id_otp = 'io'
   name_otp = 'no'
   geometry = 'geom'
   geom_wgs = 'geom_wgs'
   traversable_walking = 'b_tw'
   traversable_biking = 'b_tb'
   traffic_light = 'tl'

class Edge(Enum):
   id_ig: int = 'ii'
   id_otp: str = 'io'
   uv: tuple = 'uv' # source & target node ids as a tuple
   name_otp: str = 'no'
   geometry: LineString = 'geom'
   geom_wgs: LineString = 'geom_wgs'
   length: float = 'l'
   length_b: float = 'lb'
   edge_class: str = 'ec'
   street_class: str = 'sc'
   is_stairs: bool = 'b_st'
   is_no_thru_traffic: bool = 'b_ntt'
   allows_walking: bool = 'b_aw'
   allows_biking: bool = 'b_ab'
   traversable_walking: bool = 'b_tw'
   traversable_biking: bool = 'b_tb'
   bike_safety_factor: float = 'bsf'
   noises: Dict[int, float] = 'n' # nodata = None, no noises = {}
   noise_source: NoiseSource = 'ns' # nodata = None, no noises = ''
   noise_sources: Dict[NoiseSource, int] = 'nss' # nodata = None, no noises = {}
   aqi_exp: Tuple[float, float] = 'aqie' # air quality index exposure as tuple(aqi, length)

def to_str(value):
    return str(value) if value != 'None' else None
def to_int(value):
    return int(value)
def to_float(value):
    return float(value)
def to_geom(value):
    return wkt.loads(value)
def to_bool(value):
   return ast.literal_eval(value)
def to_dict(value):
   return ast.literal_eval(value) if value != 'None' else None
def to_tuple(value):
   return ast.literal_eval(value) if value != 'None' else None

edge_attr_converters = {
    Edge.id_ig: to_int,
    Edge.id_otp: to_str,
    Edge.uv: to_tuple,
    Edge.name_otp: to_str,
    Edge.geometry: to_geom,
    Edge.geom_wgs: to_geom,
    Edge.length: to_float,
    Edge.length_b: to_float,
    Edge.edge_class: to_str,
    Edge.street_class: to_str,
    Edge.is_stairs: to_bool,
    Edge.is_no_thru_traffic: to_bool,
    Edge.allows_walking: to_bool,
    Edge.allows_biking: to_bool,
    Edge.traversable_walking: to_bool,
    Edge.traversable_biking: to_bool,
    Edge.bike_safety_factor: to_float,
    Edge.noises: to_dict,
    Edge.noise_source: to_str,
    Edge.noise_sources: to_dict,
    Edge.aqi_exp: to_tuple
}

node_attr_converters = {
    Node.id_ig: to_int,
    Node.id_otp: to_str,
    Node.name_otp: to_str,
    Node.geometry: to_geom,
    Node.geom_wgs: to_geom,
    Node.traversable_walking: to_bool,
    Node.traversable_biking: to_bool,
    Node.traffic_light: to_bool,
}
