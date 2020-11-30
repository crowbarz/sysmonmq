"""SysMonMQ constants."""

from inotify_simple import flags as in_flags
from inotify_simple import masks as in_masks

APP_NAME = "sysmonmq"
APP_VERSION = "0.0.1"

## Application defaults
DEF_THREAD_MAX_WORKERS = 10
DEF_THREAD_MAIN = "Main"
DEF_THREAD = ""
DEF_THREAD_POOL_PREFIX = "Command"
DEF_COMMAND_TIMEOUT = 10
DEF_REFRESH_INTERVAL = 300
DEF_DISCOVERY_ENTITY_TYPE = "sensor"
DEF_DISCOVERY_ICON = "mdi:radiobox-marked"

DEF_INOTIFY_FLAGS_UPDATE = in_flags.MODIFY
DEF_INOTIFY_FLAGS_RESTART = (
    in_flags.ATTRIB
    | in_masks.MOVE
    | in_flags.CREATE
    | in_flags.DELETE
    | in_flags.DELETE_SELF
    | in_flags.MOVE_SELF
)
DEF_INOTIFY_FLAGS = (
    in_flags.ATTRIB
    | in_masks.MOVE
    | in_flags.DELETE_SELF
    | in_flags.MOVE_SELF
    | in_flags.MODIFY
)

DEF_INOTIFY_FLAGS_PARENT = (
    in_flags.CREATE | in_flags.DELETE | in_flags.DELETE_SELF | in_flags.MOVE_SELF
)

## Config file option defaults
DEF_DEBUG = 0
DEF_CONFIG_FILE = "/etc/sysmonmq.yaml"

DEF_WATCHER_TRIGGER_DELAY = 2
DEF_MQTT_RECONNECT_DELAY_MIN = 1
DEF_MQTT_RECONNECT_DELAY_MAX = 120
DEF_MQTT_QOS = 1
DEF_MQTT_SUBSCRIBE_QOS = 2
DEF_MQTT_RETAIN = False
DEF_MQTT_DISCOVERY_RETAIN = False
DEF_MQTT_DISCOVERY_UPDATE_DELAY = 2