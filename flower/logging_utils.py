import logging


class CeleryOneLineExceptionFormatter(logging.Formatter):
    """
    Special logging formatter mostly for Celery, to make exceptions on 1 line.
    """
    def formatException(self, exc_info):
        """
        Format an exception so that it prints on a single line.
        """
        result = super(CeleryOneLineExceptionFormatter, self).formatException(exc_info)
        return repr(result)  # or format into one line however you want to

    def format(self, record):
        s = super(CeleryOneLineExceptionFormatter, self).format(record)
        if record.exc_text or record.levelno >= logging.ERROR:
            s = s.replace('\n', '') + '|'
        return s
