"""
General configuration file for Green Path server.

Currently features only one config setting:
    proj_crs_epsg:
        EPSG code for projected coordinate reference system (CRS)
        to be used in graph build and routing.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Conf:
    proj_crs_epsg: int


gp_conf = Conf(
    proj_crs_epsg=3879
)
