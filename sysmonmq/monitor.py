"""SysMonMQ monitor base class."""

import logging
import json

from .const import APP_NAME, DEF_COMMAND_TIMEOUT
from .config import (
    OPT_MQTT_ERROR,
    OPT_MQTT_OUTPUT,
    OPT_MQTT_OUTPUT_ON_ERROR,
    OPT_MQTT_PREFIX,
    OPT_MQTT_QOS,
    OPT_MQTT_RETAIN,
    OPT_MQTT_TOPIC,
    OPT_MQTT_TOPIC_PREFIX,
    OPT_MQTT_TOPIC_SUFFIX,
    OPT_TOPIC,
    OPT_QOS,
    OPT_RETAIN,
)
from .mqtt import mqtt_publish, mqtt_is_connected, mqtt_get_topic
from .command import Command
from .debug import is_debug_level

_LOGGER = logging.getLogger(APP_NAME)


class Monitor:
    """Monitor base class."""

    def __init__(self, opts, config):
        if is_debug_level(8):
            _LOGGER.debug(type(self).__name__ + "(opts=%s)", opts)
        self.config = config
        if config:
            mqtt_prefix = opts[OPT_MQTT_PREFIX]  # required
        else:
            mqtt_prefix = opts[OPT_MQTT_PREFIX]  # required
        mqtt_topic_prefix = opts.get(OPT_MQTT_TOPIC_PREFIX)
        mqtt_topic = opts[OPT_MQTT_TOPIC]  # required
        self.mqtt_prefix = mqtt_prefix
        self.mqtt_topic_prefix = mqtt_topic_prefix
        self.mqtt_topic = mqtt_topic
        self.mqtt_qos = opts[OPT_MQTT_QOS]  # required
        self.mqtt_retain = opts.get(OPT_MQTT_RETAIN)  # required for publish
        self._mqtt_output_opts = opts.get(OPT_MQTT_OUTPUT)
        self._mqtt_error_opts = opts.get(OPT_MQTT_ERROR)

        self.mqtt_output_topic = None
        if opts.get(OPT_MQTT_OUTPUT):
            mqtt_output = opts[OPT_MQTT_OUTPUT]
            self.mqtt_output_topic = self.get_topic(
                mqtt_topic,
                type_prefix=mqtt_output[OPT_MQTT_TOPIC_PREFIX],
                type_suffix=mqtt_output[OPT_MQTT_TOPIC_SUFFIX],
            )
            self.mqtt_output_qos = mqtt_output[OPT_MQTT_QOS]
            self.mqtt_output_retain = mqtt_output[OPT_MQTT_RETAIN]
        self.mqtt_error_topic = None
        if opts.get(OPT_MQTT_ERROR):
            mqtt_error = opts[OPT_MQTT_ERROR]
            self.mqtt_error_topic = self.get_topic(
                mqtt_topic,
                type_prefix=mqtt_error[OPT_MQTT_TOPIC_PREFIX],
                type_suffix=mqtt_error[OPT_MQTT_TOPIC_SUFFIX],
            )
            self.mqtt_error_qos = mqtt_error[OPT_MQTT_QOS]
            self.mqtt_error_retain = mqtt_error[OPT_MQTT_RETAIN]
            self.mqtt_output_on_error = mqtt_error[OPT_MQTT_OUTPUT_ON_ERROR]
        self.commands = []

    def get_topic(
        self,
        topic=None,
        prefix=None,
        topic_prefix=None,
        type_prefix=None,
        type_suffix=None,
    ) -> str:
        """Generate MQTT topic from components."""
        if topic is None:
            topic = self.mqtt_topic
        if prefix is None:
            prefix = self.mqtt_prefix
        if topic_prefix is None:
            topic_prefix = self.mqtt_topic_prefix
        return mqtt_get_topic(topic, prefix, topic_prefix, type_prefix, type_suffix)

    def publish(self, payload, topic=None, qos=None, retain=None):
        """Publish to MQTT monitor topic."""

        if topic is None:
            topic = self.get_topic()
        if qos is None:
            qos = self.mqtt_qos
        if retain is None:
            retain = self.mqtt_retain
        assert retain is not None

        if mqtt_is_connected():
            mqtt_publish(
                topic=topic,
                payload=payload,
                qos=qos,
                retain=retain,
            )
        else:
            _LOGGER.error(
                "MQTT broker not connected, not sending message: "
                'topic="%s", payload="%s"',
                topic,
                payload,
            )

    def publish_output(self, command=None, output=None, rc=0, errmsg=None):
        """Publish to MQTT output topic."""
        mqtt_output_opts = self._mqtt_output_opts
        assert mqtt_output_opts is not None

        mqtt_output_topic = self.get_topic(
            type_prefix=mqtt_output_opts[OPT_MQTT_TOPIC_PREFIX],
            type_suffix=mqtt_output_opts[OPT_MQTT_TOPIC_SUFFIX],
        )
        self.publish(
            json.dumps({"command": command, "output": output, "rc": rc}),
            topic=mqtt_output_topic,
            qos=mqtt_output_opts[OPT_MQTT_QOS],
            retain=mqtt_output_opts[OPT_MQTT_RETAIN],
        )

    def publish_error(self, errmsg, command=None, output=None, rc=255):
        """Publish to MQTT error topic."""
        mqtt_error_opts = self._mqtt_error_opts
        mqtt_output_opts = self._mqtt_output_opts
        assert mqtt_error_opts is not None and mqtt_output_opts is not None

        mqtt_error_topic = self.get_topic(
            type_prefix=mqtt_error_opts[OPT_MQTT_TOPIC_PREFIX],
            type_suffix=mqtt_error_opts[OPT_MQTT_TOPIC_SUFFIX],
        )
        self.publish(
            errmsg,
            topic=mqtt_error_topic,
            qos=mqtt_error_opts[OPT_MQTT_QOS],
            retain=mqtt_error_opts[OPT_MQTT_RETAIN],
        )
        if command and output and mqtt_error_opts[OPT_MQTT_OUTPUT_ON_ERROR]:
            self.publish_output(command, output, rc, errmsg)

    def publish_mqtt_discovery(self, discovery_opts, remove=False):
        """Publish config to MQTT discovery topic."""
        if not discovery_opts:  ## Discovery not enabled
            return

        if is_debug_level(4):
            _LOGGER.debug("publishing mqtt discovery for %s", type(self).__name__)
        discovery_topic = discovery_opts[OPT_TOPIC]
        discovery_qos = discovery_opts[OPT_QOS]
        discovery_retain = discovery_opts[OPT_RETAIN]

        device_data = self.get_mqtt_device_data()
        if not device_data:
            return

        device_name = device_data["device"]["name"]
        device_id = device_data["device"]["identifiers"][0]
        mqtt_discovery = self.get_mqtt_discovery_config(
            device_name, device_id, device_data
        )
        if not mqtt_discovery:  ## No discovery data for this sensor
            return

        if not mqtt_is_connected():
            _LOGGER.error(
                "MQTT broker not connected, not sending MQTT discovery message"
            )
            return

        for platform, platform_data in mqtt_discovery.items():
            for entity, entity_data in platform_data.items():
                topic = discovery_topic + "/" + platform
                topic += "/" + device_name + "/" + entity + "/config"
                self.publish(
                    json.dumps(entity_data) if not remove else "",
                    topic=topic,
                    qos=discovery_qos,
                    retain=discovery_retain,
                )

    def queue_command(self, command, timeout=DEF_COMMAND_TIMEOUT, ignore_rc=False):
        """Queue a command to be run by the thread pool."""
        com = Command(self, command, timeout, ignore_rc)
        self.commands.append(com)

    def process_command(self, com):
        """Process completed command."""
        self.on_command_exit(com)
        if com in self.commands:
            self.commands.remove(com)

    def on_command_exit(self, *args) -> None:
        """Stub command exit callback."""
        raise RuntimeError(
            "Stub Monitor.on_command_exit() called for " f"{type(self).__name__} object"
        )

    def get_mqtt_device_data(self):
        """Stub Home Assistant MQTT discovery device data callback."""
        return None

    def get_mqtt_discovery_config(self, device_name, device_id, device_data):
        """Stub Home Assistant MQTT discovery entity config callback."""
        return None
