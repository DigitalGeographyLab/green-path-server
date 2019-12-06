import time
from datetime import datetime

class Logger:
    """A somewhat generic logger class that can be used to write log messages to gunicorn, log file and/or console/terminal output. 

    Attributes:
        app_logger (optional): A logger object of the Flask/Gunicorn application.
        b_printing (optional): A boolean variable indicating whether logs should be printed to standard console/terminal output.
        log_file (optional): A name for a log file (in the root of the application) where log messages will be written.
    """

    def __init__(self, app_logger = None, b_printing: bool = False, log_file: str = None):
        self.app_logger = app_logger
        self.b_printing = b_printing
        self.log_file = log_file

    def print_log(self, text, level):
        """Prints a log message to console/terminal and/or to a log file (if specified at init). The log message is prefixed
        with current time and the given logging level.
        """
        log_prefix = datetime.utcnow().strftime('%y/%m/%d %H:%M:%S') + ' ['+ level +'] '
        if (self.b_printing == True):
            print(log_prefix + text)
        if (self.log_file is not None):
            with open(self.log_file, 'a') as the_file:
                the_file.write(log_prefix + text + '\n')

    def debug(self, text: str):
        if (self.b_printing == True or self.log_file is not None):
            self.print_log(text, 'DEBUG')
        if (self.app_logger is not None):
            self.app_logger.debug(text)

    def info(self, text: str):
        if (self.b_printing == True or self.log_file is not None):
            self.print_log(text, 'INFO')
        if (self.app_logger is not None):
            self.app_logger.info(text)

    def warning(self, text: str):
        if (self.b_printing == True or self.log_file is not None):
            self.print_log(text, 'WARNING')
        if (self.app_logger is not None):
            self.app_logger.warning(text)

    def error(self, text: str):
        if (self.b_printing == True or self.log_file is not None):
            self.print_log(text, 'ERROR')
        if (self.app_logger is not None):
            self.app_logger.error(text)

    def critical(self, text: str):
        if (self.b_printing == True or self.log_file is not None):
            self.print_log(text, 'CRITICAL')
        if (self.app_logger is not None):
            self.app_logger.critical(text)

    def duration(self, time1, text, round_n: int = 3, unit: str = 's', log_level: str = 'debug') -> None:
        """Creates a log message that contains the duration between the current time and a given time [time1].
        """
        log_str = ''
        if (unit == 's'):
            time_elapsed = round(time.time() - time1, round_n)
            log_str = '--- %s s --- %s' % (time_elapsed, text)
        elif (unit == 'ms'):
            time_elapsed = round((time.time() - time1) * 1000)
            log_str = '--- %s ms --- %s' % (time_elapsed, text)

        if (self.b_printing == True or self.log_file is not None):
            level = 'DEBUG' if (log_level == 'debug') else 'INFO'
            self.print_log(log_str, level)
        elif (log_level == 'debug'):
            self.debug(log_str)
        elif (log_level == 'info'):
            self.info(log_str)
        elif (log_level == 'warn'):
            self.warning
