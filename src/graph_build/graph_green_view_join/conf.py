from dataclasses import dataclass


@dataclass(frozen=True)
class GraphGreenViewJoinConf:
    graph_file_in: str
    graph_file_out: str
    greenery_points_fp: str
    lc_wfs_cache_gpkg_fp: str
    lc_out_temp_dir: str
    db_edge_table: str
    db_low_veg_share_table: str
    db_high_veg_share_table: str
    db_dry_run: bool


conf = GraphGreenViewJoinConf(
    'graph_build/graph_green_view_join/graph_in/kumpula.graphml',
    'graph_build/graph_green_view_join/graph_out/kumpula.graphml',
    'graph_build/graph_green_view_join/data/greenery_points.gpkg',
    'graph_build/graph_green_view_join/data/land_cover_wfs_cache.gpkg',
    'graph_build/graph_green_view_join/temp',
    'edge_buffers_subset',  # edge_buffers
    'edge_subset_low_veg_shares',  # edge_low_veg_shares
    'edge_subset_high_veg_shares',  # edge_high_veg_shares
    True
)
