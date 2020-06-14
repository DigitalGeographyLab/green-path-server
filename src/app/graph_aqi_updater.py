import time
import ast
import random
import traceback
import pandas as pd
from shapely.geometry import LineString
from os import listdir
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.graph_handler import GraphHandler
import utils.aq_exposures as aq_exps
import utils.igraphs as ig_utils
from app.logger import Logger
import utils.igraphs as ig_utils
from utils.igraphs import Edge as E
from typing import List, Set, Dict, Tuple, Optional

class GraphAqiUpdater:
    """GraphAqiUpdater triggers an AQI to graph update if new AQI data is available in /aqi_cache.

    Attributes:
        graph_handler: A GraphHandler object via which aqi values can be updated to a graph.
        aqi_dir (str): A path to an aqi_cache -directory (e.g. 'aqi_cache/').
        aqi_data_wip: The name of an aqi data csv file that is currently being updated to a graph.
        aqi_data_latest: The name of the aqi data csv file that was last updated to a graph.
        aqi_data_updatetime: datetime.utcnow() of the latest aqi update.
        scheduler: A BackgroundScheduler instance that will periodically check for new aqi data and
            update it to a graph if available.
    """

    def __init__(self, logger: Logger, G: GraphHandler, aqi_dir: str = 'aqi_updates/'):
        self.log = logger
        self.G = G
        self.edge_df = self.create_updater_edge_df(G)
        self.sens = aq_exps.get_aq_sensitivities()
        self.aqi_update_status = ''
        self.aqi_dir = aqi_dir
        self.aqi_data_wip = ''
        self.aqi_data_latest = ''
        self.aqi_data_updatetime = None
        self.scheduler = BackgroundScheduler()
        self.check_interval = 5 + random.randint(1, 15)
        self.scheduler.add_job(self.maybe_read_update_aqi_to_graph, 'interval', seconds=self.check_interval, max_instances=2)
        self.start()

    def create_updater_edge_df(self, G: GraphHandler):
        edge_df = ig_utils.get_edge_gdf(G.graph, attrs=[E.length])
        edge_df[E.id_ig.name] = edge_df.index
        return edge_df[[E.id_ig.name, E.length.name]]

    def start(self):
        self.log.info('starting graph aqi updater with check interval (s): '+ str(self.check_interval))
        self.scheduler.start()

    def get_aqi_update_status_response(self):
        return { 
            'b_updated': self.bool_graph_aqi_is_up_to_date(), 
            'latest_data': self.aqi_data_latest, 
            'update_time_utc': self.get_aqi_update_time_str(), 
            'updated_since_secs': self.get_aqi_updated_since_secs()
            }

    def maybe_read_update_aqi_to_graph(self):
        """Triggers an AQI to graph update if new AQI data is available and not yet updated or being updated.
        """
        new_aqi_data_csv = self.new_aqi_data_available()
        if (new_aqi_data_csv is not None):
            try:
                self.read_update_aqi_to_graph(new_aqi_data_csv)
            except Exception:
                self.aqi_update_status = 'could not complete AQI update from: '+ new_aqi_data_csv
                self.log.error(self.aqi_update_status)
                traceback.print_exc()
                self.log.warning('waiting 60 s after exception before next AQI update attempt')
                time.sleep(60)
                self.aqi_data_wip = ''

    def get_expected_aqi_data_name(self) -> str:
        """Returns the name of the expected latest aqi data csv file based on the current time, e.g. aqi_2019-11-11T17.csv.
        """
        curdt = datetime.utcnow().strftime('%Y-%m-%dT%H')
        return 'aqi_'+ curdt +'.csv'

    def get_aqi_update_time_str(self) -> str:
        return self.aqi_data_updatetime.strftime('%y/%m/%d %H:%M:%S') if self.aqi_data_updatetime is not None else None

    def get_aqi_updated_since_secs(self) -> int:
        if (self.aqi_data_updatetime is not None):
            updated_since_secs = (datetime.utcnow() - self.aqi_data_updatetime).total_seconds()
            return int(round(updated_since_secs))
        else:
            return None

    def bool_graph_aqi_is_up_to_date(self) -> bool:
        """Returns True if the latest AQI is updated to graph, else returns False. This can be attached to an API endpoint
        from which clients can ask whether the green path service supports real-time AQ routing at the moment.
        """
        if (self.aqi_data_updatetime is None):
            return False
        elif (self.get_aqi_updated_since_secs() < 60 * 70):
            return True
        else:
            return False

    def new_aqi_data_available(self) -> str:
        """Returns the name of a new AQI csv file if it's not yet updated or being updated to a graph and it exists in aqi_dir.
        Else returns None.
        """
        new_aqi_available = None
        aqi_update_status = ''

        aqi_data_expected = self.get_expected_aqi_data_name()
        if (aqi_data_expected == self.aqi_data_latest):
            aqi_update_status = 'latest AQI was updated to graph'
        elif (aqi_data_expected == self.aqi_data_wip):
            aqi_update_status = 'AQI update already in progress'
        elif (aqi_data_expected in listdir(self.aqi_dir)):
            aqi_update_status = 'AQI update will be done from: '+ aqi_data_expected
            new_aqi_available = aqi_data_expected
        else:
            aqi_update_status = 'expected AQI data is not available ('+ aqi_data_expected +')'
        
        if (aqi_update_status != self.aqi_update_status):
            self.log.info(aqi_update_status)
            self.aqi_update_status = aqi_update_status
        return new_aqi_available

    def get_aq_update_attrs(self, aqi: float, length: float):
        aq_costs = aq_exps.get_aqi_costs(aqi, length, self.sens)
        return { 'aqi': aqi, **aq_costs }

    def get_missing_aq_update_attrs(self, length: float):
        """Set AQI to None to all edges that did not receive AQI update. 
        """
        aq_costs = {}
        if (length == 0.0):
            # set zero costs to edges with null geometry
            aq_costs = { 'aqc_'+ str(sen) : 0 for sen in self.sens }
        else:
            # set high AQ costs to edges outside the AQI data extent (aqi_coeff=50)
            aq_costs = { 'aqc_'+ str(sen) : aq_exps.calc_aqi_cost(length, aqi_coeff=50, sen=1) for sen in self.sens }
        return { 'aqi': None, **aq_costs }
    
    def read_update_aqi_to_graph(self, aqi_updates_csv: str):
        """Updates new AQI values and AQ costs to edges and AQI=None to edges that do not get AQI update. 
        """
        self.log.info('starting AQI update from: '+ aqi_updates_csv)
        self.aqi_data_wip = aqi_updates_csv

        # read aqi update csv
        edge_aqi_updates = pd.read_csv(self.aqi_dir + aqi_updates_csv)

        # inspect how many edges will get AQI
        aqi_update_count = len(edge_aqi_updates)
        if (len(self.edge_df) != aqi_update_count):
            missing_ratio = round(100 * (len(self.edge_df)-len(edge_aqi_updates)) / len(self.edge_df), 1)
            self.log.info(f'AQI updates missing for {missing_ratio} % edges')

        # update AQI and AQ costs to graph
        aqi_update_df = pd.merge(self.edge_df, edge_aqi_updates, on=E.id_ig.name, how='inner')
        if (len(aqi_update_df) != aqi_update_count):
            self.log.info(f'failed to merge AQI updates to edge gdf, missing {aqi_update_count - len(aqi_update_df)} edges')  
        
        aqi_update_df['aq_updates'] = aqi_update_df.apply(lambda x: self.get_aq_update_attrs(x['aqi'], x[E.length.name]), axis=1)
        self.G.update_edge_attr_to_graph(aqi_update_df, df_attr='aq_updates')

        # update missing AQI and AQ costs to edges outside AQI data extent (AQI -> None)
        missing_aqi_update_df = pd.merge(self.edge_df, edge_aqi_updates, on=E.id_ig.name, how='outer', suffixes=['', '_'], indicator=True)
        missing_aqi_update_df = missing_aqi_update_df[missing_aqi_update_df['_merge'] == 'left_only']
        missing_aqi_update_df['aq_updates'] = [self.get_missing_aq_update_attrs(length) for length in missing_aqi_update_df[E.length.name]]
        self.G.update_edge_attr_to_graph(missing_aqi_update_df, df_attr='aq_updates')

        # check that all edges got either AQI value or AQI=None
        if (len(self.edge_df) != (len(missing_aqi_update_df) + len(aqi_update_df))):
            self.log.error(f'edge count: {len(self.edge_df)} != all AQI updates: {len(missing_aqi_update_df) + len(aqi_update_df)}')
        else:
            self.log.info('AQI update succeeded')
        
        self.aqi_data_updatetime = datetime.utcnow()
        self.aqi_data_latest = aqi_updates_csv
        self.aqi_data_wip = ''
