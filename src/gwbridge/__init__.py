import os

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
METADATA_FILE = ".deploy/metadata.json"
CONFIG_FILE = ".deploy/config.json"
PROGRAM_NAME = __name__

from gwbridge.logger import configure_logger  # noqa: E402

program_log = configure_logger()
