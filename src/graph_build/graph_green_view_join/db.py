from typing import Callable, List, Union
import graph_build.graph_green_view_join.env as env
import pandas as pd
from geopandas import GeoDataFrame
from sqlalchemy import create_engine, inspect, text
from functools import partial


def __get_conn_string(db: str) -> str:
    return f'postgresql://{env.db_user}:{env.db_pass}@{env.db_host}:{env.db_port}/{db}'


def __write_to_postgis(
    log,
    sql_engine,
    gdf: GeoDataFrame,
    table_name: str,
    if_exists: str = 'replace',
    index: bool = False
) -> None:

    log.info('Writing GeoDataFrame to PostGIS:')
    log.info(f'{gdf.head()}')

    gdf.to_postgis(
        table_name,
        sql_engine,
        if_exists=if_exists,
        chunksize=50000,
        index=index
    )

    __execute_sql(log, sql_engine, f'''
        ALTER TABLE {table_name} RENAME COLUMN geometry TO geom;
        ALTER INDEX idx_{table_name}_geometry
            RENAME TO idx_{table_name}_geom;
    ''')


def get_db_writer(
    log,
    b_inspect: bool = False,
    inspect_table: str = None,
    db: str = 'gp'
) -> Callable[[GeoDataFrame, str, str, bool], None]:

    engine = create_engine(__get_conn_string(db))

    if b_inspect and inspect_table:
        inspector = inspect(engine)
        print(inspector.get_columns(inspect_table))

    return partial(__write_to_postgis, log, engine)


def __execute_sql(
    log,
    engine,
    query_str: str,
    logging: bool = False,
    returns: bool = False,
    dry_run: bool = False
) -> Union[None, list]:

    queries = query_str.split(';') if ';' in query_str else [query_str]
    queries = [query.strip() for query in queries if len(query.strip()) > 0]

    all_rows = []
    with engine.connect() as conn:
        for query in queries:
            log.info(f'{"Executing SQL:" if not dry_run else "Skipping SQL:"}\n{query}')
            if dry_run:
                continue
            result = conn.execute(text(query))
            if result.cursor and (logging or returns):
                rows = result.fetchall()
                if logging:
                    log.info('Result rows:')
                    for row in rows:
                        log.info(f'{row}')
                if returns:
                    all_rows += rows
            if not dry_run:
                log.info('SQL execution finished')

    if returns:
        return all_rows


def get_sql_executor(
    log,
    db: str = 'gp'
) -> Callable[
        [
        str, Union[bool, None], Union[bool, None], Union[bool, None]],
        Union[list, None]
        ]:

    engine = create_engine(__get_conn_string(db))
    return partial(__execute_sql, log, engine)


def get_db_table_names(
    execute_sql: Callable[[str], list]
) -> List[str]:

    db_tables = execute_sql(
        '''
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
        ''',
        returns=True
    )
    return [r for r, in db_tables]


def read_db_table_to_df(table: str, db='gp') -> pd.DataFrame:
    engine = create_engine(__get_conn_string(db))
    with engine.connect() as conn:
        return pd.read_sql(f'SELECT * FROM {table}', conn)
