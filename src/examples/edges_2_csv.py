"""
This script exports edge information of a graph to CSV.

The file can be run as a module (at src/):
    python -m examples.edges_2_csv

"""

import common.igraph as ig_utils
from common.igraph import Edge as E
import gp_server.app.noise_exposures as noise_exps
import pandas as pd


graph_dir = r'graphs'
graph_id = r'kumpula'
# graph_id = r'hma_r_hel-clip'
aqi_update_fp = fr'aqi_updates/yearly_2019_aqi_avg_sum_{graph_id}.csv'
out_csv_fp = fr'examples/{graph_id}_edges.csv'

edge_attrs_in = [
    E.id_ig,
    E.id_way,
    E.length,
    E.gvi,
    E.aqi,
    E.noises
]  # geometry is read by default

edge_attrs_out = [
    E.id_ig.name,
    E.length.name,
    E.gvi.name,
    E.aqi.name,
    E.noises.name,
    'mdB'
]  # only these are exported to CSV


graph = ig_utils.read_graphml(fr'{graph_dir}/{graph_id}.graphml')
edges = ig_utils.get_edge_gdf(graph, attrs=edge_attrs_in, drop_na_geoms=True)
# edges = edges.drop_duplicates(E.id_way.name)  # keep only edges unique by geometry


# ensure sum of noise exposure is length by adding missing exposures to 40dB
edges[E.noises.name] = edges.apply(
    lambda row: noise_exps.add_db_40_exp_to_noises(
        row[E.noises.name], row[E.length.name]), axis=1
)
edges['mdB'] = edges.apply(
    lambda row: noise_exps.get_mean_noise_level(
        row[E.noises.name], row[E.length.name]), axis=1
)
# stringify noises dict
edges[E.noises.name] = [str(noises) for noises in edges[E.noises.name]]


# join AQI to edge data
edge_aqis = pd.read_csv(aqi_update_fp)
edges = pd.merge(
    edges,
    edge_aqis,
    how='left',
    left_on=E.id_ig.name,
    right_on=E.id_ig.name,
    left_index=False,
    right_index=False,
    validate='one_to_one'
)


# export to CSV
edges = edges[edge_attrs_out].rename(columns={E.id_ig.name: 'edge_id'})
edges.to_csv(out_csv_fp, sep=';', index=False)

print(f'Exported edges to CSV: {out_csv_fp}')
print(f'Preview: {edges.head()}')
