import time
from os import listdir
from datetime import datetime
from utils.graph_handler import GraphHandler
from apscheduler.schedulers.background import BackgroundScheduler

class GraphAqiUpdater:
    """GraphAqiUpdater triggers an AQI to graph update if new AQI data is available in /aqi_cache.

    Attributes:
        graph_handler: A GraphHandler object that can update aqi values to a graph.
        aqi_dir (str): A path to an aqi_cache -directory (e.g. 'aqi_cache/').
        aqi_data_wip: The name of an aqi data csv file that is currently being updated to a graph.
        aqi_data_latest: The name of the aqi data csv file that was last updated to a graph.
        aqi_data_updatetime: datetime.utcnow() of the latest aqi update.
        scheduler: A BackgroundScheduler object that will periodically check for new aqi data and
            update it to a graph if available.
    """

    def __init__(self, graph_handler: GraphHandler, aqi_dir: str = 'aqi_cache/', start: bool = False):
        self.graph_handler = graph_handler
        self.aqi_dir = aqi_dir
        self.aqi_data_wip = ''
        self.aqi_data_latest = ''
        self.aqi_data_updatetime = None
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self.maybe_update_aqi_to_graph, 'interval', seconds=10, max_instances=2)
        if (start == True): self.scheduler.start()

    def maybe_update_aqi_to_graph(self):
        """Triggers an AQI to graph update if new AQI data is available and not yet updated or being updated.
        """
        new_aqi_data_csv = self.new_aqi_data_available()
        if (new_aqi_data_csv is not None):
            self.update_aqi_to_graph(new_aqi_data_csv)

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
        aqi_data_expected = self.get_expected_aqi_data_name()
        if (aqi_data_expected == self.aqi_data_latest):
            return None
        elif (aqi_data_expected == self.aqi_data_wip):
            print('AQI update already in progress')
            return None
        elif (aqi_data_expected in listdir(self.aqi_dir)):
            print('AQI update will be done')
            return aqi_data_expected
        else:
            print('expected AQI data is not available')
            return None

    def update_aqi_to_graph(self, aqi_updates_csv: str):
        self.aqi_data_wip = aqi_updates_csv
        try:
            self.graph_handler.update_aqi_to_graph(self.aqi_dir + aqi_updates_csv)
            utctime_str = datetime.utcnow().strftime('%y/%m/%d %H:%M:%S')
            print('AQI update succeeded at:', utctime_str,'(UTC)')
            self.aqi_data_updatetime = datetime.utcnow()
            self.aqi_data_latest = aqi_updates_csv
            self.aqi_data_wip = ''
        except Exception:
            print('failed to update AQI to graph')
            time.sleep(15)
            pass
