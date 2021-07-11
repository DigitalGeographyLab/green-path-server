import os
import pytest
from graph_build.otp_graph_import.conf import OtpGraphImportConf


conf = OtpGraphImportConf(
    node_csv_file = 'graph_build/tests/otp_graph_import/data/test_nodes.csv',
    edge_csv_file = 'graph_build/tests/otp_graph_import/data/test_edges.csv',
    hma_poly_file = 'graph_build/tests/common/HMA.geojson',
    igraph_out_file = 'graph_build/tests/otp_graph_import/temp/test_graph.graphml',
    b_export_otp_data_to_gpkg = False,
    b_export_decomposed_igraphs_to_gpkg = False,
    b_export_final_graph_to_gpkg = False,
    debug_otp_graph_gpkg = None,
    debug_igraph_gpkg = None
)

all_nodes_fp = 'graph_build/otp_graph_import/otp_nodes.csv'
all_edges_fp = 'graph_build/otp_graph_import/otp_edges.csv'
kumpula_nodes_fp = 'graph_build/tests/otp_graph_import/data/kumpula_nodes.csv'
kumpula_edges_fp = 'graph_build/tests/otp_graph_import/data/kumpula_edges.csv'
kumpula_aoi_fp = 'graph_build/tests/otp_graph_import/data/kumpula_aoi.geojson'

graph_import_graph_out_dir = r'graph_build/tests/otp_graph_import/temp/'


@pytest.fixture(scope='session', autouse=True)
def remove_test_exports():

    files_to_rm = os.listdir(graph_import_graph_out_dir)

    for fn in files_to_rm:
        if fn == '.gitignore':
            continue
        os.remove(fr'{graph_import_graph_out_dir}{fn}')
        print(f'Removed test data: {graph_import_graph_out_dir}{fn}')
