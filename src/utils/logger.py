import time
from datetime import datetime

class Logger:

    def __init__(self, app_logger = None, b_printing: bool = False, log_file: str = None, log_level: str = None):
        self.app_logger = app_logger
        self.b_printing = b_printing
        self.log_file = log_file

    def print_log(self, text, level):
        log_prefix = datetime.utcnow().strftime('%y/%m/%d %H:%M:%S') + ' ['+ level +'] '
        print (log_prefix + text)
        if (self.log_file is not None):
            with open(self.log_file, 'a') as the_file:
                the_file.write(log_prefix + text + '\n')

    def debug(self, text: str):
        if (self.b_printing == True):
            self.print_log(text, 'DEBUG')
        elif (self.app_logger is not None):
            self.app_logger.debug(text)

    def info(self, text: str):
        if (self.b_printing == True):
            self.print_log(text, 'INFO')
        elif (self.app_logger is not None):
            self.app_logger.info(text)

    def warning(self, text: str):
        if (self.b_printing == True):
            self.print_log(text, 'WARNING')
        elif (self.app_logger is not None):
            self.app_logger.warning(text)

    def error(self, text: str):
        if (self.b_printing == True):
            self.print_log(text, 'ERROR')
        elif (self.app_logger is not None):
            self.app_logger.error(text)

    def critical(self, text: str):
        if (self.b_printing == True):
            self.print_log(text, 'CRITICAL')
        elif (self.app_logger is not None):
            self.app_logger.critical(text)

    def duration(self, time1, text, round_n: int = 3, unit: str = 's', log_level: str = 'debug') -> None:
        log_str = ''
        if unit == 's':
            time_elapsed = round(time.time() - time1, round_n)
            log_str = '--- %s s --- %s' % (time_elapsed, text)
        elif unit == 'ms':
            time_elapsed = round((time.time() - time1) * 1000)
            log_str = '--- %s ms --- %s' % (time_elapsed, text)

        if (self.b_printing == True):
            level = 'DEBUG' if log_level == 'debug' else 'INFO' if log_level == 'info' else 'WARN'
            self.print_log(log_str, level)
        elif (log_level == 'debug'):
            self.debug(log_str)
        elif (log_level == 'info'):
            self.info(log_str)
        elif (log_level == 'warn'):
            self.warning
