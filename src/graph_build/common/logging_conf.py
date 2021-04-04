logging_conf = {
    'version': 1,
    'disable_existing_loggers': False,
        'formatters': {
            'standard': { 
                'format': '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
    },
    'handlers': {       
        'default': { 
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        },
        'my_logger': { 
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
