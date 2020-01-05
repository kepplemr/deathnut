import logging
import sys

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

try:
    import sofrito
    root_logger.handlers = [sofrito.stackdriver_logging.stackdriver_handler('deathnut')]
except ImportError:
    root_logger.handlers = [logging.StreamHandler(sys.stdout)]
except:
    root_logger.handlers = [sofrito.stackdriver_logging.stackdriver_handler()]

# logging.getLogger().setLevel(logging.INFO)
# logger = logging.getLogger(__name__)
# formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# handler = logging.StreamHandler(sys.stdout)
# handler.setFormatter(formatter)
# handler.setLevel(logging.INFO)
# logger.addHandler(handler)

def get_deathnut_logger(name):
    return logging.getLogger(name)