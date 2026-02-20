import logging

def setup_logger(name: str):
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(name)
