from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from utils.aqi_processor import AqiProcessor
from utils.graph_handler import GraphHandler

aqi_update_interval_secs: int = 20
G = GraphHandler(subset=True)
AQI = AqiProcessor(aqi_dir='aqi_cache/')
aqi_scheduler = BackgroundScheduler()

def process_aqi_updates_to_csv():
    key, filename = AQI.get_current_enfuser_key_filename()
    print('current AQI key:', key)
    print('and filename:', filename)
    # TODO: aqi_zip = AQI.fetch_enfuser_data(key, filename)
    # TODO: aqi_nc = AQI.extract_zipped_aqi(aqi_zip)
    aqi_nc = 'allPollutants_2019-09-11T15.nc'
    aqi_raster = AQI.convert_aqi_nc_to_raster(aqi_nc)
    AQI.fillna_in_raster(aqi_raster, na_val=1.0)
    edge_aqi_updates_file = AQI.create_edge_aqi_update_csv(G, aqi_raster)
    AQI.remove_temp_files()
    return edge_aqi_updates_file

edge_aqi_updates_file = process_aqi_updates_to_csv()
