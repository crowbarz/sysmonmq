"""SysMonMQ config options."""

from .const import (
    DEF_DISCOVERY_ICON,
    DEF_MQTT_DISCOVERY_RETAIN,
    DEF_MQTT_SUBSCRIBE_QOS,
    DEF_REFRESH_INTERVAL,
    DEF_COMMAND_TIMEOUT,
    DEF_DEBUG,
    DEF_MQTT_RECONNECT_DELAY_MIN,
    DEF_MQTT_RECONNECT_DELAY_MAX,
    DEF_MQTT_QOS,
    DEF_MQTT_RETAIN,
    DEF_WATCHER_TRIGGER_DELAY,
)

DEF_CONFIG_FILE = "/etc/sysmonmq.yaml"

## Configuration options
OPT_DEBUG = "debug"
OPT_DUMP_CONFIG_CLI = "dump-config"  # command line version (note dash)
OPT_DUMP_CONFIG = "dump_config"
OPT_CONFIG_FILE = "config"
OPT_REFRESH_INTERVAL = "refresh_interval"

OPT_MQTT = "mqtt"
OPT_HOST = "host"
OPT_PORT = "port"
OPT_CLIENT_ID = "client_id"
OPT_CLEAN_SESSION = "clean_session"
OPT_KEEPALIVE = "keepalive"
OPT_RECONNECT_DELAY_MIN = "reconnect_delay_min"
OPT_RECONNECT_DELAY_MAX = "reconnect_delay_max"
OPT_USERNAME = "username"
OPT_PASSWORD = "password"
OPT_ENABLE_SSL = "enable_ssl"

OPT_SSL = "ssl"
OPT_CAFILE = "cafile"
OPT_CERTFILE = "certfile"
OPT_KEYFILE = "keyfile"
OPT_KEYFILE_PASSWORD = "keyfile_password"
OPT_TLS_INSECURE = "tls_insecure"

OPT_CLIENT = "client"
OPT_BIRTH = "birth"
OPT_CLOSE = "close"
OPT_WILL = "will"
OPT_TOPIC = "topic"
OPT_QOS = "qos"
OPT_RETAIN = "retain"
OPT_PAYLOAD = "payload"

OPT_MQTT_ERROR = "mqtt_error"
OPT_MQTT_OUTPUT = "mqtt_output"
OPT_MQTT_TOPIC = "mqtt_topic"
OPT_MQTT_QOS = "mqtt_qos"
OPT_MQTT_RETAIN = "mqtt_retain"

OPT_DISCOVERY = "discovery"
OPT_STATUS = "status"
OPT_PAYLOAD_AVAILABLE = "payload_available"

OPT_MQTT_PAYLOAD = "mqtt_payload"
OPT_MQTT_OUTPUT_ON_ERROR = "output_on_error"

OPT_MQTT_PREFIX = "mqtt_prefix"
OPT_MQTT_PREFIX_HOST = "mqtt_prefix_host"

OPT_CPU_LOAD_AVERAGE = "cpu_load_average"
OPT_CPU_LOAD_FILE = "load_file"
OPT_CPU_LOAD_FORMAT = "load_format"
OPT_MEMORY_USAGE = "memory_usage"
OPT_MEMORY_USAGE_FILE = "usage_file"
OPT_DISK_USAGE = "disk_usage"
OPT_DISK_USAGE_COMMAND = "usage_command"
OPT_CPU_TEMP = "cpu_temperature"
OPT_TEMP_SENSOR_FILE = "temp_sensor_file"

OPT_SYSTEM_SENSORS = "system_sensors"
OPT_COMMAND_SENSORS = "command_sensors"
OPT_MONITORED_SERVICES = "monitored_services"
OPT_MONITORED_CONTAINERS = "monitored_containers"
OPT_MONITORED_COMMANDS = "monitored_commands"
OPT_ACTIONS_LIST = "actions_list"
OPT_SERVICES = "services"
OPT_CONTAINERS = "containers"
OPT_COMMANDS = "commands"
OPT_ACTIONS = "actions"
OPT_WATCHERS = "watchers"
OPT_FILES = "files"
OPT_KEYWORDS = "keywords"
OPT_IGNORE_RC = "ignore_rc"
OPT_TRIGGER_DELAY = "trigger_delay"
OPT_RESTART_DELAY = "restart_delay"
OPT_JSON_PAYLOAD = "json_payload"
OPT_ATTRIBUTES = "attributes"

OPT_NAME = "name"
OPT_DISPLAY_NAME = "display_name"
OPT_COMMAND = "command"
OPT_STATUS_COMMAND = "status_command"
OPT_MQTT_TOPIC_PREFIX = "mqtt_topic_prefix"
OPT_MQTT_TOPIC_SUFFIX = "mqtt_topic_suffix"
OPT_COMMAND_TIMEOUT = "command_timeout"
OPT_APPEND_PAYLOAD = "append_payload"
OPT_FORMAT_COMMAND = "format_command"
OPT_PAYLOAD_MATCH = "payload_match"

OPT_ENTITY_TYPE = "entity_type"
OPT_CONFIG_REMOVE = "config_remove"
OPT_CONFIG_INHERIT = "config_inherit"

## Configuration options hierarchy and defaults
TOP_OPTS_DEF = {
    OPT_DEBUG: DEF_DEBUG,
    OPT_DUMP_CONFIG: False,
    OPT_CONFIG_FILE: DEF_CONFIG_FILE,
    OPT_REFRESH_INTERVAL: DEF_REFRESH_INTERVAL,
    OPT_COMMAND_TIMEOUT: DEF_COMMAND_TIMEOUT,
    OPT_MQTT_PREFIX: "sysmonmq",
    OPT_MQTT_PREFIX_HOST: False,
    OPT_MQTT_OUTPUT: {
        OPT_MQTT_TOPIC_PREFIX: "output",
        OPT_MQTT_TOPIC_SUFFIX: None,
        OPT_MQTT_QOS: DEF_MQTT_QOS,
        OPT_MQTT_RETAIN: DEF_MQTT_RETAIN,
        OPT_IGNORE_RC: False,
    },
    OPT_MQTT_ERROR: {
        OPT_MQTT_TOPIC_PREFIX: "error",
        OPT_MQTT_TOPIC_SUFFIX: None,
        OPT_MQTT_QOS: DEF_MQTT_QOS,
        OPT_MQTT_RETAIN: DEF_MQTT_RETAIN,
        OPT_MQTT_OUTPUT_ON_ERROR: False,
    },
}
TOP_OPTS_SUB = {
    OPT_MQTT: None,
    OPT_SYSTEM_SENSORS: None,
    OPT_MONITORED_SERVICES: None,
    OPT_MONITORED_CONTAINERS: None,
    OPT_MONITORED_COMMANDS: None,
    OPT_ACTIONS_LIST: None,
}
TOP_OPTS_ALL = {**TOP_OPTS_DEF, **TOP_OPTS_SUB}.keys()
TOP_OPTS_SUB_ALL = TOP_OPTS_SUB.keys()

## MQTT client options
MQTT_DISCOVERY_OPTS_DEF = {
    OPT_TOPIC: "homeassistant",
    OPT_QOS: DEF_MQTT_QOS,
    OPT_RETAIN: DEF_MQTT_DISCOVERY_RETAIN,  # discovery default
}
MQTT_DISCOVERY_OPTS_ALL = MQTT_DISCOVERY_OPTS_DEF.keys()

MQTT_STATUS_OPTS_DEF = {
    OPT_TOPIC: "homeassistant/status",
    OPT_PAYLOAD_AVAILABLE: "online",
    OPT_QOS: DEF_MQTT_SUBSCRIBE_QOS,  # subscribe default
}
MQTT_STATUS_OPTS_ALL = MQTT_STATUS_OPTS_DEF.keys()

MQTT_OPTS_DEF = {
    OPT_DEBUG: False,
    OPT_HOST: "mqtt",
    OPT_PORT: 1883,
    OPT_CLIENT_ID: None,
    OPT_CLEAN_SESSION: True,
    OPT_KEEPALIVE: 60,
    OPT_RECONNECT_DELAY_MIN: DEF_MQTT_RECONNECT_DELAY_MIN,
    OPT_RECONNECT_DELAY_MAX: DEF_MQTT_RECONNECT_DELAY_MAX,
    OPT_USERNAME: None,
    OPT_PASSWORD: None,
    OPT_ENABLE_SSL: False,
    OPT_SSL: {
        OPT_CAFILE: None,
        OPT_CERTFILE: None,
        OPT_KEYFILE: None,
        OPT_KEYFILE_PASSWORD: None,
        OPT_TLS_INSECURE: False,
    },
    OPT_CLIENT: {
        OPT_MQTT_PREFIX: None,  # inherit
        OPT_REFRESH_INTERVAL: None,  # inherit
        OPT_TOPIC: None,
        OPT_QOS: DEF_MQTT_QOS,
        OPT_RETAIN: True,
        OPT_BIRTH: {
            OPT_MQTT_PREFIX: None,  # inherit
            OPT_TOPIC: None,  # inherit
            OPT_PAYLOAD: "online",
            OPT_REFRESH_INTERVAL: None,  # inherit
            OPT_QOS: None,  # inherit
            OPT_RETAIN: None,  # inherit
        },
        OPT_CLOSE: {
            OPT_MQTT_PREFIX: None,  # inherit
            OPT_TOPIC: None,  # inherit
            OPT_PAYLOAD: "offline",
            OPT_QOS: None,  # inherit
            OPT_RETAIN: None,  # inherit
        },
        OPT_WILL: {
            OPT_MQTT_PREFIX: None,  # inherit
            OPT_TOPIC: None,  # inherit
            OPT_PAYLOAD: "offline",
            OPT_QOS: None,  # inherit
            OPT_RETAIN: None,  # inherit
        },
    },
    OPT_STATUS: MQTT_STATUS_OPTS_DEF,
}
MQTT_OPTS_SUB = {
    OPT_DISCOVERY: None,
}
CLIENT_OPTS_SUB = {
    OPT_MQTT_OUTPUT: None,  # inherit
    OPT_MQTT_ERROR: None,  # inherit
}

MQTT_OPTS_ALL = {**MQTT_OPTS_DEF, **MQTT_OPTS_SUB}.keys()
SSL_OPTS_ALL = MQTT_OPTS_DEF[OPT_SSL].keys()
CLIENT_OPTS_ALL = {**MQTT_OPTS_DEF[OPT_CLIENT], **CLIENT_OPTS_SUB}.keys()
BIRTH_OPTS_ALL = MQTT_OPTS_DEF[OPT_CLIENT][OPT_BIRTH].keys()
CLOSE_OPTS_ALL = MQTT_OPTS_DEF[OPT_CLIENT][OPT_CLOSE].keys()
WILL_OPTS_ALL = MQTT_OPTS_DEF[OPT_CLIENT][OPT_WILL].keys()

## MQTT error and output message
MQTT_OUTPUT_OPTS_DEF = {
    OPT_MQTT_TOPIC_PREFIX: None,  # inherit
    OPT_MQTT_TOPIC_SUFFIX: None,  # inherit
    OPT_MQTT_QOS: None,  # inherit
    OPT_MQTT_RETAIN: None,  # inherit
    OPT_IGNORE_RC: None,  # inherit
}
MQTT_OUTPUT_OPTS_ALL = MQTT_OUTPUT_OPTS_DEF.keys()

MQTT_ERROR_OPTS_DEF = {
    OPT_MQTT_TOPIC_PREFIX: None,  # inherit
    OPT_MQTT_TOPIC_SUFFIX: None,  # inherit
    OPT_MQTT_QOS: None,  # inherit
    OPT_MQTT_RETAIN: None,  # inherit
    OPT_MQTT_OUTPUT_ON_ERROR: None,  # inherit
}
MQTT_ERROR_OPTS_ALL = MQTT_ERROR_OPTS_DEF.keys()

## Sensor options
SYSTEM_SENSORS_OPTS_DEF = {
    OPT_MQTT_PREFIX: None,  # inherit
    OPT_MQTT_TOPIC_PREFIX: "system",
    OPT_MQTT_QOS: DEF_MQTT_QOS,
    OPT_MQTT_RETAIN: DEF_MQTT_RETAIN,
    OPT_REFRESH_INTERVAL: None,  # inherit
    OPT_COMMAND_TIMEOUT: None,  # inherit
}
SYSTEM_SENSORS_OPTS_SUB = {
    OPT_CPU_LOAD_AVERAGE: None,
    OPT_MEMORY_USAGE: None,
    OPT_DISK_USAGE: None,
    OPT_CPU_TEMP: None,
    OPT_MQTT_OUTPUT: None,
    OPT_MQTT_ERROR: None,
}
SYSTEM_SENSORS_OPTS_ALL = {**SYSTEM_SENSORS_OPTS_DEF, **SYSTEM_SENSORS_OPTS_SUB}.keys()
SYSTEM_SENSORS_OPTS_SUB_ALL = SYSTEM_SENSORS_OPTS_SUB.keys()

SYSTEM_SENSOR_OPTS_DEF = {
    OPT_MQTT_PREFIX: None,  # inherit
    OPT_MQTT_TOPIC_PREFIX: None,  # inherit
    OPT_REFRESH_INTERVAL: None,  # inherit
    OPT_MQTT_QOS: None,  # inherit
    OPT_MQTT_RETAIN: None,  # inherit
}
SYSTEM_SENSOR_OPTS_SUB = {
    OPT_MQTT_OUTPUT: None,
    OPT_MQTT_ERROR: None,
}

CPU_LOAD_OPTS_DEF = {
    **SYSTEM_SENSOR_OPTS_DEF,
    OPT_CPU_LOAD_FILE: "/proc/loadavg",
    OPT_CPU_LOAD_FORMAT: "%.2f",
    OPT_MQTT_TOPIC: "load_average",
}
CPU_LOAD_OPTS_ALL = {**CPU_LOAD_OPTS_DEF, **SYSTEM_SENSOR_OPTS_SUB}.keys()

MEMORY_USAGE_OPTS_DEF = {
    **SYSTEM_SENSOR_OPTS_DEF,
    OPT_MEMORY_USAGE_FILE: "/proc/meminfo",
    OPT_MQTT_TOPIC: "memory_usage",
}
MEMORY_USAGE_OPTS_ALL = {**MEMORY_USAGE_OPTS_DEF, **SYSTEM_SENSOR_OPTS_SUB}.keys()

DISK_USAGE_OPTS_DEF = {
    **SYSTEM_SENSOR_OPTS_DEF,
    OPT_DISK_USAGE_COMMAND: "df -m -l -x tmpfs -x devtmpfs",
    OPT_COMMAND_TIMEOUT: None,  # inherit
    OPT_MQTT_TOPIC: "disk_usage",
}
DISK_USAGE_OPTS_ALL = {**DISK_USAGE_OPTS_DEF, **SYSTEM_SENSOR_OPTS_SUB}.keys()

TEMP_OPTS_DEF = {
    **SYSTEM_SENSOR_OPTS_DEF,
    OPT_TEMP_SENSOR_FILE: "/sys/class/thermal/thermal_zone0/temp",
    OPT_MQTT_TOPIC: "temperature",
}
TEMP_OPTS_ALL = {**TEMP_OPTS_DEF, **SYSTEM_SENSOR_OPTS_SUB}.keys()

## Watchers options
WATCHERS_OPTS_DEF = {
    OPT_FILES: None,
    OPT_COMMANDS: None,
    OPT_KEYWORDS: None,
    OPT_TRIGGER_DELAY: DEF_WATCHER_TRIGGER_DELAY,
    OPT_RESTART_DELAY: DEF_COMMAND_TIMEOUT,
}
WATCHERS_OPTS_ALL = WATCHERS_OPTS_DEF.keys()

## Command Sensors options
COMMAND_SENSORS_OPTS_DEF = {
    OPT_COMMAND_TIMEOUT: None,  # inherit
    OPT_MQTT_PREFIX: None,  # inherit
    OPT_MQTT_QOS: DEF_MQTT_QOS,
    OPT_MQTT_RETAIN: DEF_MQTT_RETAIN,
    OPT_REFRESH_INTERVAL: None,  # inherit
    OPT_IGNORE_RC: True,
    OPT_FORMAT_COMMAND: False,
    OPT_ATTRIBUTES: None,
    # OPT_JSON_PAYLOAD: True, ## defined in monitor_*
    # OPT_DISCOVERY: {}, ## defined in monitored_*
}

COMMAND_SENSOR_OPTS_DEF = {
    OPT_NAME: "",
    OPT_DISPLAY_NAME: None,  ## default to name
    OPT_MQTT_TOPIC: "",  ## default to name
    OPT_STATUS_COMMAND: None,
    OPT_COMMAND_TIMEOUT: None,  # inherit
    OPT_REFRESH_INTERVAL: None,  # inherit
    OPT_MQTT_PREFIX: None,  # inherit
    OPT_MQTT_TOPIC_PREFIX: None,  # inherit
    OPT_MQTT_QOS: None,  # inherit
    OPT_MQTT_RETAIN: None,  # inherit
    OPT_IGNORE_RC: None,  # inherit
    OPT_FORMAT_COMMAND: None,  # inherit
    OPT_JSON_PAYLOAD: None,  # inherit
}
COMMAND_SENSOR_OPTS_SUB = {
    OPT_ATTRIBUTES: None,  # inherit
    OPT_MQTT_OUTPUT: None,  # inherit
    OPT_MQTT_ERROR: None,  # inherit
    OPT_DISCOVERY: None,  # inherit
}
COMMAND_SENSOR_OPTS_REQ = [OPT_NAME]
COMMAND_SENSOR_OPTS_ALL = {**COMMAND_SENSOR_OPTS_DEF, **COMMAND_SENSOR_OPTS_SUB}.keys()

DISCOVERY_OPTS_DEF = {
    OPT_ENTITY_TYPE: None,  # inherit
    OPT_CONFIG_REMOVE: None,  # inherit / replace_lists
    OPT_CONFIG_INHERIT: None,  # inherit
}
DISCOVERY_OPTS_ALL = DISCOVERY_OPTS_DEF.keys()

## Monitored Services options
MONITORED_SERVICES_OPTS_DEF = {
    **COMMAND_SENSORS_OPTS_DEF,
    OPT_STATUS_COMMAND: "/bin/systemctl is-active {service}",
    OPT_MQTT_TOPIC_PREFIX: "service",
    OPT_FORMAT_COMMAND: True,
    OPT_JSON_PAYLOAD: True,
    OPT_DISCOVERY: {
        OPT_ENTITY_TYPE: "binary_sensor",
        OPT_CONFIG_REMOVE: None,
        OPT_CONFIG_INHERIT: {
            # "icon": "mdi:code-greater-than",
            "device_class": "problem",
            "payload_on": "True",
            "payload_off": "False",
            "value_template": "{{ value_json.status != 'active' }}",
        },
    },
}
MONITORED_SERVICES_OPTS_SUB = {
    OPT_SERVICES: None,
    OPT_WATCHERS: None,
    OPT_MQTT_OUTPUT: None,  # inherit
    OPT_MQTT_ERROR: None,  # inherit
}
MONITORED_SERVICES_OPTS_ALL = {
    **MONITORED_SERVICES_OPTS_DEF,
    **MONITORED_SERVICES_OPTS_SUB,
}.keys()

## Monitored containers options
MONITORED_CONTAINERS_OPTS_DEF = {
    **COMMAND_SENSORS_OPTS_DEF,
    OPT_STATUS_COMMAND: "docker inspect -f '{{{{.State.Status}}}}' {container}",
    OPT_MQTT_TOPIC_PREFIX: "container",
    OPT_FORMAT_COMMAND: True,
    OPT_JSON_PAYLOAD: True,
    OPT_DISCOVERY: {
        OPT_ENTITY_TYPE: "binary_sensor",
        OPT_CONFIG_REMOVE: None,
        OPT_CONFIG_INHERIT: {
            # "icon": "mdi:docker",
            "device_class": "problem",
            "payload_on": "True",
            "payload_off": "False",
            "value_template": "{{ value_json.status != 'running' }}",
        },
    },
}
MONITORED_CONTAINERS_OPTS_SUB = {
    OPT_CONTAINERS: None,
    OPT_WATCHERS: None,
    OPT_MQTT_OUTPUT: None,  # inherit
    OPT_MQTT_ERROR: None,  # inherit
}
MONITORED_CONTAINERS_OPTS_ALL = {
    **MONITORED_CONTAINERS_OPTS_DEF,
    **MONITORED_CONTAINERS_OPTS_SUB,
}.keys()

## Monitored commands options
MONITORED_COMMANDS_OPTS_DEF = {
    **COMMAND_SENSORS_OPTS_DEF,
    OPT_STATUS_COMMAND: None,  # no default
    OPT_MQTT_TOPIC_PREFIX: None,  # set to group key
    OPT_JSON_PAYLOAD: False,
    OPT_DISCOVERY: {
        OPT_ENTITY_TYPE: "sensor",
        ## 20201215 removed icon default as binary_sensor doesn't support icons
        # OPT_CONFIG_INHERIT: {
        #     "icon": DEF_DISCOVERY_ICON,
        # },
    },
}
MONITORED_COMMANDS_OPTS_SUB = {
    OPT_COMMANDS: None,
    OPT_WATCHERS: None,
    OPT_MQTT_OUTPUT: None,  # inherit
    OPT_MQTT_ERROR: None,  # inherit
}
MONITORED_COMMANDS_OPTS_ALL = {
    **MONITORED_COMMANDS_OPTS_DEF,
    **MONITORED_COMMANDS_OPTS_SUB,
}.keys()

## Actions list options
ACTIONS_LIST_OPTS_DEF = {
    OPT_COMMAND_TIMEOUT: DEF_COMMAND_TIMEOUT,
    OPT_MQTT_PREFIX: None,  # inherit
    OPT_MQTT_TOPIC_PREFIX: "action",
    OPT_MQTT_QOS: DEF_MQTT_SUBSCRIBE_QOS,  # subscribe default
    OPT_APPEND_PAYLOAD: False,
    OPT_FORMAT_COMMAND: False,
}
ACTIONS_LIST_OPTS_SUB = {
    OPT_ACTIONS: None,
    OPT_MQTT_OUTPUT: None,
    OPT_MQTT_ERROR: None,
    OPT_IGNORE_RC: False,
}
ACTIONS_LIST_OPTS_ALL = {**ACTIONS_LIST_OPTS_DEF, **ACTIONS_LIST_OPTS_SUB}.keys()

ACTION_OPTS_DEF = {
    OPT_NAME: "",  # required
    OPT_MQTT_TOPIC: "",  # optional
    OPT_MQTT_PREFIX: None,  # inherit
    OPT_MQTT_TOPIC_PREFIX: None,  # inherit
    OPT_COMMAND: "",  # required if type(payload_match) is not dict
    OPT_COMMAND_TIMEOUT: None,  # inherit
    OPT_APPEND_PAYLOAD: None,  # inherit
    OPT_FORMAT_COMMAND: None,  # inherit
    OPT_MQTT_QOS: None,  # inherit
    OPT_IGNORE_RC: None,  # inherit
}
ACTION_OPTS_SUB = {
    OPT_PAYLOAD_MATCH: None,  # optional
    OPT_MQTT_OUTPUT: None,  # inherit
    OPT_MQTT_ERROR: None,  # inherit
}
ACTION_OPTS_REQ = [OPT_NAME]  # additional checks in action.py
ACTION_OPTS_ALL = {**ACTION_OPTS_DEF, **ACTION_OPTS_SUB}.keys()

## Asynchronous event types
EVENT_CONNECT = 1
EVENT_DISCONNECT = 2
EVENT_MESSAGE = 3
EVENT_COMMAND = 4
EVENT_WATCHER = 5
