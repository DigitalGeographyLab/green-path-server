"""
This file provides an easy access to settings of the Green Paths route planner app.

The default values can be overridden as necessary, e.g. set research_mode to True if additional
path properties (such as list of edge IDs) are needed. It is recommended to disable unused
features (walking_enabled, quiet_paths_enabled etc.) to allow smaller memory usage and faster
routing.

Configurations:
    graph_file (str): file path to graph file (e.g. graphs/hma.graphml)

    test_mode (bool): set to True to use sample AQI layer during tests runs

    research_mode (bool): set to True for additional path properties

    walk_speed_ms (float): walking speed in m/s 
    bike_speed_ms (float): cycling speed in m/s

    max_od_search_dist_m (float): maximum distance in meters to search for nearest origin or
        destination, higher values make O/D search slower

    walking_enabled (bool): enables/disables walk cost calculation
    cycling_enabled (bool): enables/disables bike cost calculation
    quiet_paths_enabled (bool): enables/disables noise cost calculation
    clean_paths_enabled (bool): enables/disables air quality cost calculation
    gvi_paths_enabled (bool): enables/disables green view cost calculation

    use_mean_aqi (bool): set to True to use mean AQI data instead of real-time data
    mean_aqi_file_name (str): name of CSV file containing mean AQI values (edge_id & aqi) 
        in the path aqi_updates/
    edge_data (bool): return exposure properties and coordinates of paths' edges

    noise_sensitivities (list): list of sensitivities* to use in quiet path routing
    aq_sensitivities (list): list of sensitivities* to use in fresh air path routing
    gvi_sensitivities (list): list of sensitivities* to use in green path routing
        * Sensitivities are used to assign higher (or lower) weights to environmentally adjusted costs
          in environmentally sensitive routing. Lower sensitivities result faster paths whereas higher
          sensitivities result longer paths but with better exposures. The maximum number of paths for
          one origin-destination pair is bounded by the number of sensitivities. 
"""

import os
from typing import List, Union
from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingConf:
    graph_file: str
    test_mode: bool
    research_mode: bool
    walk_speed_ms: float
    bike_speed_ms: float
    max_od_search_dist_m: float
    walking_enabled: bool
    cycling_enabled: bool
    quiet_paths_enabled: bool
    clean_paths_enabled: bool
    gvi_paths_enabled: bool
    use_mean_aqi: bool
    mean_aqi_file_name: Union[str, None]
    edge_data: bool
    noise_sensitivities: Union[List[float], None]
    aq_sensitivities: Union[List[float], None]
    gvi_sensitivities: Union[List[float], None]


conf = RoutingConf(
    graph_file = os.getenv('GP_GRAPH', r'graphs/kumpula.graphml'),
    test_mode = False,
    research_mode = False,
    walk_speed_ms = 1.2,
    bike_speed_ms = 5.55,
    max_od_search_dist_m = 650,
    walking_enabled = True,
    cycling_enabled = True,
    quiet_paths_enabled = True,
    clean_paths_enabled = True,
    gvi_paths_enabled = True,
    use_mean_aqi = False,
    mean_aqi_file_name = None,
    edge_data = False,
    noise_sensitivities = [0.1, 0.4, 1.3, 3.5, 6],
    aq_sensitivities = [5, 15, 30],
    gvi_sensitivities = [2, 4, 8]
)
