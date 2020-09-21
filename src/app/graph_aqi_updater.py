import time
import ast
import gc
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
        __aqi_update_status (str): A message describing the current state of the AQI updater. 
        __aqi_data_wip (str): The name of an aqi data csv file that is currently being updated to a graph.
        __aqi_data_latest (str): The name of the aqi data csv file that was last updated to a graph.
        __aqi_data_updatetime: datetime.utcnow() of the latest successful aqi update.
        __G: A GraphHandler object via which aqi values are updated to a graph.
        __edge_df: A pandas DataFrame object containing edges to be updated (as by __create_updater_edge_df()).
        __sens (List[float]): A list of air quality sensitivity coefficients.
        __aqi_dir (str): A path to an aqi_cache -directory (e.g. 'aqi_cache/').
        __scheduler: A BackgroundScheduler instance that will periodically check for new aqi data and
            update it to a graph if available.
        __check_interval (int): The number of seconds between AQI update attempts.
    """

    def __init__(self, logger: Logger, G: GraphHandler, aqi_dir: str = 'aqi_updates/'):
        self.log = logger
        self.__aqi_update_status = ''
        self.__aqi_data_wip = ''
        self.__aqi_data_latest = ''
        self.__aqi_data_updatetime = None
        self.__G = G
        self.__edge_df = self.__create_updater_edge_df(G)
        self.__sens = aq_exps.get_aq_sensitivities()
        self.__aqi_dir = aqi_dir
        self.__scheduler = BackgroundScheduler()
        self.__check_interval = 5 + random.randint(1, 15)
        self.__scheduler.add_job(self.__maybe_read_update_aqi_to_graph, 'interval', seconds=self.__check_interval, max_instances=2)
        self.__start()

    def __create_updater_edge_df(self, G: GraphHandler):
        edge_df = ig_utils.get_edge_gdf(G.graph, attrs=[E.length, E.length_b])
        edge_df[E.id_ig.name] = edge_df.index
        edge_df = edge_df[[E.id_ig.name, E.length.name, E.length_b.name]]
        return edge_df

    def __start(self):
        self.log.info('starting graph aqi updater with check interval (s): '+ str(self.__check_interval))
        self.__scheduler.start()

    def get_aqi_update_status_response(self):
        return { 
            'b_updated': self.__bool_graph_aqi_is_up_to_date(), 
            'latest_data': self.__aqi_data_latest, 
            'update_time_utc': self.__get_aqi_update_time_str(), 
            'updated_since_secs': self.get_aqi_updated_since_secs()
            }

    def __maybe_read_update_aqi_to_graph(self):
        """Triggers an AQI to graph update if new AQI data is available and not yet updated or being updated.
        """
        new_aqi_data_csv = self.__new_aqi_data_available()
        if new_aqi_data_csv:
            try:
                self.__read_update_aqi_to_graph(new_aqi_data_csv)
            except Exception:
                self.__aqi_update_status = 'could not complete AQI update from: '+ new_aqi_data_csv
                self.log.error(self.__aqi_update_status)
                self.log.error(traceback.format_exc())
                self.log.warning('waiting 60 s after exception before next AQI update attempt')
                time.sleep(60)
            finally:
                gc.collect()
                self.__aqi_data_wip = ''

    def __get_expected_aqi_data_name(self) -> str:
        """Returns the name of the expected latest aqi data csv file based on the current time, e.g. aqi_2019-11-11T17.csv.
        """
        curdt = datetime.utcnow().strftime('%Y-%m-%dT%H')
        return 'aqi_'+ curdt +'.csv'

    def __get_aqi_update_time_str(self) -> str:
        return self.__aqi_data_updatetime.strftime('%y/%m/%d %H:%M:%S') if self.__aqi_data_updatetime is not None else None

    def get_aqi_updated_since_secs(self) -> int:
        if (self.__aqi_data_updatetime is not None):
            updated_since_secs = (datetime.utcnow() - self.__aqi_data_updatetime).total_seconds()
            return int(round(updated_since_secs))
        else:
            return None

    def __bool_graph_aqi_is_up_to_date(self) -> bool:
        """Returns True if the latest AQI is updated to graph, else returns False. This can be attached to an API endpoint
        from which clients can ask whether the green path service supports real-time AQ routing at the moment.
        """
        if (self.__aqi_data_updatetime is None):
            return False
        elif (self.get_aqi_updated_since_secs() < 60 * 70):
            return True
        else:
            return False

    def __new_aqi_data_available(self) -> str:
        """Returns the name of a new AQI csv file if it's not yet updated or being updated to a graph and it exists in aqi_dir.
        Else returns None.
        """
        new_aqi_csv = None
        aqi_update_status = ''

        aqi_data_expected = self.__get_expected_aqi_data_name()
        if (aqi_data_expected == self.__aqi_data_latest):
            aqi_update_status = 'latest AQI was updated to graph'
        elif (aqi_data_expected == self.__aqi_data_wip):
            aqi_update_status = 'AQI update already in progress'
        elif (aqi_data_expected in listdir(self.__aqi_dir)):
            aqi_update_status = 'AQI update will be done from: '+ aqi_data_expected
            new_aqi_csv = aqi_data_expected
        else:
            aqi_update_status = 'expected AQI data is not available ('+ aqi_data_expected +')'
        
        if (aqi_update_status != self.__aqi_update_status):
            self.log.info(aqi_update_status)
            self.__aqi_update_status = aqi_update_status
        return new_aqi_csv

    def __get_aq_update_attrs(self, aqi: float, length: float, length_b: float):
        aq_costs = aq_exps.get_aqi_costs(aqi, length, self.__sens)
        aq_costs_b = aq_exps.get_aqi_costs(aqi, length, self.__sens, length_b=length_b, prefix='b')
        return { 'aqi': aqi, **aq_costs, **aq_costs_b }

    def __get_missing_aq_update_attrs(self, length: float):
        """Set AQI to None to all edges that did not receive AQI update. Set high AQ costs to edges with geometry and 0 to 
        edges without.
        """
        aq_costs = {}
        if (length == 0.0):
            # set zero costs to edges with null geometry
            aq_costs = { 'aqc_'+ str(sen) : 0.0 for sen in self.__sens }
            aq_costs_b = { 'baqc_'+ str(sen) : 0.0 for sen in self.__sens }
        else:
            # set high AQ costs to edges outside the AQI data extent (aqi_coeff=40)
            aq_costs = { 'aqc_'+ str(sen) : round(length + length * 40, 2) for sen in self.__sens }
            aq_costs_b = { 'baqc_'+ str(sen) : round(length + length * 40, 2) for sen in self.__sens }
        return { 'aqi': None, **aq_costs, **aq_costs_b }
    
    def __read_update_aqi_to_graph(self, aqi_updates_csv: str):
        """Updates new AQI values and AQ costs to edges and AQI=None to edges that do not get AQI update. 
        """
        self.log.info('starting AQI update from: '+ aqi_updates_csv)
        self.__aqi_data_wip = aqi_updates_csv

        # read aqi update csv
        edge_aqi_updates = pd.read_csv(self.__aqi_dir + aqi_updates_csv)

        # inspect how many edges will get AQI
        aqi_update_count = len(edge_aqi_updates)
        if (len(self.__edge_df) != aqi_update_count):
            missing_ratio = round(100 * (len(self.__edge_df)-len(edge_aqi_updates)) / len(self.__edge_df), 1)
            self.log.info(f'AQI updates missing for {missing_ratio} % edges')

        # update AQI and AQ costs to graph
        aqi_update_df = pd.merge(self.__edge_df, edge_aqi_updates, on=E.id_ig.name, how='inner')
        if (len(aqi_update_df) != aqi_update_count):
            self.log.info(f'failed to merge AQI updates to edge gdf, missing {aqi_update_count - len(aqi_update_df)} edges')  
        
        aqi_update_df['aq_updates'] = aqi_update_df.apply(lambda x: self.__get_aq_update_attrs(x['aqi'], x[E.length.name], x[E.length_b.name]), axis=1)
        self.__G.update_edge_attr_to_graph(aqi_update_df, df_attr='aq_updates')

        # update missing AQI and AQ costs to edges outside AQI data extent (AQI -> None)
        missing_aqi_update_df = pd.merge(self.__edge_df, edge_aqi_updates, on=E.id_ig.name, how='outer', suffixes=['', '_'], indicator=True)
        missing_aqi_update_df = missing_aqi_update_df[missing_aqi_update_df['_merge'] == 'left_only']
        missing_aqi_update_df['aq_updates'] = [self.__get_missing_aq_update_attrs(length) for length in missing_aqi_update_df[E.length.name]]
        self.__G.update_edge_attr_to_graph(missing_aqi_update_df, df_attr='aq_updates')

        # check that all edges got either AQI value or AQI=None
        if (len(self.__edge_df) != (len(missing_aqi_update_df) + len(aqi_update_df))):
            self.log.error(f'edge count: {len(self.__edge_df)} != all AQI updates: {len(missing_aqi_update_df) + len(aqi_update_df)}')
        else:
            self.log.info('AQI update succeeded')

        # TODO see if these help to release some memory (remove if not)
        del edge_aqi_updates
        del aqi_update_df
        del missing_aqi_update_df
        
        self.__aqi_data_updatetime = datetime.utcnow()
        self.__aqi_data_latest = aqi_updates_csv
