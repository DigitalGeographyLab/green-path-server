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
