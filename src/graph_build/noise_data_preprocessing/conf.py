from dataclasses import dataclass


@dataclass(frozen=True)
class NoiseDataPreprocessingConf:
    hel_wfs_download: bool
    process_hel: bool
    process_espoo: bool
    process_syke: bool
    mask_poly_file: str
    noise_layer_info_csv: str
    noise_data_hel_gpkg: str
    processed_data_gpkg: str
    wfs_hki_url: str


conf = NoiseDataPreprocessingConf(
    hel_wfs_download = False,
    process_hel = True,
    process_espoo = True,
    process_syke = True,
    mask_poly_file = 'extent_data/HMA.geojson',
    noise_layer_info_csv = 'noise_data/noise_layers.csv',
    noise_data_hel_gpkg = 'noise_data/noise_data_raw.gpkg',
    processed_data_gpkg = 'noise_data/noise_data_processed.gpkg',
    wfs_hki_url = 'https://kartta.hel.fi/ws/geoserver/avoindata/wfs',
)
