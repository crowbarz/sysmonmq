"""SysMonMQ Action classes."""

import logging
from typing import List

from .const import APP_NAME, DEF_MQTT_DISCOVERY_UPDATE_DELAY
from .config import (
    OPT_ACTIONS_LIST,
    OPT_NAME,
    OPT_MQTT_TOPIC,
    OPT_COMMAND_TIMEOUT,
    OPT_COMMAND,
    OPT_APPEND_PAYLOAD,
    OPT_FORMAT_COMMAND,
    OPT_PAYLOAD_AVAILABLE,
    OPT_PAYLOAD_MATCH,
    OPT_IGNORE_RC,
    OPT_ACTIONS,
    OPT_MQTT_OUTPUT,
    OPT_MQTT_ERROR,
    OPT_TOPIC,
    OPT_QOS,
    ACTIONS_LIST_OPTS_DEF,
    ACTIONS_LIST_OPTS_ALL,
    ACTION_OPTS_DEF,
    ACTION_OPTS_REQ,
    ACTION_OPTS_ALL,
)
from .globals import SysMonMQ, MessageEvent
from .mqtt import (
    mqtt_get_error_opts,
    mqtt_get_output_opts,
    mqtt_message_callback_add,
    mqtt_subscribe,
)
from .monitor import Monitor
from .sensor import schedule_refresh_all_sensors
from .util import check_opts, deepcopy, inherit_opts, merge
from .debug import is_debug_level

_LOGGER = logging.getLogger(APP_NAME)


class Action(Monitor):
    """Action base class."""

    def __init__(self, opts, config):
        super().__init__(opts, config)

    def message_callback(self, mqttc, state, message):
        """Enqueue message and raise event flag."""
        if is_debug_level(4):
            _LOGGER.debug(
                "%s: topic=%s, payload=%s",
                type(self).__name__,
                message.topic,
                message.payload,
            )
        MessageEvent(self, message)

    def get_subscriptions(self):  # -> [( topic, qos )]
        """Itemise subscriptions for command action."""
        return [(self.get_topic(), self.mqtt_qos)]

    def on_message(self, *args) -> None:
        raise RuntimeError(
            "Stub Action.on_message() called for %s object", type(self).__name__
        )


class DiscoveryStatusAction(Action):
    """Action that monitors the MQTT discovery status topic."""

    def __init__(self, status_opts, config: SysMonMQ):
        # super().__init__(opts, config)
        if is_debug_level(8):
            _LOGGER.debug(
                type(self).__name__ + "(status_opts=%s)",
                status_opts,
            )
        self.mqtt_topic = status_opts[OPT_TOPIC]
        self.mqtt_qos = status_opts[OPT_QOS]
        self.mqtt_prefix = ""
        self.mqtt_topic_prefix = ""
        self.payload_available = status_opts[OPT_PAYLOAD_AVAILABLE]
        self._config = config

    def on_message(self, message):
        """Send MQTT discovery config on status available."""
        config = self._config
        topic = message.topic
        payload = str(message.payload, encoding="utf-8", errors="ignore")
        if is_debug_level(4):
            _LOGGER.debug("DiscoveryStatusAction: topic=%s, payload=%s", topic, payload)
        if payload == self.payload_available:
            send_mqtt_discovery(config)


class CommandAction(Action):
    """Action that executes a command on the local system."""

    ## NOTE: authorisation to be handled at MQTT level
    def __init__(self, opts, config):
        super().__init__(opts, config)
        self._command = opts[OPT_COMMAND]  ## required
        self._timeout = opts[OPT_COMMAND_TIMEOUT]  ## required
        self._append_payload = opts[OPT_APPEND_PAYLOAD]  ## required
        self._format_command = opts[OPT_FORMAT_COMMAND]  ## required
        self._payload_match = opts.get(OPT_PAYLOAD_MATCH)
        self.name = opts[OPT_NAME]  ## required
        self.ignore_rc = opts[OPT_IGNORE_RC]  ## required

    def on_message(self, message):
        """Message callback function from main event loop."""
        topic = message.topic
        payload = str(message.payload, encoding="utf-8", errors="ignore")
        try:
            match = True
            payload_match = self._payload_match
            command = self._command
            if payload_match is None:
                pass
            elif type(payload_match) == str:
                match = payload == payload_match
            elif type(payload_match) == list:
                match = payload in payload_match
            elif type(payload_match) == dict:
                match = payload in payload_match
                if match:
                    command = payload_match[payload]
                elif None in payload_match:
                    match = True
                    command = payload_match[None]
            else:
                _LOGGER.error(
                    "CommandAction(%s): payload match failed: %s: %s",
                    self.name,
                    payload_match,
                    type(payload_match).__name__,
                )
                match = False
            if match and command:
                if is_debug_level(4):
                    _LOGGER.debug('payload "%s" matched "%s"', payload, payload_match)
                if self._append_payload and payload:
                    command += " " + payload
                if self._format_command:
                    command = command.format(payload=payload)

                ## Queue command for a separate thread
                self.queue_command(
                    command, timeout=self._timeout, ignore_rc=self.ignore_rc
                )
                _LOGGER.debug(
                    'CommandAction(%s): payload="%s", queued command="%s")',
                    self.name,
                    payload,
                    command,
                )
            else:
                _LOGGER.debug(
                    'CommandAction(%s): unmatched payload="%s", ignoring',
                    self.name,
                    payload,
                )
        except Exception as e:
            if is_debug_level(4):
                _LOGGER.debug("CommandAction(%s): error=%s", self.name, e)
            self.publish_error(f'Could not queue action "{self.name}"', str(e))

    def on_command_exit(self, com):
        """Handle command completion from main event loop."""
        errmsg = com.err_msg
        command = self._command
        output = com.output
        rc = com.rc
        if errmsg:
            if is_debug_level(4):
                _LOGGER.debug("CommandAction(%s): error=%s", self.name, errmsg)
            self.publish_error(errmsg, command, output, rc)
        else:
            _LOGGER.info('CommandAction(%s): output="%s", rc=%s', self.name, output, rc)
            self.publish_output(command, output, rc)


def create_actions(actions, base_opts, config):  # -> [actions]
    """Create CommandActions from actions options."""
    err = False
    action_objs = []
    actions_opts = []
    base_opts[OPT_ACTIONS] = list()
    if actions is None:  ## only section header specified
        return (actions, actions_opts)

    for action in actions:
        action_opts = deepcopy(ACTION_OPTS_DEF)
        subsection = (
            OPT_ACTIONS_LIST
            + " > "
            + OPT_ACTIONS
            + " > "
            + action.get(OPT_NAME, "unknown")
        )
        if check_opts(action, ACTION_OPTS_ALL, ACTION_OPTS_REQ, section=subsection):
            merge(action_opts, action, limit=0)
            inherit_opts(action_opts, base_opts)

            ## Check payload_match and command options
            command = action_opts[OPT_COMMAND]
            payload_match = action.get(OPT_PAYLOAD_MATCH)
            payload_match_type = None if payload_match is None else type(payload_match)
            if payload_match_type not in [str, list, dict, None]:
                _LOGGER.error(
                    'payload_match must be type str, list or dict in "%s"',
                    subsection,
                )
                err = True
            elif (not command and payload_match_type is not dict) or (
                command and payload_match_type is dict
            ):
                _LOGGER.error(
                    'one of "command" or "payload_match" (type dict) required in "%s"',
                    subsection,
                )
                err = True
            elif payload_match_type is not None:
                ## Manually inherit payload_match due to polymorphic type
                action_opts[OPT_PAYLOAD_MATCH] = payload_match
            if action_opts[OPT_MQTT_TOPIC] == "":
                action_opts[OPT_MQTT_TOPIC] = action_opts[OPT_NAME]

            ## Check action level mqtt_output and mqtt_error options
            mqtt_output_opts = mqtt_get_output_opts(
                action.get(OPT_MQTT_OUTPUT),
                base_opts[OPT_MQTT_OUTPUT],
                subsection,
            )
            mqtt_error_opts = mqtt_get_error_opts(
                action.get(OPT_MQTT_ERROR),
                base_opts[OPT_MQTT_ERROR],
                subsection,
            )
            if mqtt_output_opts is None or mqtt_error_opts is None:
                err = True
            else:
                action_opts[OPT_MQTT_OUTPUT] = mqtt_output_opts
                action_opts[OPT_MQTT_ERROR] = mqtt_error_opts

            if not err:
                actions_opts.append(action_opts)
                action_objs.append(CommandAction(action_opts, config))
        else:
            err = True
    return (action_objs, actions_opts) if not err else (None, None)


def setup_actions_list(opts, top_opts, config):  # -> err(boolean)
    """Setup actions list."""
    if is_debug_level(8):
        _LOGGER.debug("setup_actions_list(opts=%s)", opts)
    err = False
    action_objs = []
    actions_list_opts = ACTIONS_LIST_OPTS_DEF
    if not opts:
        return (action_objs, actions_list_opts)

    if check_opts(opts, ACTIONS_LIST_OPTS_ALL, section=OPT_ACTIONS_LIST):
        ## Merge and inherit top level options
        merge(actions_list_opts, opts, limit=0)
        inherit_opts(actions_list_opts, top_opts)
    else:
        err = True

    ## Check action_list level mqtt_output and mqtt_error opts
    mqtt_output_opts = mqtt_get_output_opts(
        opts.get(OPT_MQTT_OUTPUT),
        top_opts[OPT_MQTT_OUTPUT],
        section=OPT_ACTIONS_LIST,
    )
    mqtt_error_opts = mqtt_get_error_opts(
        opts.get(OPT_MQTT_ERROR),
        top_opts[OPT_MQTT_ERROR],
        section=OPT_ACTIONS_LIST,
    )
    if mqtt_output_opts is None or mqtt_error_opts is None:
        err = True
    else:
        actions_list_opts[OPT_MQTT_OUTPUT] = mqtt_output_opts
        actions_list_opts[OPT_MQTT_ERROR] = mqtt_error_opts

    if not err and OPT_ACTIONS in opts:
        ## Create actions_list
        actions_list_opts[OPT_ACTIONS] = []
        (action_objs, actions_opts) = create_actions(
            opts[OPT_ACTIONS],
            actions_list_opts,
            config,
        )
        if action_objs is not None:
            actions_list_opts[OPT_ACTIONS] = actions_opts
        else:
            err = True

    return (action_objs, actions_list_opts) if not err else (None, None)


def setup_discovery_status(status_opts, config: SysMonMQ) -> List[Action]:
    """Create MQTT discovery status action."""
    if config.discovery_opts is None or status_opts is None:
        return None
    return [DiscoveryStatusAction(status_opts, config)]


def subscribe_actions(actions_list):  # -> bool
    """Subscribe to actions."""
    subs = []
    if actions_list is None:
        return None
    for action in actions_list:
        for sub in action.get_subscriptions():
            (topic, _) = sub
            subs.append(sub)
            mqtt_message_callback_add(topic, action.message_callback)
    if subs:
        _LOGGER.debug("subscribing to MQTT topics: %s", subs)
        return mqtt_subscribe(subs)


def send_mqtt_discovery(config):
    """Publish MQTT discovery options and schedule refresh of all sensors."""
    discovery_opts = config.discovery_opts
    for sensor in config.sensors:
        sensor.publish_mqtt_discovery(discovery_opts)
    schedule_refresh_all_sensors(config, DEF_MQTT_DISCOVERY_UPDATE_DELAY)
    config.force_check = True
