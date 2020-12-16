"""SysMonMQ CommandSensor class."""

import json
import logging

from .const import APP_NAME, DEF_DISCOVERY_ENTITY_TYPE, DEF_DISCOVERY_ICON
from .config import (
    DISCOVERY_OPTS_ALL,
    DISCOVERY_OPTS_DEF,
    OPT_ATTRIBUTES,
    OPT_CONFIG_INHERIT,
    OPT_CONFIG_REMOVE,
    OPT_DISCOVERY,
    OPT_ENTITY_TYPE,
    OPT_FORMAT_COMMAND,
    OPT_MONITORED_SERVICES,
    OPT_MONITORED_CONTAINERS,
    OPT_MONITORED_COMMANDS,
    OPT_MQTT_TOPIC_PREFIX,
    OPT_SERVICES,
    OPT_CONTAINERS,
    OPT_COMMANDS,
    OPT_IGNORE_RC,
    OPT_WATCHERS,
    OPT_NAME,
    OPT_DISPLAY_NAME,
    OPT_STATUS_COMMAND,
    OPT_MQTT_TOPIC,
    OPT_MQTT_OUTPUT,
    OPT_MQTT_ERROR,
    OPT_JSON_PAYLOAD,
    COMMAND_SENSOR_OPTS_ALL,
    COMMAND_SENSOR_OPTS_DEF,
    COMMAND_SENSOR_OPTS_REQ,
    MONITORED_CONTAINERS_OPTS_ALL,
    MONITORED_CONTAINERS_OPTS_DEF,
    MONITORED_SERVICES_OPTS_ALL,
    MONITORED_SERVICES_OPTS_DEF,
    MONITORED_COMMANDS_OPTS_ALL,
    MONITORED_COMMANDS_OPTS_DEF,
)
from .sensor import Sensor
from .mqtt import mqtt_get_error_opts, mqtt_get_output_opts
from .util import check_opts, deepcopy, inherit_opts, merge, without_keys, slugify
from .watcher import get_watchers_opts
from .debug import is_debug_level

_LOGGER = logging.getLogger(APP_NAME)


class CommandSensor(Sensor):
    """Command sensor."""

    def __init__(self, opts, command, config):
        name = opts[OPT_NAME]  # required
        if opts[OPT_MQTT_TOPIC] == "":
            opts[OPT_MQTT_TOPIC] = name  # default to name
        super().__init__(opts, config)

        self.name = name
        self.display_name = opts.get(OPT_DISPLAY_NAME)
        if not self.display_name:
            self.display_name = name  # default to name
        self.service_status = None
        self.force_refresh = False

        self._config = config
        self._ignore_rc = opts[OPT_IGNORE_RC]  # required
        self._format_command = opts[OPT_FORMAT_COMMAND]  # required,
        self._json_payload = opts[OPT_JSON_PAYLOAD]  # required
        self._discovery = opts.get(OPT_DISCOVERY)
        self._attributes = opts.get(OPT_ATTRIBUTES)
        self._command = command

    def update(self):
        """Update service sensor."""
        command = self._command
        if self._format_command:
            try:
                command = self._command.format(
                    service=self.name, container=self.name, command=self.name
                )
            except Exception as e:
                self.publish_error(f'Could not format command for "{self.name}', str(e))
                return
        try:
            self.queue_command(command, ignore_rc=self._ignore_rc)
            if is_debug_level(4):
                _LOGGER.debug(
                    'CommandSensor(%s): queued command="%s"', self.name, command
                )
        except Exception as e:
            if is_debug_level(4):
                _LOGGER.debug("CommandAction(%s): error=%s", self.name, e)
            self.publish_error(f'Could not queue command for "{self.name}"', str(e))
            return

    def on_command_exit(self, com):
        """Parse output of sensor status command."""
        config = self._config
        status = com.output
        if com.err_msg:
            if is_debug_level(4):
                _LOGGER.debug("CommandSensor(%s): error=%s", self.name, com.err_msg)
            self.publish_error(
                f'Could not retrieve status update for "{self.name}"', com.err_msg
            )
        elif self.force_refresh or status != self.service_status:
            if self._json_payload:
                status_json = None
                try:
                    status_json = json.loads(status)
                    if not isinstance(status_json, dict):
                        status_json = None
                except ValueError:
                    pass

                payload = {
                    "host": config.hostname,
                    "section": self.mqtt_topic_prefix,
                    "topic": self.mqtt_topic,
                    "display_name": self.display_name,
                    **self._attributes,
                }
                if status_json:
                    payload.update(status_json)
                else:
                    payload.update({"status": status})
                self.publish(json.dumps(payload))
            else:
                self.publish(status)
            _LOGGER.debug("CommandSensor(%s): status=%s", self.name, status)
            self.service_status = status
            self.force_refresh = False
        else:
            if is_debug_level(4):
                _LOGGER.debug(
                    "CommandSensor(%s): status=%s (unchanged, skip publish)",
                    self.name,
                    status,
                )

    def get_mqtt_discovery_config(self, device_name, device_id, device_data):
        """Command sensor Home Assistant MQTT discovery config."""
        discovery = self._discovery if self._discovery is not None else {}
        name = self.name
        name_slug = slugify(name)
        topic_prefix = self.mqtt_topic_prefix + " " if self.mqtt_topic_prefix else ""
        topic_prefix_slug = slugify(topic_prefix) + ("_" if topic_prefix else "")
        display_name = self.display_name

        entity_type = DEF_DISCOVERY_ENTITY_TYPE
        if OPT_ENTITY_TYPE in discovery:
            entity_type = discovery[OPT_ENTITY_TYPE]
        config_remove = []
        if OPT_CONFIG_REMOVE in discovery:
            config_remove = discovery[OPT_CONFIG_REMOVE]
        config_inherit = {}
        if OPT_CONFIG_INHERIT in discovery:
            config_inherit = discovery[OPT_CONFIG_INHERIT]

        entity_data = {
            **device_data,
            "unique_id": device_id + "_" + topic_prefix_slug + name_slug,
            "name": device_name + " " + topic_prefix + display_name,
            "state_topic": self.get_topic(),
        }

        if self._json_payload:
            entity_data.update(
                {
                    "json_attributes_topic": self.get_topic(),
                    "value_template": "{{ value_json.status }}",
                }
            )

        if config_remove:
            entity_data = without_keys(entity_data, config_remove)
        merge(entity_data, config_inherit)
        return {entity_type: {name_slug: entity_data}}


def create_command_sensors(
    services, base_opts, config, section
):  # -> ([Sensor]|None, opts)
    """Create CommandSensors from services and containers options."""
    err = False
    sensors = []
    sensors_opts = []
    if services is None:  ## only section header specified
        return (sensors, sensors_opts)

    for service in services:
        service_opts = deepcopy(COMMAND_SENSOR_OPTS_DEF)
        name = service.get(OPT_NAME) if service.get(OPT_NAME) else "(unknown)"
        subsection = section + " > " + name
        if check_opts(
            service,
            COMMAND_SENSOR_OPTS_ALL,
            COMMAND_SENSOR_OPTS_REQ,
            section=subsection,
        ):
            merge(service_opts, service, limit=0)
            inherit_opts(service_opts, base_opts)
            if not service_opts[OPT_STATUS_COMMAND]:
                _LOGGER.error(
                    'required option "%s" missing in "%s"',
                    OPT_STATUS_COMMAND,
                    subsection,
                )
                err = True
        else:
            err = True

        ## Check service level attributes options
        attributes_opts = dict(base_opts[OPT_ATTRIBUTES])
        if OPT_ATTRIBUTES in service:
            if service[OPT_ATTRIBUTES] is None:
                pass
            elif not isinstance(service[OPT_ATTRIBUTES], dict):
                _LOGGER.error(
                    'option "%s" in "%s" is not a dict', OPT_ATTRIBUTES, subsection
                )
                err = True
            else:
                attributes_opts = dict(service[OPT_ATTRIBUTES])
        if not err:
            service_opts[OPT_ATTRIBUTES] = attributes_opts

        ## Check service level mqtt_output and mqtt_error options
        mqtt_output_opts = mqtt_get_output_opts(
            service.get(OPT_MQTT_OUTPUT),
            base_opts[OPT_MQTT_OUTPUT],
            subsection,
        )
        mqtt_error_opts = mqtt_get_error_opts(
            service.get(OPT_MQTT_ERROR),
            base_opts[OPT_MQTT_ERROR],
            subsection,
        )
        if mqtt_output_opts is None or mqtt_error_opts is None:
            err = True
        else:
            service_opts[OPT_MQTT_OUTPUT] = mqtt_output_opts
            service_opts[OPT_MQTT_ERROR] = mqtt_error_opts

        ## Check service level discovery options
        discovery_opts = dict(DISCOVERY_OPTS_DEF)
        service_opts[OPT_DISCOVERY] = discovery_opts
        merge(discovery_opts, base_opts[OPT_DISCOVERY], replace_lists=True)
        if OPT_DISCOVERY in service:
            opt_discovery = service[OPT_DISCOVERY]
            if check_opts(
                opt_discovery,
                DISCOVERY_OPTS_ALL,
                section=subsection + " > " + OPT_DISCOVERY,
            ):
                ## Merge discovery sub-options
                merge(discovery_opts, opt_discovery)
            else:
                err = True

        if not err:
            sensors_opts.append(service_opts)
            command = service_opts[OPT_STATUS_COMMAND]
            sensors.append(CommandSensor(service_opts, command, config))

    return (sensors, sensors_opts) if not err else (None, None)


def setup_command_sensors(
    opts_name, opts, opts_def, opts_all, opt_list_key, base_opts, config
):  # -> ([Monitor]|None, [Watcher], opts)
    """Set up command sensors."""
    if is_debug_level(8):
        _LOGGER.debug("setup_command_sensors(opts_name=%s, opts=%s)", opts_name, opts)
    err = False
    sensors = []
    watchers = []
    sensors_opts = opts_def
    if not opts:
        return (sensors, watchers, sensors_opts)

    if check_opts(opts, opts_all, section=opts_name):
        ## Merge and inherit top level options
        merge(sensors_opts, opts, limit=0)
        inherit_opts(sensors_opts, base_opts)
    else:
        err = True

    ## Check monitored_* level attributes options
    attributes_opts = {}  ## No default attributes
    if OPT_ATTRIBUTES in opts:
        if opts[OPT_ATTRIBUTES] is None:
            pass
        elif not isinstance(opts[OPT_ATTRIBUTES], dict):
            _LOGGER.error(
                'option "%s" in "%s" is not a dict', OPT_ATTRIBUTES, opts_name
            )
            err = True
        else:
            attributes_opts = dict(opts[OPT_ATTRIBUTES])
    if not err:
        sensors_opts[OPT_ATTRIBUTES] = attributes_opts

    ## Check monitored_* level mqtt_output and mqtt_error options
    mqtt_output_opts = mqtt_get_output_opts(
        opts.get(OPT_MQTT_OUTPUT),
        base_opts[OPT_MQTT_OUTPUT],
        section=opts_name,
    )
    mqtt_error_opts = mqtt_get_error_opts(
        opts.get(OPT_MQTT_ERROR),
        base_opts[OPT_MQTT_ERROR],
        section=opts_name,
    )
    if mqtt_output_opts is None or mqtt_error_opts is None:
        err = True
    if not err:
        sensors_opts[OPT_MQTT_OUTPUT] = mqtt_output_opts
        sensors_opts[OPT_MQTT_ERROR] = mqtt_error_opts

    ## Check monitored_* level discovery options
    if OPT_DISCOVERY in opts:
        opt_discovery = opts[OPT_DISCOVERY]
        if check_opts(
            opt_discovery, DISCOVERY_OPTS_ALL, section=opts_name + " > " + OPT_DISCOVERY
        ):
            ## Merge discovery sub-options
            ## Defaults defined in respective monitor_* defaults
            merge(sensors_opts[OPT_DISCOVERY], opt_discovery, replace_lists=True)

    if not err and opt_list_key in opts:
        ## Create service sensors
        (sensors, commands_opts) = create_command_sensors(
            opts[opt_list_key],
            sensors_opts,
            config,
            section=f"{opts_name} > {opt_list_key}",
        )
        if sensors is not None:
            sensors_opts[opt_list_key] = commands_opts
        else:
            err = True

    ## Create watchers if sensors are created and watchers specified
    if not err and sensors and OPT_WATCHERS in opts:
        (watchers, watcher_opts) = get_watchers_opts(
            opts[OPT_WATCHERS],
            sensors,
            section=opts_name,
        )
        if watchers is not None:
            sensors_opts[OPT_WATCHERS] = watcher_opts
        else:
            err = True

    if not err:
        return (sensors, watchers, sensors_opts)
    else:
        return (None, None, None)


def setup_monitored_services(
    opts, top_opts, config
):  # -> ([Monitor]|None, [Watcher], opts)
    """Set up monitored services."""

    return setup_command_sensors(
        OPT_MONITORED_SERVICES,
        opts,
        MONITORED_SERVICES_OPTS_DEF,
        MONITORED_SERVICES_OPTS_ALL,
        OPT_SERVICES,
        top_opts,
        config,
    )


def setup_monitored_containers(
    opts, top_opts, config
):  # -> ([Monitor]|None, [Watcher], opts)
    """Set up monitored containers."""

    return setup_command_sensors(
        OPT_MONITORED_CONTAINERS,
        opts,
        MONITORED_CONTAINERS_OPTS_DEF,
        MONITORED_CONTAINERS_OPTS_ALL,
        OPT_CONTAINERS,
        top_opts,
        config,
    )


def setup_monitored_commands(
    opts, top_opts, config
):  # -> ([Monitor]|None, [Watcher], opts)
    """Set up monitored commands keys."""

    err = False
    sensors_all = []
    watchers_all = []
    opts_all = {}

    if opts is None:
        return (sensors_all, watchers_all, opts_all)

    for opt_key, opts_key in opts.items():
        section = OPT_MONITORED_COMMANDS + " > " + opt_key
        commands_opts_def = deepcopy(MONITORED_COMMANDS_OPTS_DEF)
        commands_opts_def[OPT_MQTT_TOPIC_PREFIX] = opt_key
        (sensors, watchers, command_opts) = setup_command_sensors(
            section,
            opts_key,
            commands_opts_def,
            MONITORED_COMMANDS_OPTS_ALL,
            OPT_COMMANDS,
            top_opts,
            config,
        )
        if sensors is None:
            err = True
        else:
            sensors_all += sensors
            watchers_all += watchers
            opts_all[opt_key] = command_opts
    if err:
        return (None, None, None)
    else:
        return (sensors_all, watchers_all, opts_all)
