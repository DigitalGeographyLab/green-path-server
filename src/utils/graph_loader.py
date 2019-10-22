import utils.files as file_utils
import utils.graphs as graph_utils
import utils.noise_exposures as noise_exps

def load_graph_data(subset=False):
    """Loads and returns all graph related features needed in routing.
    """
    sens = noise_exps.get_noise_sensitivities()
    db_costs = noise_exps.get_db_costs()
    if (subset == True):
        graph = file_utils.load_graph_kumpula_noise()
    else:
        graph = file_utils.load_graph_full_noise()
    print('Graph of', graph.size(), 'edges read.')
    edge_gdf = graph_utils.get_edge_gdf(graph, attrs=['geometry', 'length', 'noises'])
    node_gdf = graph_utils.get_node_gdf(graph)
    print('Graph features extracted.')
    graph_utils.set_graph_noise_costs(graph, edge_gdf, db_costs=db_costs, sens=sens)
    edge_gdf = edge_gdf[['uvkey', 'geometry', 'noises']]
    print('Noise costs set.')
    edges_sind = edge_gdf.sindex
    nodes_sind = node_gdf.sindex
    print('Spatial index built.')
    return (graph, edge_gdf, node_gdf, edges_sind, nodes_sind)
