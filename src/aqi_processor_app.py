import time
import traceback
from utils.aqi_processor import AqiProcessor
from utils.graph_handler import GraphHandler
from datetime import datetime
from utils.logger import Logger

log = Logger(b_printing=True, log_file='aqi_processor_app.log')
G = GraphHandler(log, subset=False, add_wgs_center=True, gdf_attrs=['length'])
AQI = AqiProcessor(log, set_aws_secrets=True)

def process_aqi_updates_to_csv():
    AQI.set_wip_edge_aqi_csv_name()
    enfuser_data_key, aqi_zip_name = AQI.get_current_enfuser_key_filename()
    log.info('created key for current AQI: '+ enfuser_data_key)
    try:
        log.info('fetching enfuser data...')
        aqi_zip_name = AQI.fetch_enfuser_data(enfuser_data_key, aqi_zip_name)
        log.info('got aqi_zip: '+ aqi_zip_name)
        aqi_nc_name = AQI.extract_zipped_aqi(aqi_zip_name)
        log.info('extracted aqi_nc: '+ aqi_nc_name)
        aqi_tif_name = AQI.convert_aqi_nc_to_raster(aqi_nc_name)
        log.info('extracted aqi_tif: '+ aqi_tif_name)
        AQI.fillna_in_raster(aqi_tif_name, na_val=1.0)
        edge_aqi_csv_name = AQI.create_edge_aqi_csv(G, aqi_tif_name)
        log.info('exported edge_aqi_csv '+ edge_aqi_csv_name)
        log.info('AQI processing succeeded')
    except Exception:
        log.error('failed to process aqi data to: '+ AQI.wip_edge_aqi_csv)
        traceback.print_exc()
        time.sleep(30)
    finally:
        AQI.remove_temp_files()
        AQI.remove_old_aqi_files()
        AQI.reset_wip_edge_aqi_csv_name()

log.info('starting AQI processor app')

while True:
    if (AQI.new_aqi_available() == True):
        process_aqi_updates_to_csv()
    time.sleep(10)
