#%%
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import time
from multiprocessing import Pool
from fiona.crs import from_epsg
import utils.files as files
import utils.geometry as geom_utils
import utils.networks as nw
import utils.quiet_paths as qp
import utils.exposures as exps
import utils.utils as utils

#%% 1. Set graph extent, name and output folder
graph_name = 'hel-v3'
# graph_name = 'kumpula-v3'
out_dir = 'graphs'
# aoi_poly = files.get_koskela_kumpula_box()
aoi_poly = files.get_hel_poly(WGS84=True, buffer_m=1000)

#%% 2.1 Get undirected projected graph
print('\nGraph to construct:', graph_name)
start_time = time.time()
graph = nw.get_walkable_network(extent_poly_wgs=aoi_poly)
utils.print_duration(start_time, 'Graph acquired.', round_n=1)

#%% 2.2 Delete unnecessary edge attributes and get edges as dictionaries
nw.delete_unused_edge_attrs(graph, save_attrs=['uvkey', 'length', 'geometry', 'noises', 'osmid'])
edge_dicts = nw.get_all_edge_dicts(graph, attrs=['geometry'], by_nodes=False)
print('Got all edge dicts:', len(edge_dicts))

#%% 2.3 Add missing edge geometries to graph
start_time = time.time()
def get_edge_geoms(edge_dict):
    return nw.get_missing_edge_geometries(graph, edge_dict)
pool = Pool(processes=4)
edge_geom_dicts = pool.map(get_edge_geoms, edge_dicts)
pool.close()
for edge_d in edge_geom_dicts:
    nx.set_edge_attributes(graph, { edge_d['uvkey']: {'geometry': edge_d['geometry'], 'length': edge_d['length']}})
utils.print_duration(start_time, 'Missing edge geometries added.', round_n=1)

#%% 3.1 Remove unwalkable streets & tunnels from the graph [query graph for filtering]
print('Query unwalkable network...')
graph_filt = nw.get_unwalkable_network(extent_poly_wgs=aoi_poly)
filt_edge_dicts = nw.get_all_edge_dicts(graph_filt, by_nodes=False)
nw.add_missing_edge_geometries(graph_filt, filt_edge_dicts)

#%% 3.2 Remove unwalkable streets & tunnels from the graph [prepare networks for comparison]
filt_edge_gdf = nw.get_edge_gdf(graph_filt, by_nodes=True)
# add osmid as string to unwalkable (filter) edge gdfs
filt_edge_gdf['osmid_str'] = [nw.osmid_to_string(osmid) for osmid in filt_edge_gdf['osmid'] ]
print('Found', len(filt_edge_gdf), 'unwalkable edges within the extent.')
## save tunnel edge gdf to file
filt_edges_file = filt_edge_gdf.drop(['oneway', 'access', 'osmid', 'uvkey', 'service', 'junction', 'lanes'], axis=1, errors='ignore')
filt_edges_filename = graph_name +'_tunnel_edges'
filt_edges_file.to_file('data/networks.gpkg', layer=filt_edges_filename, driver="GPKG")
print('exported', filt_edges_filename, 'to data/networks.gpkg')
# get edge gdf from graph
edge_gdf = nw.get_edge_gdf(graph, by_nodes=True, attrs=['geometry', 'length', 'osmid'])
# add osmid as string to edge gdfs
edge_gdf['osmid_str'] = [nw.osmid_to_string(osmid) for osmid in edge_gdf['osmid']]

#%% 3.3 Find matching (unwalkable) edges from the graph 
edges_to_rm = []
edges_to_rm_gdfs = []
for idx, filt_edge in filt_edge_gdf.iterrows():
    utils.print_progress(idx, len(filt_edge_gdf), percentages=True)
    edges_found = edge_gdf.loc[edge_gdf['osmid_str'].str.contains(filt_edge['osmid_str'])].copy()
    if (len(edges_found) > 0):
        edges_found['filter_match'] = [geom_utils.lines_overlap(filt_edge['geometry'], geom, min_intersect=0.5) for geom in edges_found['geometry']]
        edges_match = edges_found.loc[edges_found['filter_match'] == True].copy()
        edges_to_rm_gdfs.append(edges_match)
        rm_edges = list(edges_match['uvkey'])
        edges_to_rm += rm_edges
all_edges_to_rm_gdf = gpd.GeoDataFrame(pd.concat(edges_to_rm_gdfs, ignore_index=True), crs=from_epsg(3879))
rm_edges_filename = graph_name +'_tunnel_edges_to_rm'
all_edges_to_rm_gdf.drop(columns=['filter_match', 'uvkey', 'osmid']).to_file('data/networks.gpkg', layer=rm_edges_filename, driver="GPKG")
print('\nexported', rm_edges_filename, 'to data/networks.gpkg')

# filter out duplicate edges to remove
edges_to_rm = list(set(edges_to_rm))
print('Found', len(edges_to_rm), 'edges to remove (by matching osmid & geometry).')

#%% 3.4 Remove matched unwalkable edges from the graph
removed = 0
for uvkey in edges_to_rm:
    try:
        graph.remove_edge(uvkey[0], uvkey[1])
        removed += 1
    except Exception:
        continue
    try:
        graph.remove_edge(uvkey[1], uvkey[0])
        removed += 1
    except Exception:
        continue
print('Removed', removed, 'edges from the graph')

#%% 4. Remove unnecessary attributes from the graph
nw.delete_unused_edge_attrs(graph)

#%% 5.1 Remove isolated nodes from the graph
isolate_nodes = list(nx.isolates(graph))
graph.remove_nodes_from(isolate_nodes)
print('Removed', len(isolate_nodes), 'isolated nodes.')

#%% 6.1 Find small unconnected subgraphs from the graph (to remove)
sub_graphs = nx.connected_component_subgraphs(graph)
# find nodes to remove from the subgraphs
rm_nodes = []
for sb in sub_graphs:
    sub_graph = sb.copy()
    print(f'subgraph has {sub_graph.number_of_nodes()} nodes')
    sub_graph_size = len(sub_graph.nodes)
    if (sub_graph_size < 40):
        rm_nodes += list(sub_graph.nodes)
    if (sub_graph_size >= 40 and sub_graph_size < len(graph.nodes)-5000):
        sub_g_edges = nw.get_edge_gdf(sub_graph, attrs=['geometry', 'length'])
        sub_g_filename = graph_name +'_large_subgraph_n'+ str(sub_graph_size)
        sub_g_edges.drop(columns=['uvkey']).to_file('data/networks.gpkg', layer=sub_g_filename, driver="GPKG")
        print('exported', sub_g_filename, 'to data/networks.gpkg')

print('Found', len(rm_nodes), 'nodes to remove (to remove subgrahs).')

#%% 6.2 Remove subgraphs (by nodes)
removed = 0
errors = 0
for rm_node in rm_nodes:
    try:
        graph.remove_node(rm_node)
        print('removed node', rm_node)
        removed += 1
    except Exception:
        errors += 1
print('Removed', removed, 'nodes from the graph (subgraphs)')
print('Could not remove', errors, 'nodes (removed already before).')

#%% 7. Remove isolated nodes again from the graph (just to be sure)
isolate_nodes = list(nx.isolates(graph))
graph.remove_nodes_from(isolate_nodes)
print('Found & removed', len(isolate_nodes), 'isolated nodes.')

#%% 8. Export filtered graph to file
graph_filename = graph_name +'_u_g_f_s.graphml'
print('Exporting graph of', graph.number_of_nodes(), 'nodes and', graph.number_of_edges(), 'edges to file...')
ox.save_graphml(graph, filename=graph_filename, folder='graphs', gephi=False)
print('Exported graph to file:', graph_filename)

#%% 9.1 Prepare for extraction of noise distances
noise_polys = files.get_noise_polygons()
noise_polys_sind = noise_polys.sindex
edge_dicts = nw.get_all_edge_dicts(graph, attrs=['geometry', 'length'], by_nodes=False)

# define function for spatial join between edge geometries and noise polygons
def get_edge_noises_df(edge_dicts):
    edge_gdf_sub = gpd.GeoDataFrame(edge_dicts, crs=from_epsg(3879))[['geometry', 'length', 'uvkey']]
    # build spatial indexes
    edges_sind = edge_gdf_sub.sindex
    # add noise split lines as list
    edge_gdf_sub['split_lines'] = [geom_utils.get_split_lines_list(line_geom, noise_polys) for line_geom in edge_gdf_sub['geometry']]
    # explode new rows from split lines column
    split_lines = geom_utils.explode_lines_to_split_lines(edge_gdf_sub, 'uvkey')
    # join noises to split lines
    split_line_noises = exps.get_noise_attrs_to_split_lines(split_lines, noise_polys)
    # aggregate noises back to edges
    edge_noises = exps.aggregate_line_noises(split_line_noises, 'uvkey')
    return edge_noises

#%% 9.2 Extract noise data by edge geometries
print('Extract contaminated distances to noises...')
# divide list of all edge dicts to chunks of 3000 edges
edge_chunks = utils.get_list_chunks(edge_dicts, 3000)
pool = Pool(processes=4)
start_time = time.time()
edge_noise_dfs = pool.map(get_edge_noises_df, edge_chunks)
time_elapsed = time.time() - start_time
edge_time = round(time_elapsed/len(edge_dicts), 5)
print('\n--- %s minutes ---' % (round(time_elapsed/60, 2)))
print('--- %s seconds per edge ---' % (edge_time))
print('Noises extracted by edge geometries.')

#%% 9.3 Update edge noises to graph
for edge_noises in edge_noise_dfs:
    nw.update_edge_noises_to_graph(edge_noises, graph)
print('Noises updated to graph.')

#%% 10. Export graph with edge noises
graph_filename = graph_name +'_u_g_n2_f_s.graphml'
print('Exporting graph of', graph.number_of_nodes(), 'nodes and', graph.number_of_edges(), 'edges to file...')
ox.save_graphml(graph, filename=graph_filename, folder='graphs', gephi=False)
print('Exported graph to file:', graph_filename)

#%% 11. Validate contaminated distances in the exported graph
graph_filename = graph_name +'_u_g_n2_f_s.graphml'
graph = files.load_graphml(graph_filename, folder=out_dir, directed=False)
# get edge gdf
edge_gdf = nw.get_edge_gdf(graph, attrs=['geometry', 'length', 'noises'], by_nodes=False)
edge_sample = edge_gdf.sample(n=10000)
# compare total length of contaminated distances along edge(s) to total length of edge(s)
edge_noise_length_check = exps.compare_lens_noises_lens(edge_sample)
edge_problems = edge_noise_length_check.query("len_noise_error < -0.005")
problem_count = len(edge_problems)
if (problem_count > 0):
    missing_ratio = round((problem_count/len(edge_gdf)) * 100, 3)
    print('Contaminated distances (noises) bad for:', problem_count, 'edges ('+ str(missing_ratio)+' %)')
else:
    print('Contaminated distances (noises) of edges ok.')

#%% 12. Validate exported graph for use in quiet path app
start_time = time.time()
nts = qp.get_noise_tolerances()
db_costs = qp.get_db_costs()
edge_gdf = nw.get_edge_gdf(graph, attrs=['geometry', 'length', 'noises'], by_nodes=False)
nw.set_graph_noise_costs(graph, edge_gdf, db_costs=db_costs, nts=nts)
# get full number of edges (undirected edges x 2)
edge_gdf_all = nw.get_edge_gdf(graph, by_nodes=True)
#%% check that set noise costs are ok
odd_edge_gdf_noise_costs = edge_gdf_all[(edge_gdf_all['nc_0.1'] > 1300) | (edge_gdf_all['nc_0.1'] < 0.02)]
if (len(odd_edge_gdf_noise_costs) > 0):
    missing_ratio = round((len(odd_edge_gdf_noise_costs)/len(edge_gdf_all)) * 100, 3)
    print('Edge noise costs odd for:', len(odd_edge_gdf_noise_costs) , 'edges ('+ str(missing_ratio)+' %)')
    odd_edge_noise_costs_filename = graph_name +'_odd_edge_noise_costs'
    odd_edge_gdf_noise_costs.drop(columns=['uvkey']).to_file('data/networks.gpkg', layer=odd_edge_noise_costs_filename, driver="GPKG")
else:
    print('Edge noise costs ok.')

#%%
