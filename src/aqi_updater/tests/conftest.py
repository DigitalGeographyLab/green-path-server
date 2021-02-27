import os
import glob
from shutil import copyfile


test_data_source = r'aqi_updater/tests/test_data_source/'
test_data_dir = r'aqi_updater/tests/test_data/'
aqi_updates_dir = r'aqi_updater/tests/test_aqi_updates/'


def pytest_sessionstart(session):

    temp_test_aqi_updates = [
        'aqi_2020-10-10T08.csv',
        'aqi_map.json'
    ]

    for fn in temp_test_aqi_updates:
        try:
            os.remove(fr'{aqi_updates_dir}{fn}')
            print(f'Removed test data: {aqi_updates_dir}{fn}')
        except Exception as e:
            print(e)
            continue

    files = glob.glob(fr'{test_data_dir}*')
    for f in files:
        os.remove(f)
        print(f'Removed test data: {f}')

    fns = os.listdir(test_data_source)
    files = glob.glob(fr'{test_data_source}*')
    for fp, fn in zip(files, fns):
        copyfile(fp, rf'{test_data_dir}{fn}')
        print(f'Copied test data to {test_data_dir}: {fn}')
