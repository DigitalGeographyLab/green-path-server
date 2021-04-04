import os
import pytest


graph_export_graph_out_dir = r'graph_build/tests/graph_export/graph_out/'

@pytest.fixture(scope='session', autouse=True)
def remove_test_exports():

    files_to_rm = os.listdir(graph_export_graph_out_dir)

    for fn in files_to_rm:
        if fn == '.gitignore':
            continue
        os.remove(fr'{graph_export_graph_out_dir}{fn}')
        print(f'Removed test data: {graph_export_graph_out_dir}{fn}')
