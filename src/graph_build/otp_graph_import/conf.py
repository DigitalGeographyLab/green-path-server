from dataclasses import dataclass


@dataclass(frozen=True)
class OtpGraphImportConf:
    node_csv_file: str
    edge_csv_file: str
    hma_poly_file: str
    igraph_out_file: str
    b_export_otp_data_to_gpkg: bool
    b_export_decomposed_igraphs_to_gpkg: bool
    b_export_final_graph_to_gpkg: bool
    debug_otp_graph_gpkg: str
    debug_igraph_gpkg: str


conf = OtpGraphImportConf(
    node_csv_file = 'graph_build/otp_graph_import/otp_graph_data/kumpula_nodes.csv',
    edge_csv_file = 'graph_build/otp_graph_import/otp_graph_data/kumpula_edges.csv',
    hma_poly_file = 'graph_build/otp_graph_import/extent_data/HMA.geojson',
    igraph_out_file = 'graph_build/otp_graph_import/kumpula.graphml',
    b_export_otp_data_to_gpkg = False,
    b_export_decomposed_igraphs_to_gpkg = False,
    b_export_final_graph_to_gpkg = False,
    debug_otp_graph_gpkg = 'graph_build/otp_graph_import/debug/otp_graph_features.gpkg',
    debug_igraph_gpkg = 'graph_build/otp_graph_import/debug/otp2igraph_features.gpkg',
)
