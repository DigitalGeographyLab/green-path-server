from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from utils.aqi_processor import AqiProcessor
from utils.graph_handler import GraphHandler

aqi_update_interval_secs: int = 20
G = GraphHandler(subset=True)
AQI = AqiProcessor(aqi_dir='aqi_cache/')
AQI.set_aws_secrets()
aqi_scheduler = BackgroundScheduler()

def process_aqi_updates_to_csv():
    enfuser_data_key, aqi_zip_name = AQI.get_current_enfuser_key_filename()
    print('current AQI key:', enfuser_data_key)
    print('and filename:', aqi_zip_name)
    aqi_zip_name = AQI.fetch_enfuser_data(enfuser_data_key, aqi_zip_name)
    print('got aqi_zip:', aqi_zip_name)
    aqi_nc_name = AQI.extract_zipped_aqi(aqi_zip_name)
    print('extracted aqi_nc:', aqi_nc_name)
    aqi_tif_name = AQI.convert_aqi_nc_to_raster(aqi_nc_name)
    print('extracted aqi_tif:', aqi_tif_name)
    AQI.fillna_in_raster(aqi_tif_name, na_val=1.0)
    edge_aqi_csv_name = AQI.create_edge_aqi_csv(G, aqi_tif_name)
    print('created edge_aqi_csv:', edge_aqi_csv_name)
    AQI.remove_temp_files()
    return edge_aqi_csv_name

edge_aqi_csv_name = process_aqi_updates_to_csv()
