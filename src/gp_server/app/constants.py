from enum import Enum
from typing import Dict


class TravelMode(Enum):
    WALK = 'walk'
    BIKE = 'bike'

class RoutingMode(Enum):
    QUIET = 'quiet'
    GREEN = 'green'
    CLEAN = 'clean' # i.e. fresh air
    FAST = 'fast' # i.e. shortest
    SAFE = 'safe' # only for bike

class PathType(Enum):
    FASTEST = RoutingMode.FAST.value
    SAFEST = RoutingMode.SAFE.value
    QUIET = RoutingMode.QUIET.value
    GREEN = RoutingMode.GREEN.value
    CLEAN = RoutingMode.CLEAN.value

cost_prefix_dict: Dict[TravelMode, Dict[RoutingMode, str]] = {
    TravelMode.WALK: {
        RoutingMode.QUIET: 'c_n_',
        RoutingMode.GREEN: 'c_g_',
        RoutingMode.CLEAN: 'c_aq_'
    },
    TravelMode.BIKE: {
        RoutingMode.QUIET: 'c_n_b_',
        RoutingMode.GREEN: 'c_g_b_',
        RoutingMode.CLEAN: 'c_aq_b_'
    }
}

class RoutingException(Exception):
    pass

class ErrorKey(Enum):
    DESTINATION_NOT_FOUND = 'destination_not_found'
    ORIGIN_NOT_FOUND = 'origin_not_found'
    ORIGIN_OR_DEST_NOT_FOUND = 'origin_or_destination_not_found'
    PATHFINDING_ERROR = 'error_in_path_finding'
    PATH_PROCESSING_ERROR = 'error_in_path_processing'
    OD_SAME_LOCATION = 'od_are_same_location'
    NO_REAL_TIME_AQI_AVAILABLE = 'no_real_time_aqi_available'
    INVALID_TRAVEL_MODE_PARAM = 'invalid_travel_mode_in_request_params'
    INVALID_ROUTING_MODE_PARAM = 'invalid_routing_mode_in_request_params'
    AQI_ROUTING_NOT_AVAILABLE = 'air_quality_routing_not_available'
    UNKNOWN_ERROR = 'unknown_error'

status_code_by_error: Dict[ErrorKey, int] = {
    ErrorKey.DESTINATION_NOT_FOUND.value: 404,
    ErrorKey.ORIGIN_NOT_FOUND.value: 404,
    ErrorKey.ORIGIN_OR_DEST_NOT_FOUND.value: 404,
    ErrorKey.PATHFINDING_ERROR.value: 500,
    ErrorKey.PATH_PROCESSING_ERROR.value: 500,
    ErrorKey.OD_SAME_LOCATION.value: 400,
    ErrorKey.NO_REAL_TIME_AQI_AVAILABLE.value: 503,
    ErrorKey.INVALID_TRAVEL_MODE_PARAM.value: 400,
    ErrorKey.INVALID_ROUTING_MODE_PARAM.value: 400,
    ErrorKey.AQI_ROUTING_NOT_AVAILABLE.value: 503,
    ErrorKey.UNKNOWN_ERROR.value: 500
}
