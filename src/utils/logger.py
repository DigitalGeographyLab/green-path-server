
class Logger:

    def __init__(self, app_logger = None, b_printing: bool = False, log_file: str = None):
        self.app_logger = app_logger
        self.b_printing = b_printing
        self.log_file = log_file

    def debug(self, text: str):
        if (self.app_logger is not None):
            self.app_logger.debug(text)

    def info(self, text: str):
        if (self.app_logger is not None):
            self.app_logger.info(text)

    def warning(self, text: str):
        if (self.app_logger is not None):
            self.app_logger.warning(text)

    def error(self, text: str):
        if (self.app_logger is not None):
            self.app_logger.error(text)

    def critical(self, text: str):
        if (self.app_logger is not None):
            self.app_logger.critical(text)
