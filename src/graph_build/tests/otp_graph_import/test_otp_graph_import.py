
import pytest
from shapely.geometry import LineString, Polygon, Point, GeometryCollection
import pandas as pd
import geopandas as gpd
import shapely.wkt
from pyproj import CRS
from common.igraph import Node, Edge
import common.igraph as ig_utils
from graph_build.otp_graph_import.otp_graph_import import convert_otp_graph_to_igraph
from graph_build.tests.otp_graph_import.conftest import (
    conf, all_nodes_fp, all_edges_fp, kumpula_nodes_fp, kumpula_edges_fp, kumpula_aoi_fp
)


def intersects_polygon(geom: LineString, polygon: Polygon):
    if not geom or geom.is_empty:
        return True
    return True if geom.intersects(polygon) else False


@pytest.mark.skip(reason='run once')
def test_create_test_otp_graph_data():
    test_area = gpd.read_file(kumpula_aoi_fp)['geometry'][0]

    e = pd.read_csv(all_edges_fp, sep=';')
    assert len(e) == 1282306
    e[Edge.geometry.name] = [
        shapely.wkt.loads(geom) if isinstance(geom, str) else LineString() for geom in e[Edge.geometry.name]
    ]
    e = gpd.GeoDataFrame(e, geometry=Edge.geometry.name, crs=CRS.from_epsg(4326))
    e['in_test_area'] = [intersects_polygon(line, test_area) for line in e[Edge.geometry.name]]
    e_filt = e.query('in_test_area == True').copy()
    e_filt.drop(columns=['in_test_area']).to_csv(kumpula_edges_fp, sep=';')
    used_nodes = set(list(e_filt['node_orig_id'])+list(e_filt['node_dest_id']))

    n = pd.read_csv(all_nodes_fp, sep=';')
    n['in_test_area'] = [True if id_otp in used_nodes else False for id_otp in n['id_otp']]
    n_filt = n.query('in_test_area == True').copy()
    n_filt.drop(columns=['in_test_area']).to_csv(kumpula_nodes_fp, sep=';')
    assert len(n_filt) == 8564


def test_imports_otp_graph_to_igraph():
    graph = convert_otp_graph_to_igraph(
        node_csv_file = conf.node_csv_file,
        edge_csv_file = conf.edge_csv_file,
        hma_poly_file = conf.hma_poly_file,
        igraph_out_file = conf.igraph_out_file,
        b_export_otp_data_to_gpkg = False,
        b_export_decomposed_igraphs_to_gpkg = False,
        b_export_final_graph_to_gpkg = False,
        debug_otp_graph_gpkg = None,
        debug_igraph_gpkg = None
    )
    assert graph.ecount() == 3702
    assert graph.vcount() == 1328


def test_reads_the_created_igraph():
    graph = ig_utils.read_graphml(conf.igraph_out_file)
    assert graph.ecount() == 3702
    assert graph.vcount() == 1328
    attr_names = list(graph.vs[0].attributes().keys())
    for attr in attr_names:
        assert attr in [e.value for e in Node]  # no unknown node attributes allowed
    attr_names = list(graph.es[0].attributes().keys())
    for attr in attr_names:
        assert attr in [e.value for e in Edge]  # no unknown edge attributes allowed
    for n in graph.vs:
        attrs = n.attributes()
        assert attrs[Node.id_ig.value] == n.index
        assert isinstance(attrs[Node.id_ig.value], int)
        assert isinstance(attrs[Node.id_otp.value], str)
        assert isinstance(attrs[Node.name_otp.value], str)
        assert isinstance(attrs[Node.geometry.value], Point)
        assert isinstance(attrs[Node.geom_wgs.value], Point)
        assert isinstance(attrs[Node.traversable_walking.value], bool)
        assert isinstance(attrs[Node.traversable_biking.value], bool)
        assert isinstance(attrs[Node.traffic_light.value], bool)
    for e in graph.es:
        attrs = e.attributes()
        assert attrs[Edge.id_ig.value] == e.index
        assert isinstance(attrs[Edge.id_ig.value], int)
        assert isinstance(attrs[Edge.id_otp.value], str)
        assert isinstance(attrs[Edge.name_otp.value], str)
        assert isinstance(attrs[Edge.geometry.value], (LineString, GeometryCollection))
        assert isinstance(attrs[Edge.geom_wgs.value], (LineString, GeometryCollection))
        assert isinstance(attrs[Edge.length.value], float)
        assert isinstance(attrs[Edge.edge_class.value], str)
        assert isinstance(attrs[Edge.street_class.value], str)
        assert isinstance(attrs[Edge.is_stairs.value], bool)
        assert isinstance(attrs[Edge.is_no_thru_traffic.value], bool)
        assert isinstance(attrs[Edge.allows_walking.value], bool)
        assert isinstance(attrs[Edge.allows_biking.value], bool)
        assert isinstance(attrs[Edge.traversable_walking.value], bool)
        assert isinstance(attrs[Edge.traversable_biking.value], bool)
        assert isinstance(attrs[Edge.bike_safety_factor.value], float)


def test_gets_graph_data_as_gdf():
    graph = ig_utils.read_graphml(conf.igraph_out_file)
    # test read graph to wgs gdf
    gdf = ig_utils.get_edge_gdf(
        graph,
        id_attr=Edge.id_ig,
        attrs=[Edge.length],
        geom_attr=Edge.geom_wgs,
        drop_na_geoms=True
    )
    gdf['geom_length'] = [geom.length for geom in gdf[Edge.geom_wgs.name]]
    assert round(gdf['geom_length'].mean(), 6) == 0.000451
    # test read to projected gdf
    gdf = ig_utils.get_edge_gdf(
        graph,
        id_attr=Edge.id_ig,
        attrs=[Edge.length],
        geom_attr=Edge.geometry,
        drop_na_geoms=True
    )
    gdf['geom_length'] = [geom.length for geom in gdf[Edge.geometry.name]]
    assert round(gdf['geom_length'].mean(), 2) == 33.27
