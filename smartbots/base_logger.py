import logging
from os.path import join
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
path_log = join(BASE_DIR, 'temp', 'data.log')
logging.basicConfig(filename=path_log, filemode='w', format='%(asctime)s - %(filename)s - %(funcName)s - %(levelname)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')
logger = logging.getLogger(__name__)