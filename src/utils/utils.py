from typing import List, Set, Dict, Tuple
import pandas as pd
import geopandas as gpd
import time
from time import sleep
import sys

def print_progress(idx: int, count: int, percentages: bool = False) -> None:
    if (percentages):
        sys.stdout.write('\r{0} %'.format(int(round(((idx/count)*100)))))
    else:
        sys.stdout.write('\r')
        sys.stdout.write(str(idx+1)+'/'+str(count)+' ')
    sys.stdout.flush()
    sleep(0.02)

def get_list_chunks(l: list, n: int) -> List[list]:
    """Transforms a list to a list of lists each having n or fewer objects in them.
    
    Args:
        l: A list.
        n: A number indicating how many objects should be in each list.
    Returns:
        A list of lists.
    """
    chunks = []
    for i in range(0, len(l), n):
        chunks.append(l[i:i + n])
    return chunks

def print_duration(time1, text, round_n: int = 3) -> None:
    time_elapsed = round(time.time() - time1, round_n)
    print('--- %s s --- %s' % (time_elapsed, text))
