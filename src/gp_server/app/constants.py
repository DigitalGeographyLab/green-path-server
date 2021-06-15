from enum import Enum
from typing import Dict


class TravelMode(Enum):
    WALK = 'walk'
    BIKE = 'bike'


class RoutingMode(Enum):
    GREEN = 'green'
    QUIET = 'quiet'
    CLEAN = 'clean'  # i.e. fresh air
    FAST = 'fast'  # i.e. shortest
    SAFE = 'safe'  # only for bike


class PathType(Enum):
    GREEN = RoutingMode.GREEN.value
    QUIET = RoutingMode.QUIET.value
    CLEAN = RoutingMode.CLEAN.value
    FASTEST = RoutingMode.FAST.value
    SAFEST = RoutingMode.SAFE.value


cost_prefix_dict: Dict[TravelMode, Dict[RoutingMode, str]] = {
    TravelMode.WALK: {
        RoutingMode.GREEN: 'c_g_',
        RoutingMode.QUIET: 'c_n_',
        RoutingMode.CLEAN: 'c_aq_'
    },
    TravelMode.BIKE: {
        RoutingMode.GREEN: 'c_g_b_',
        RoutingMode.QUIET: 'c_n_b_',
        RoutingMode.CLEAN: 'c_aq_b_'
    }
}


path_type_by_routing_mode: Dict[RoutingMode, PathType] = {
    RoutingMode.GREEN: PathType.GREEN,
    RoutingMode.QUIET: PathType.QUIET,
    RoutingMode.CLEAN: PathType.CLEAN,
    RoutingMode.FAST: PathType.FASTEST,
    RoutingMode.SAFE: PathType.SAFEST,
}


class RoutingException(Exception):
    pass


class ErrorKey(Enum):
    ORIGIN_NOT_FOUND = 'origin_not_found'
    DESTINATION_NOT_FOUND = 'destination_not_found'
    ORIGIN_OR_DEST_NOT_FOUND = 'origin_or_destination_not_found'
    WALK_ROUTING_NOT_AVAILABLE = 'walk_routing_not_available_by_config'
    BIKE_ROUTING_NOT_AVAILABLE = 'bike_routing_not_available_by_config'
    GREEN_PATH_ROUTING_NOT_AVAILABLE = 'green_path_routing_not_available_by_config'
    QUIET_PATH_ROUTING_NOT_AVAILABLE = 'quiet_path_routing_not_available_by_config'
    CLEAN_PATH_ROUTING_NOT_AVAILABLE = 'clean_path_routing_not_available_by_config'
    PATHFINDING_ERROR = 'error_in_path_finding'
    PATH_PROCESSING_ERROR = 'error_in_path_processing'
    OD_SAME_LOCATION = 'od_are_same_location'
    NO_REAL_TIME_AQI_AVAILABLE = 'no_real_time_aqi_available'
    INVALID_TRAVEL_MODE_PARAM = 'invalid_travel_mode_in_request_params'
    INVALID_ROUTING_MODE_PARAM = 'invalid_routing_mode_in_request_params'
    SAFE_PATHS_ONLY_AVAILABLE_FOR_BIKE = 'routing_mode_safe_is_only_for_bike'
    AQI_ROUTING_NOT_AVAILABLE = 'air_quality_routing_not_available'
    UNKNOWN_ERROR = 'unknown_error'


status_code_by_error: Dict[ErrorKey, int] = {
    ErrorKey.ORIGIN_NOT_FOUND.value: 404,
    ErrorKey.DESTINATION_NOT_FOUND.value: 404,
    ErrorKey.ORIGIN_OR_DEST_NOT_FOUND.value: 404,
    ErrorKey.WALK_ROUTING_NOT_AVAILABLE.value: 503,
    ErrorKey.BIKE_ROUTING_NOT_AVAILABLE.value: 503,
    ErrorKey.GREEN_PATH_ROUTING_NOT_AVAILABLE.value: 503,
    ErrorKey.QUIET_PATH_ROUTING_NOT_AVAILABLE.value: 503,
    ErrorKey.CLEAN_PATH_ROUTING_NOT_AVAILABLE.value: 503,
    ErrorKey.PATHFINDING_ERROR.value: 500,
    ErrorKey.PATH_PROCESSING_ERROR.value: 500,
    ErrorKey.OD_SAME_LOCATION.value: 400,
    ErrorKey.NO_REAL_TIME_AQI_AVAILABLE.value: 503,
    ErrorKey.INVALID_TRAVEL_MODE_PARAM.value: 400,
    ErrorKey.INVALID_ROUTING_MODE_PARAM.value: 400,
    ErrorKey.SAFE_PATHS_ONLY_AVAILABLE_FOR_BIKE.value: 400,
    ErrorKey.AQI_ROUTING_NOT_AVAILABLE.value: 503,
    ErrorKey.UNKNOWN_ERROR.value: 500
}
