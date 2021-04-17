import os
from glob import glob
import traceback
import logging
import logging.config
from aqi_updater.logging_conf import logging_conf
logging.config.dictConfig(logging_conf)


log = logging.getLogger('configuration')
path = r'aqi_updater/'


# load env variables from either Docker secrets or .env file
try:
    found_secrets = False
    for var in glob('/run/secrets/*'):
        k = var.split('/')[-1]
        v = open(var).read().rstrip('\n')
        os.environ[k] = v
        log.info(f'Read docker secret: {k} (len: {len(v)})')
        found_secrets = True
except Exception:
    traceback.print_exc()
    pass
if not found_secrets:
    log.warning('No docker secrets found')

try:
    fh = open(fr'{path}.env', 'r')
    lines = fh.read().splitlines()
    for line in lines:
        line.rstrip('\n')
        row = line.partition('=')
        os.environ[row[0]] = row[2]
    fh.close()
    log.info(f'Read {len(lines)} variables from .env')
except Exception:
    log.warning('No .env file found')
    pass
