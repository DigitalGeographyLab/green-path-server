from dataclasses import dataclass


@dataclass(frozen=True)
class GraphExportConf:
    graph_id: str
    base_dir: str
    hel_extent_fp: str


conf = GraphExportConf(
    'kumpula',
    'graph_build/graph_export',
    'graph_build/common/hel.geojson'
)
