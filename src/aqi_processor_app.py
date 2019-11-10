import time
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from utils.aqi_processor import AqiProcessor
from utils.graph_handler import GraphHandler
from datetime import datetime

G = GraphHandler(subset=True, add_wgs_center=True)
AQI = AqiProcessor(set_aws_secrets=True)

def process_aqi_updates_to_csv():
    AQI.set_wip_edge_aqi_csv_name()
    enfuser_data_key, aqi_zip_name = AQI.get_current_enfuser_key_filename()
    print('\ncreated key for current AQI:', enfuser_data_key)
    try:
        print('fetching enfuser data...')
        aqi_zip_name = AQI.fetch_enfuser_data(enfuser_data_key, aqi_zip_name)
        print('got aqi_zip:', aqi_zip_name)
        aqi_nc_name = AQI.extract_zipped_aqi(aqi_zip_name)
        print('extracted aqi_nc:', aqi_nc_name)
        aqi_tif_name = AQI.convert_aqi_nc_to_raster(aqi_nc_name)
        print('extracted aqi_tif:', aqi_tif_name)
        AQI.fillna_in_raster(aqi_tif_name, na_val=1.0)
        edge_aqi_csv_name = AQI.create_edge_aqi_csv(G, aqi_tif_name)
        print('exported edge_aqi_csv:', edge_aqi_csv_name)
        utctime_str = datetime.utcnow().strftime('%y/%m/%d %H:%M:%S')
        print('AQI processing succeeded at (utc):', utctime_str)
    except Exception:
        traceback.print_exc()
    finally:
        AQI.remove_temp_files()
        AQI.remove_old_edge_aqi_csv_files()
        AQI.reset_wip_edge_aqi_csv_name()

print('starting AQI processing schedule')
while True:
    if (AQI.new_aqi_available() == True):
        process_aqi_updates_to_csv()
    time.sleep(10)
