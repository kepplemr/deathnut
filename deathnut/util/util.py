import logging
import sofrito


root_logger = logging.getLogger()
root_logger.handlers = [sofrito.stackdriver_logging.stackdriver_handler('deathnut')]

# logging.getLogger().setLevel(logging.INFO)
# logger = logging.getLogger(__name__)
# formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# handler = logging.StreamHandler(sys.stdout)
# handler.setFormatter(formatter)
# handler.setLevel(logging.INFO)
# logger.addHandler(handler)

def get_deathnut_logger(name):
    return logging.getLogger(__name__)

class DeathnutException(Exception):
   """Custom Exception to make ownership clear"""
   pass

