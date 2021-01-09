import os

test_mode: bool = os.getenv('TEST_MODE', 'False') == 'True'
graph_subset: bool = os.getenv('GRAPH_SUBSET', 'False') == 'True'
research_mode: bool = os.getenv('RESEARCH_MODE', 'False') == 'True'
graph_file: str = r'graphs/kumpula.graphml' if graph_subset else r'graphs/hma.graphml'
