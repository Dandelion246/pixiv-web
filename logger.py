import logging

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger('pixiv')
logger.setLevel(logging.INFO)

# file_handler = logging.FileHandler('../kemono/src/log.txt')
# formatter = logging.Formatter('[%(asctime)s] line:%(lineno)d - %(levelname)s: %(message)s')
# file_handler.setFormatter(formatter)

stream_format = logging.Formatter('[%(asctime)s] %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(stream_format)

# logger.addHandler(file_handler)
logger.addHandler(stream_handler)
