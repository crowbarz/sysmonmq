"""SysMonMQ options functions."""

import logging
import argparse
import yaml


from .const import APP_NAME, APP_VERSION
from .config import (
    OPT_DEBUG,
    OPT_CONFIG_FILE,
    OPT_DISCOVERY,
    OPT_DUMP_CONFIG,
    OPT_DUMP_CONFIG_CLI,
    OPT_MONITORED_COMMANDS,
    OPT_MQTT,
    OPT_MQTT_ERROR,
    OPT_MQTT_OUTPUT,
    OPT_MQTT_PREFIX,
    OPT_MQTT_PREFIX_HOST,
    OPT_REFRESH_INTERVAL,
    OPT_STATUS,
    OPT_SYSTEM_SENSORS,
    OPT_MONITORED_SERVICES,
    OPT_MONITORED_CONTAINERS,
    OPT_ACTIONS_LIST,
    TOP_OPTS_DEF,
    TOP_OPTS_ALL,
    TOP_OPTS_SUB_ALL,
    MQTT_OUTPUT_OPTS_ALL,
    MQTT_ERROR_OPTS_ALL,
)
from .util import check_opts, merge, without_keys
from .mqtt import mqtt_setup
from .sensor import setup_system_sensors
from .command_sensor import (
    setup_monitored_commands,
    setup_monitored_services,
    setup_monitored_containers,
)
from .action import setup_actions_list, setup_discovery_status
from .debug import configure_debug

_LOGGER = logging.getLogger(APP_NAME)


def get_cli_options():
    """Read options on command line."""
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument(
        "-d",
        "--" + OPT_DEBUG,
        help="set debugging level",
        type=int,
        nargs="?",
        const=1,
        default=0,
    )
    parser.add_argument(
        "--" + OPT_DUMP_CONFIG_CLI,
        help="dump full config and exit",
        action="store_true",
        dest=OPT_DUMP_CONFIG,
    )
    parser.add_argument(
        "-c", "--" + OPT_CONFIG_FILE, action="append", help="set config file location"
    )
    parser.add_argument(
        "-v",
        "--version",
        help="show application version",
        action="version",
        version="%(prog)s " + APP_VERSION,
    )
    args = vars(parser.parse_args())
    _LOGGER.debug("read arguments: %s", args)
    return args


def get_config_file_options(config_file):
    """Read options from config file."""
    ok = True
    if type(config_file) == list:
        cfg = {}
        for f in config_file:
            more_cfg = get_config_file_options(f)
            if more_cfg is not None:
                merge(cfg, more_cfg, merge_none=True)
            else:
                return None
        return cfg

    try:
        with open(config_file, "r") as ymlfile:
            cfg = yaml.safe_load(ymlfile)
        if cfg is None:
            cfg = {}
        _LOGGER.debug('read configuration file "%s": %s', config_file, cfg)
        return cfg
    except Exception as e:
        _LOGGER.warning('could not read config file "%s": %s', config_file, e)
        return None


def get_config_options(opts):  # -> opts
    """Read config options."""

    ## Get command line options
    cli_opts = get_cli_options()
    if cli_opts is None:
        return None
    merge(opts, cli_opts, merge_none=True)

    ## Get config file options
    cfg_opts = get_config_file_options(opts[OPT_CONFIG_FILE])
    if cfg_opts is None:
        return None
    merge(opts, cfg_opts, merge_none=True)
    return opts


def parse_opts(config):  # -> top_opts
    """Parse configuration options."""
    assert config.sensors == [] and config.actions == [] and config.watchers == []

    err = False
    top_opts = TOP_OPTS_DEF
    configure_debug(top_opts, config)
    opts = get_config_options(top_opts)

    ## Check options hierarchy
    if opts is None:
        return None
    elif not check_opts(opts, TOP_OPTS_ALL):
        err = True
    if OPT_MQTT_OUTPUT in opts:
        if not check_opts(opts[OPT_MQTT_OUTPUT], MQTT_OUTPUT_OPTS_ALL):
            err = True
    if OPT_MQTT_ERROR in opts:
        if not check_opts(opts[OPT_MQTT_ERROR], MQTT_ERROR_OPTS_ALL):
            err = True
    merge(top_opts, without_keys(opts, TOP_OPTS_SUB_ALL))
    configure_debug(top_opts, config)
    config.refresh_interval = top_opts[OPT_REFRESH_INTERVAL]

    ## Set MQTT prefix
    if top_opts[OPT_MQTT_PREFIX_HOST]:
        if top_opts[OPT_MQTT_PREFIX]:
            top_opts[OPT_MQTT_PREFIX] += "/" + config.hostname
        else:
            top_opts[OPT_MQTT_PREFIX] = config.hostname
    config.mqtt_prefix = top_opts[OPT_MQTT_PREFIX]

    ## Parse MQTT options
    mqtt_opts = mqtt_setup(opts.get(OPT_MQTT), top_opts, config)
    if mqtt_opts:
        top_opts[OPT_MQTT] = mqtt_opts
        config.discovery_opts = mqtt_opts.get(OPT_DISCOVERY)
        status_opts = mqtt_opts[OPT_STATUS]
        status_actions = setup_discovery_status(status_opts, config)
        if status_actions:
            config.actions += status_actions
    else:
        err = True

    ## Parse subsystem options
    if OPT_SYSTEM_SENSORS in opts:
        (system_sensors, sensors_opts) = setup_system_sensors(
            opts[OPT_SYSTEM_SENSORS], top_opts, config
        )
        if system_sensors is None:
            err = True
        else:
            config.sensors += system_sensors
            top_opts[OPT_SYSTEM_SENSORS] = sensors_opts

    if OPT_MONITORED_SERVICES in opts:
        (
            service_sensors,
            service_watchers,
            services_opts,
        ) = setup_monitored_services(opts[OPT_MONITORED_SERVICES], top_opts, config)
        if service_sensors is None:
            err = True
        else:
            config.sensors += service_sensors
            config.watchers += service_watchers
            top_opts[OPT_MONITORED_SERVICES] = services_opts

    if OPT_MONITORED_CONTAINERS in opts:
        (
            container_sensors,
            container_watchers,
            container_opts,
        ) = setup_monitored_containers(opts[OPT_MONITORED_CONTAINERS], top_opts, config)
        if container_sensors is None:
            err = True
        else:
            config.sensors += container_sensors
            config.watchers += container_watchers
            top_opts[OPT_MONITORED_CONTAINERS] = container_opts

    if OPT_MONITORED_COMMANDS in opts:
        (
            command_sensors,
            command_watchers,
            command_opts,
        ) = setup_monitored_commands(opts[OPT_MONITORED_COMMANDS], top_opts, config)
        if command_sensors is None:
            err = True
        else:
            config.sensors += command_sensors
            config.watchers += command_watchers
            top_opts[OPT_MONITORED_COMMANDS] = command_opts

    if OPT_ACTIONS_LIST in opts:
        (actions_list, actions_list_opts) = setup_actions_list(
            opts[OPT_ACTIONS_LIST],
            top_opts,
            config,
        )
        if actions_list is None:
            err = True
        else:
            config.actions += actions_list
            top_opts[OPT_ACTIONS_LIST] = actions_list_opts
    if err:
        return None

    config.opts = top_opts
    return top_opts
