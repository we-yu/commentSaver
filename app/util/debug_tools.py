import os

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.normpath(os.path.join(CURRENT_FILE_DIR, '../config/conf.txt'))

def get_debug_value_from_config(file_path=CONFIG_PATH):
    with open(file_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if "DEBUG" in line:
                return line.split('=')[1].strip().lower() == 'true'
    return False

DEBUG = get_debug_value_from_config()

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)
