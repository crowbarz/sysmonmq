"""SysMonMQ debugging functions."""

import sys
import logging

from .const import APP_NAME
from .config import OPT_DEBUG

_LOGGER = logging.getLogger(APP_NAME)

## Debug levels:

## 1: info (default)
## 2: info + mqtt
## 3:
## 4: sensors, services, actions
## 5: command, watcher
## 6: event loop
## 7: mqtt
## 8: options, sensor setup, event loop
## 9: utils

## Module globals
debug_level = 0
log_level = logging.WARNING


def configure_debug(opts, config):
    """Configure debugging."""
    global debug_level, log_level

    if opts.get(OPT_DEBUG):
        debug_level = opts[OPT_DEBUG]
        if debug_level <= -1:
            log_level = logging.ERROR
        elif debug_level >= 4:
            log_level = logging.DEBUG
            config.mqtt_debug = True
        elif debug_level >= 3:
            log_level = logging.DEBUG
        elif debug_level >= 1:
            log_level = logging.INFO
            config.mqtt_debug = True
        else:
            log_level = logging.INFO

    if sys.version_info >= (3, 8):
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s[%(threadName)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,
        )
    else:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s[%(threadName)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    _LOGGER.setLevel(log_level)
    _LOGGER.info("setting debug level to %s", debug_level)


def is_debug_level(level):
    """Check debug level is at or above level."""
    return True if debug_level >= level else False
