
def setup_logging():
    import logging
    import logging.config
    from graph_builder.common.logging_conf import logging_conf
    logging.config.dictConfig(logging_conf)

setup_logging()
