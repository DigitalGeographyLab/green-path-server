from enum import Enum


class TravelMode(Enum):
    WALK = 'walk'
    BIKE = 'bike'

class RoutingMode(Enum):
    CLEAN = 'clean'
    QUIET = 'quiet'

class PathType(Enum):
    SHORT = 'short'
    CLEAN = RoutingMode.CLEAN.value
    QUIET = RoutingMode.QUIET.value

class RoutingException(Exception):
    pass

class ErrorKeys(Enum):
    DESTINATION_NOT_FOUND = 'destination_not_found'
    ORIGIN_NOT_FOUND = 'origin_not_found'
    ORIGIN_OR_DEST_NOT_FOUND = 'origin_or_destination_not_found'
    PATHFINDING_ERROR = 'error_in_path_finding'
    PATH_PROCESSING_ERROR = 'error_in_path_processing'
    OD_SAME_LOCATION = 'od_are_same_location'
    NO_REAL_TIME_AQI_AVAILABLE = 'no_real_time_aqi_available'
    INVALID_TRAVEL_MODE_PARAM = 'invalid_travel_mode_in_request_params'
    INVALID_EXPOSURE_MODE_PARAM = 'invalid_exposure_mode_in_request_params'
    AQI_ROUTING_NOT_AVAILABLE = 'air_quality_routing_not_available'
    UNKNOWN_ERROR = 'unknown_error'