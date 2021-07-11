from dataclasses import dataclass


@dataclass(frozen=True)
class GraphNoiseJoinConf:
    graph_in_fp: str
    noise_data_fp: str
    noise_data_extent_fp: str
    nodata_fp: str
    nodata_layer_name: str
    debug_fp: str
    noise_data_csv_dir: str
    graph_out_fp: str


conf = GraphNoiseJoinConf(
    graph_in_fp=r'graph_build/graph_noise_join/data/kumpula.graphml',
    noise_data_fp=r'graph_build/graph_noise_join/data/noise_data_processed.gpkg',
    noise_data_extent_fp=r'graph_build/graph_noise_join/data/HMA.geojson',
    nodata_fp=r'graph_build/graph_noise_join/data/extents.gpkg',
    nodata_layer_name=r'municipal_boundaries',
    debug_fp=r'graph_build/graph_noise_join/debug/noise_join_debug.gpkg',
    noise_data_csv_dir=r'graph_build/graph_noise_join/out_csv',
    graph_out_fp=r'graph_build/graph_noise_join/out_graph/kumpula.graphml'
)
