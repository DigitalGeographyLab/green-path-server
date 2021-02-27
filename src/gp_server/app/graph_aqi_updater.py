import time
import gc
import random
import traceback
import pandas as pd
from os import listdir
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
import gp_server.env as env
from gp_server.app.graph_handler import GraphHandler
import gp_server.app.aq_exposures as aq_exps
from gp_server.app.logger import Logger
import gp_server.utils.igraph as ig_utils
from gp_server.utils.igraph import Edge as E
from typing import Union
from gp_server.app.constants import cost_prefix_dict, RoutingMode, TravelMode


class GraphAqiUpdater:
    """GraphAqiUpdater updates new AQI to graph if new AQI data is available in /aqi_cache.

    Attributes:
        __aqi_update_status (str): A message describing the current state of the AQI updater. 
        __aqi_data_wip (str): The name of an aqi data csv file that is currently being updated to a graph.
        __aqi_data_latest (str): The name of the aqi data csv file that was last updated to a graph.
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
        self.__aqi_update_error = ''
        self.__aqi_data_wip = ''
        self.__aqi_data_latest = ''
        self.__G = G
        self.__edge_df = self.__create_updater_edge_df(G)
        self.__sens = aq_exps.get_aq_sensitivities()
        self.__aqi_dir = aqi_dir if not env.test_mode else 'aqi_updates/test_data/'
        self.__scheduler = BackgroundScheduler()
        self.__check_interval = 5 + random.randint(1, 15)
        self.__scheduler.add_job(
            self.__maybe_read_update_aqi_to_graph, 
            'interval', 
            seconds=self.__check_interval, 
            max_instances=2,
            next_run_time=datetime.now()
        )
        self.__start()

    def __create_updater_edge_df(self, G: GraphHandler):
        edge_df = ig_utils.get_edge_gdf(G.graph, attrs=[E.length, E.length_b])
        edge_df[E.id_ig.name] = edge_df.index
        edge_df = edge_df[[E.id_ig.name, E.length.name, E.length_b.name]]
        return edge_df

    def __start(self):
        self.log.info('Starting graph aqi updater with check interval (s): '+ str(self.__check_interval))
        self.__scheduler.start()

    def __get_latest_aqi_data_utc_time_secs(self) -> Union[int, None]:
        if self.__aqi_data_latest:
            try:
                aqi_data_time = self.__aqi_data_latest.split('aqi_', 1)[1].split('.')[0]
                dt = datetime.strptime(aqi_data_time, '%Y-%m-%dT%H')
                return int(dt.replace(tzinfo=timezone.utc).timestamp())
            except Exception:
                self.log.error(f'Could not parse UTC time from {self.__aqi_data_latest}')
                return None
        else:
            return None

    def get_aqi_update_status_response(self):
        return { 
            'aqi_data_updated': self.__aqi_data_latest != '',
            'aqi_data_utc_time_secs': self.__get_latest_aqi_data_utc_time_secs()
            }

    def __maybe_read_update_aqi_to_graph(self):
        """Triggers an AQI to graph update if new AQI data is available and not yet updated or being updated.
        """
        new_aqi_data_csv = self.__new_aqi_data_available()
        if new_aqi_data_csv:
            for attempt in range(3):
                try:
                    self.__aqi_update_error = ''
                    self.__read_update_aqi_to_graph(new_aqi_data_csv)
                    self.__validate_graph_aqi()
                    self.__aqi_data_wip = ''
                    gc.collect()
                    break
                except Exception:
                    self.__aqi_update_error = f'AQI update attempt no. {attempt+1}/3 failed from AQI update file: {new_aqi_data_csv}'
                    self.log.error(self.__aqi_update_error)
                    self.log.error(traceback.format_exc())
                    if attempt < 2:
                        wait_for_s = 10 + attempt * 10
                        self.log.warning(f'Waiting {wait_for_s} s after exception before next AQI update attempt')
                        time.sleep(wait_for_s)
                    gc.collect()

    def __get_expected_aqi_data_name(self) -> str:
        """Returns the name of the expected latest aqi data csv file based on the current time, e.g. aqi_2019-11-11T17.csv.
        """
        if env.test_mode:
            return 'aqi_2020-10-25T14.csv'
        else:
            curdt = datetime.utcnow().strftime('%Y-%m-%dT%H')
            return 'aqi_'+ curdt +'.csv'

    def __new_aqi_data_available(self) -> str:
        """Returns the name of a new AQI csv file if it's not yet updated or being updated to a graph and it exists in aqi_dir.
        Else returns None.
        """
        new_aqi_csv = None
        aqi_update_status = ''

        aqi_data_expected = self.__get_expected_aqi_data_name()
        if self.__aqi_update_error:
            aqi_update_status = self.__aqi_update_error
        elif (aqi_data_expected == self.__aqi_data_latest):
            aqi_update_status = 'Latest AQI was updated to graph'
        elif (aqi_data_expected == self.__aqi_data_wip):
            aqi_update_status = 'AQI update already in progress'
        elif (aqi_data_expected in listdir(self.__aqi_dir)):
            aqi_update_status = 'AQI update will be done from: '+ aqi_data_expected
            new_aqi_csv = aqi_data_expected
        else:
            aqi_update_status = 'Expected AQI data is not available ('+ aqi_data_expected +')'
        
        if (aqi_update_status != self.__aqi_update_status):
            self.log.info(aqi_update_status)
            self.__aqi_update_status = aqi_update_status
        return new_aqi_csv

    def __get_aq_update_attrs(self, aqi: float, length: float, length_b: float):        
        aq_costs = aq_exps.get_aqi_costs(
            aqi, length, self.__sens
        ) if env.walking_enabled else {}
        
        aq_costs_b = aq_exps.get_aqi_costs(
            aqi, length, self.__sens, length_b=length_b, travel_mode=TravelMode.BIKE
        ) if env.cycling_enabled else {}

        return {
            'aqi': aqi,
            **aq_costs,
            **aq_costs_b
        }

    def __get_missing_aq_update_attrs(self, length: float):
        """Set AQI to None to all edges that did not receive AQI update. Set high AQ costs to edges with geometry and 0 to 
        edges without.
        """
        aq_costs = {}
        cost_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.CLEAN]
        cost_prefix_bike = cost_prefix_dict[TravelMode.BIKE][RoutingMode.CLEAN]

        if (length == 0.0):
            # set zero costs to edges with null geometry
            aq_costs = { cost_prefix + str(sen) : 0.0 for sen in self.__sens }
            aq_costs_b = { cost_prefix_bike + str(sen) : 0.0 for sen in self.__sens }
        else:
            # set high AQ costs to edges outside the AQI data extent (aqi_coeff=40)
            aq_costs = { cost_prefix + str(sen) : round(length + length * 40, 2) for sen in self.__sens }
            aq_costs_b = { cost_prefix_bike + str(sen) : round(length + length * 40, 2) for sen in self.__sens }
        
        aq_costs = aq_costs if env.walking_enabled else {}
        aq_costs_b = aq_costs_b if env.cycling_enabled else {}
        
        return { E.aqi.value: None, **aq_costs, **aq_costs_b }
    
    def __read_update_aqi_to_graph(self, aqi_updates_csv: str):
        """Updates new AQI values and AQ costs to edges and AQI=None to edges that do not get AQI update. 
        """
        self.log.info('Starting AQI update from: '+ aqi_updates_csv)
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
            self.log.info(f'Failed to merge AQI updates to edge gdf, missing {aqi_update_count - len(aqi_update_df)} edges')  
        
        aqi_update_df['aq_updates'] = aqi_update_df.apply(lambda x: self.__get_aq_update_attrs(x['aqi'], x[E.length.name], x[E.length_b.name]), axis=1)
        self.__G.update_edge_attr_to_graph(aqi_update_df, df_attr='aq_updates')

        # update missing AQI and AQ costs to edges outside AQI data extent (AQI -> None)
        missing_aqi_update_df = pd.merge(self.__edge_df, edge_aqi_updates, on=E.id_ig.name, how='outer', suffixes=['', '_'], indicator=True)
        missing_aqi_update_df = missing_aqi_update_df[missing_aqi_update_df['_merge'] == 'left_only']
        missing_aqi_update_df['aq_updates'] = [self.__get_missing_aq_update_attrs(length) for length in missing_aqi_update_df[E.length.name]]
        self.__G.update_edge_attr_to_graph(missing_aqi_update_df, df_attr='aq_updates')

        # check that all edges got either AQI value or AQI=None
        if (len(self.__edge_df) != (len(missing_aqi_update_df) + len(aqi_update_df))):
            self.log.error(f'Edge count: {len(self.__edge_df)} != all AQI updates: {len(missing_aqi_update_df) + len(aqi_update_df)}')
        else:
            self.log.info('AQI update done')

        # TODO see if these help to release some memory (remove if not)
        del edge_aqi_updates
        del aqi_update_df
        del missing_aqi_update_df
        
        self.__aqi_data_latest = aqi_updates_csv

    def __validate_graph_aqi(self):
        edge_count = self.__G.graph.ecount()
        has_aqi_count = 0
        missing_aqi_count = 0
        for edge in self.__G.graph.es:
            if not edge[E.aqi.value]:
                missing_aqi_count += 1
            else:
                has_aqi_count += 1

        aqi_ok_ratio = has_aqi_count/edge_count
        missing_ratio = missing_aqi_count/edge_count

        if aqi_ok_ratio < 0.7 or missing_ratio > 0.3:
            raise Exception(f'Graph got incomplete AQI update (aqi_ok_ratio: {round(aqi_ok_ratio, 4)}, missing_ratio: {round(missing_ratio, 4)})')
        else:
            self.log.info(f'Graph AQI update resulted aqi_ok_ratio: {round(aqi_ok_ratio, 4)} & missing_ratio: {round(missing_ratio, 4)}')
