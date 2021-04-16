from typing import List
from gp_server.app.logger import Logger
from gp_server.app.path_set import PathSet
from gp_server.app.path import Path
from gp_server.app.constants import PathType, RoutingMode, TravelMode


def test_sorts_bike_paths_by_length() -> dict:
    path_set = PathSet(Logger(), RoutingMode.QUIET, TravelMode.BIKE)
    paths: List[Path] = [
        Path('fast', PathType.FASTEST.value, [123]),
        Path('q1', PathType.QUIET.value, [456], 1),
        Path('q2', PathType.QUIET.value, [678], 3),
        Path('q3', PathType.QUIET.value, [321], 5)
    ]
    paths[0].length = 10
    paths[0].bike_time_cost = 100
    paths[1].length = 8
    paths[1].bike_time_cost = 120
    paths[2].length = 14
    paths[2].bike_time_cost = 140
    paths[3].length = 12
    paths[3].bike_time_cost = 120
    
    path_set.set_unique_paths(paths)
    lens_before = tuple(p.length for p in path_set.paths)
    
    path_set.sort_bike_paths_by_length()
    lens_after = tuple(p.length for p in path_set.paths)

    assert lens_before == (10, 8, 14, 12)
    assert lens_after == (8, 10, 12, 14)


def test_drops_slower_shorter_bike_paths_1() -> dict:
    path_set = PathSet(Logger(), RoutingMode.QUIET, TravelMode.BIKE)
    paths: List[Path] = [
        Path('fast', PathType.FASTEST.value, [123]),
        Path('q1', PathType.QUIET.value, [456], 1),
        Path('q2', PathType.QUIET.value, [678], 3),
        Path('q3', PathType.QUIET.value, [321], 5)
    ]
    paths[0].length = 10
    paths[0].bike_time_cost = 100
    paths[1].length = 8
    paths[1].bike_time_cost = 120
    paths[2].length = 14
    paths[2].bike_time_cost = 140
    paths[3].length = 12
    paths[3].bike_time_cost = 160
    
    path_set.set_unique_paths(paths)
    path_set.sort_bike_paths_by_length()
    
    lens_before = tuple(p.length for p in path_set.paths)
    assert lens_before == (8, 10, 12, 14) 
    
    path_set.drop_slower_shorter_bike_paths()
    lens_after = tuple(p.length for p in path_set.paths)
    assert lens_after == (10, 14)


def test_drops_slower_shorter_bike_paths_2() -> dict:
    path_set = PathSet(Logger(), RoutingMode.QUIET, TravelMode.BIKE)
    paths: List[Path] = [
        Path('fast', PathType.FASTEST.value, [123]),
        Path('q1', PathType.QUIET.value, [456], 1),
        Path('q2', PathType.QUIET.value, [678], 3),
        Path('q3', PathType.QUIET.value, [321], 5)
    ]
    paths[0].length = 10
    paths[0].bike_time_cost = 100
    paths[1].length = 8
    paths[1].bike_time_cost = 120
    paths[2].length = 6
    paths[2].bike_time_cost = 140
    paths[3].length = 12
    paths[3].bike_time_cost = 160
    
    path_set.set_unique_paths(paths)
    path_set.sort_bike_paths_by_length()
    
    lens_before = tuple(p.length for p in path_set.paths)
    assert lens_before == (6, 8, 10, 12) 
    
    path_set.drop_slower_shorter_bike_paths()
    lens_after = tuple(p.length for p in path_set.paths)
    assert lens_after == (10, 12)


def test_reclassifies_first_as_fast_path_after_sort() -> dict:
    path_set = PathSet(Logger(), RoutingMode.QUIET, TravelMode.BIKE)
    paths: List[Path] = [
        Path('fast', PathType.FASTEST, [123]),
        Path('q1', PathType.QUIET, [456], 1),
        Path('q2', PathType.QUIET, [678], 3),
        Path('q3', PathType.QUIET, [321], 5)
    ]
    paths[0].length = 10
    paths[0].bike_time_cost = 100
    paths[1].length = 8
    paths[1].bike_time_cost = 120
    paths[2].length = 14
    paths[2].bike_time_cost = 140
    paths[3].length = 12
    paths[3].bike_time_cost = 120
    
    path_set.set_unique_paths(paths)    
    path_set.sort_bike_paths_by_length()
    assert tuple(p.length for p in path_set.paths) == (8, 10, 12, 14)
    assert path_set.paths[0].path_type == PathType.QUIET
    path_set.reclassify_path_types()
    for idx, path in enumerate(path_set.paths):
        if idx == 0:
            assert path.path_type == PathType.FASTEST
            assert path.path_id == PathType.FASTEST.value
        else:    
            assert path.path_type == PathType.QUIET
            assert path.path_id != PathType.FASTEST.value
