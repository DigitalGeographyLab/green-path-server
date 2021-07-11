import os

try:
    env_file = open('graph_build/graph_green_view_join/.env', 'r')
    lines = env_file.read().splitlines()
    for line in lines:
        line.rstrip('\n')
        row = line.partition('=')
        key, val = (row[0], row[2])
        os.environ[key] = val
    env_file.close()
except Exception:
    print('Could not read env vars')
    pass

db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', 5432)
db_user = os.getenv('DB_USER')
db_pass = os.getenv('DB_PASS')
