"""
This file contains a simple demonstration on how to use the Green Paths tool for 
batch routing and how to analyze the routing results.

This script is intended to be run from the root of the project (src/) with the command:
python -m examples.batch_routing_analysis (running as a module allows the imports to work)

Before running the script:
    - Set research_mode to True in src/conf.py
    - Set graph_file to 'graphs/kumpula.graphml' in src/conf.py
    - Start Green Paths routing app to handle routing requests at localhost:5000

"""

from gp_server.app.graph_handler import GraphHandler
from gp_server.app.types import PathEdge
from gp_server.app.logger import Logger
import gp_server.app.noise_exposures as noise_exps
from typing import List, Tuple, Union
import requests
import traceback


# initialize graph handler for fetching edge data after routing
G = GraphHandler(Logger(), 'graphs/kumpula.graphml')


# define example ODs
od_list = [
    ((60.21743, 24.96996), (60.2123, 24.95978)),
    ((60.21743, 24.96996), (60.2118, 24.95952)),
    ((60.20151, 24.96206), (60.2102, 24.96887)),
    ((60.21495, 24.97971), (60.20166, 24.968))
]


def get_od_paths(od_coords: Tuple[Tuple[float, float]]) -> Union[dict, None]:
    """Returns paths from local Green Paths routing API. If routing fails, returns None. 
    """
    od_request_coords = f'{od_coords[0][0]},{od_coords[0][1]}/{od_coords[1][0]},{od_coords[1][1]}'
    try:
        response = requests.get('http://localhost:5000/paths/walk/quiet/' + od_request_coords)
        path_data = response.json()
        return path_data['path_FC'].get('features', None)
    except Exception:
        print.error(traceback.format_exc())
        return None


# get path collections for ODs
od_paths: List[List[dict]] = [get_od_paths(od) for od in od_list]


# for example, we can fetch all edge data for one of the paths like this:
eg_path: dict = od_paths[0][0]
edge_ids: List[int] = eg_path['properties']['edge_ids']
eg_path_edges: List[PathEdge] = [G.get_edge_object_by_id(edge_id) for edge_id in edge_ids]
eg_path_edges = [edge for edge in eg_path_edges if edge]  # filter out null edges

# since we now know that the edges are PathEdge objects, we can access their attributes like this:
eg_edge_gvi_list: List[float] = [edge.gvi for edge in eg_path_edges]
print('\nEdge GVIs: ' + str(eg_edge_gvi_list))

# coordinates can be get in similar manner:
eg_edge_geom_list: List[float] = [list(edge.coords_wgs) for edge in eg_path_edges]
print('\nEdge coordinates: ' + str(eg_edge_geom_list))

# also, we can calculate noise exposure indices of individual edges:
db_costs = noise_exps.get_db_costs()

eg_edge_noise_exposure_index_list: List[float] = [
    noise_exps.get_noise_exposure_index(edge.noises, db_costs)
    for edge in eg_path_edges
]
print('\nEdge noise exposure indices: ' + str(eg_edge_noise_exposure_index_list))
