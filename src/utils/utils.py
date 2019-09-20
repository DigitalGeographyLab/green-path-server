import pandas as pd
import geopandas as gpd
import time
from time import sleep
import sys

grid_gdf = gpd.read_file('data/extents_grids.gpkg', layer='HSY_vaesto_250m_2017')

def get_grid():
    return grid_gdf

def print_progress(idx, count, percentages=False):
    if (percentages):
        sys.stdout.write('\r{0} %'.format(int(round(((idx/count)*100)))))
    else:
        sys.stdout.write('\r')
        sys.stdout.write(str(idx+1)+'/'+str(count)+' ')
    sys.stdout.flush()
    sleep(0.02)

def get_list_chunks(l, n):
    chunks = []
    for i in range(0, len(l), n):
        chunks.append(l[i:i + n])
    return chunks

def print_duration(time1, text, round_n=3):
    time_elapsed = round(time.time() - time1, round_n)
    print('--- %s s --- %s' % (time_elapsed, text))
