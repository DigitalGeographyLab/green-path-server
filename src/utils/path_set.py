from typing import List, Set, Dict, Tuple
from utils.path import Path
import utils.paths_overlay_filter as path_overlay_filter

class PathSet:

    def __init__(self, set_type: str, debug_mode: bool = False):
        self.set_type: str = set_type # either 'quiet' or 'clean'
        self.shortest_path: Path = None
        self.green_paths: List[Path] = []
        self.debug_mode: bool = debug_mode

    def set_shortest_path(self, s_path: Path):
        s_path.set_set_type(self.set_type)
        self.shortest_path = s_path

    def add_green_path(self, q_path: Path):
        q_path.set_set_type(self.set_type)
        self.green_paths.append(q_path)

    def get_all_paths(self): return [self.shortest_path] + self.green_paths

    def get_green_path_count(self): return len(self.green_paths)

    def set_path_edges(self, graph):
        if (self.shortest_path is not None):
            self.shortest_path.set_path_edges(graph)
        if (len(self.green_paths) > 0):
            for gp in self.green_paths:
                gp.set_path_edges(graph)

    def aggregate_path_attrs(self, geom=True, length=True, noises=False):
        if (self.shortest_path is not None):
            self.shortest_path.aggregate_path_attrs(geom=geom, length=length, noises=noises)
        if (len(self.green_paths) > 0):
            for gp in self.green_paths:
                gp.aggregate_path_attrs(geom=geom, length=length, noises=noises)

    def get_paths_as_list(self, geom=True):
        paths_list = [self.shortest_path] + self.green_paths
        path_dicts_list = [path.get_path_as_dict(geom=geom) for path in paths_list]
        return path_dicts_list

    def filter_out_unique_len_paths(self):
        if (self.debug_mode == True): print('green path count:', len(self.green_paths))
        filtered = []
        prev_len = self.shortest_path.length
        for path in self.green_paths:
            if (path.length != prev_len):
                filtered.append(path)
            prev_len = path.length
        self.green_paths = filtered
        if (self.debug_mode == True): print('green path count after filter by unique length:', len(self.green_paths))

    def filter_out_unique_geom_paths(self, buffer_m=50):
        cost_attr = 'nei_norm' if (self.set_type == 'quiet') else ''
        unique_paths_names = path_overlay_filter.get_unique_paths_by_geom_overlay(self.get_all_paths(), buffer_m=buffer_m, cost_attr=cost_attr, debug=self.debug_mode)
        if (unique_paths_names is not None):
            self.filter_paths_by_names(unique_paths_names)

    def filter_paths_by_names(self, filter_names: List[str]):
        if (self.debug_mode == True): print('filter paths by', len(filter_names),'names:', filter_names)
        filtered_green_paths = [path for path in self.green_paths if path.name in filter_names]
        if ('short_p' not in filter_names):
            if (self.debug_mode == True): print('replace shortest path with shortest green path')
            shortest_green_path = filtered_green_paths[0]
            shortest_green_path.set_path_type('short')
            shortest_green_path.set_path_name('short_p')
            self.set_shortest_path(shortest_green_path)
            filtered_green_paths = filtered_green_paths[1:]
        if (self.debug_mode == True): print('replace', len(self.green_paths), 'green paths with', len(filtered_green_paths),'filtered paths')
        self.green_paths = filtered_green_paths

    def set_path_noise_attrs(self, db_costs):
        self.shortest_path.set_noise_attrs(db_costs)
        for path in self.green_paths:
            path.set_noise_attrs(db_costs)

    def set_green_path_diff_attrs(self):
        for path in self.green_paths:
            path.set_green_path_diff_attrs(self.shortest_path)

    def get_as_feature_collection(self):
        return [path.get_as_geojson_feature() for path in [self.shortest_path] + self.green_paths]

    def print_set_info(self):
        print('green path count:', len(self.green_paths))
        if (len(self.green_paths > 0)):
            gp_1 = self.green_paths[0]
            print('gp_1', gp_1.noise_attrs.mdB)
