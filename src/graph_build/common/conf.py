
def setup_logging():
    import logging
    import logging.config
    from graph_build.common.logging_conf import logging_conf
    logging.config.dictConfig(logging_conf)

setup_logging()


bike_walk_time_ratio = 4.5
