from graph_build.otp_graph_import.conf import conf as otp_graph_import_conf
import graph_build.otp_graph_import.otp_graph_import as otp_graph_import
from graph_build.noise_data_preprocessing.conf import conf as noise_data_conf
import graph_build.noise_data_preprocessing.noise_data_preprocessing as noise_data_preprocessing
from graph_build.graph_green_view_join.conf import conf as green_viw_join_conf
import graph_build.graph_green_view_join.fetch_land_cover as fetch_land_cover
import graph_build.graph_green_view_join.graph_green_view_join as graph_green_view_join
import graph_build.graph_green_view_join.land_cover_overlay_analysis as gvi_lc_analysis
from graph_build.graph_export.conf import conf as graph_export_conf
import graph_build.graph_export.main as graph_export
from graph_build.graph_noise_join.conf import conf as noise_graph_join_conf
import graph_build.graph_noise_join.noise_graph_join as noise_graph_join
import graph_build.graph_noise_join.noise_graph_update as noise_graph_update
import graph_build.common.utils as utils
import logging
import logging.config
from graph_build.common.logging_conf import logging_conf
logging.config.dictConfig(logging_conf)


log = logging.getLogger('graph_build.main')


selected_script = utils.read_user_selection(
    'Which script?',
    [
        'otp_graph_import',
        'noise_data_preprocessing',
        'noise_graph_join',
        'graph_noise_update',
        'fetch_land_cover_data',
        'green_view_join',
        'green_view_land_cover_analysis',
        'graph_export'
    ]
)

if selected_script:
    log.info(f'Running script: {selected_script}')

if selected_script == 'otp_graph_import':
    if utils.confirm_config(otp_graph_import_conf):
        otp_graph_import.main(otp_graph_import_conf)

if selected_script == 'noise_data_preprocessing':
    if utils.confirm_config(noise_data_conf):
        noise_data_preprocessing.main(noise_data_conf)

if selected_script == 'noise_graph_join':
    if utils.confirm_config(noise_graph_join_conf):
        noise_graph_join.main(noise_graph_join_conf)

if selected_script == 'graph_noise_update':
    if utils.confirm_config(noise_graph_join_conf):
        noise_graph_update.main(noise_graph_join_conf)

if selected_script == 'fetch_land_cover_data':
    if utils.confirm_config(green_viw_join_conf):
        fetch_land_cover.main(green_viw_join_conf)

if selected_script == 'green_view_join':
    if utils.confirm_config(green_viw_join_conf):
        graph_green_view_join.main(green_viw_join_conf)

if selected_script == 'green_view_land_cover_analysis':
    if utils.confirm_config(green_viw_join_conf):
        gvi_lc_analysis.main(green_viw_join_conf)

if selected_script == 'graph_export':
    if utils.confirm_config(graph_export_conf):
        graph_export.graph_export(graph_export_conf)
