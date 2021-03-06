"""
This file provides an easy access to settings of the Green Paths route planner app. 

The default values can be overridden as necessary, e.g. set research_mode to True if additional
path properties (such as list of edge IDs) are needed. It is recommended to disable unused
features (walking_enabled, quiet_paths_enabled etc.) to allow smaller memory usage and faster routing. 

Configurations:
    graph_subset (bool): use clipped graph or not (used in server)
    graph_file (str): name of the graph file to use (overrides graph_subset)

    test_mode (bool): only used by pytest (use static AQI layer as real-time AQI data)

    research_mode (bool): set to True for additional path properties
    walking_enabled (bool): enables/disables walk cost calculation
    cycling_enabled (bool): enables/disables bike cost calculation
    quiet_paths_enabled (bool): enables/disables noise cost calculation
    clean_paths_enabled (bool): enables/disables air quality cost calculation
    gvi_paths_enabled (bool): enables/disables green view cost calculation

    use_mean_aqi (bool): set to True to use mean AQI data instead of real-time data
    mean_aqi_file (str): file path to mean AQI data as CSV (edge_id & aqi)

    noise_sensitivities (list): if set, overrides the default sensitivities
    aq_sensitivities (list): if set, overrides the default sensitivities
    gvi_sensitivities (list): if set, overrides the default sensitivities
"""

import os
from typing import List


graph_subset: bool = os.getenv('GRAPH_SUBSET', 'False') == 'True'
graph_id = 'kumpula' if graph_subset else 'hma'
graph_file: str = fr'graphs/{graph_id}.graphml'

test_mode: bool = False

research_mode: bool = False
walking_enabled: bool = True
cycling_enabled: bool = True
quiet_paths_enabled: bool = True
clean_paths_enabled: bool = True
gvi_paths_enabled: bool = True

use_mean_aqi: bool = False
mean_aqi_file: str = fr'yearly_2019_aqi_avg_sum_{graph_id}.csv'

# the default sensitivities for exposure optimized routing can be overridden with these:
noise_sensitivities: List[float] = []
aq_sensitivities: List[float] = []
gvi_sensitivities: List[float] = []
