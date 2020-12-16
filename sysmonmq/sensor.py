"""SysMonMQ Sensor class."""

import logging
import re
import json
from functools import reduce

from .const import APP_NAME, DEF_MQTT_QOS
from .config import (
    OPT_BIRTH,
    OPT_CLIENT,
    OPT_CLOSE,
    OPT_MQTT,
    OPT_MQTT_ERROR,
    OPT_MQTT_OUTPUT,
    OPT_MQTT_PREFIX,
    OPT_REFRESH_INTERVAL,
    OPT_SYSTEM_SENSORS,
    OPT_CPU_LOAD_AVERAGE,
    OPT_CPU_LOAD_FILE,
    OPT_CPU_LOAD_FORMAT,
    OPT_DISK_USAGE,
    OPT_DISK_USAGE_COMMAND,
    OPT_MEMORY_USAGE,
    OPT_MEMORY_USAGE_FILE,
    OPT_CPU_TEMP,
    OPT_TEMP_SENSOR_FILE,
    OPT_MQTT_TOPIC,
    OPT_MQTT_QOS,
    OPT_TOPIC,
    OPT_PAYLOAD,
    OPT_QOS,
    OPT_RETAIN,
    OPT_WILL,
    SYSTEM_SENSORS_OPTS_ALL,
    SYSTEM_SENSORS_OPTS_DEF,
    CPU_LOAD_OPTS_DEF,
    CPU_LOAD_OPTS_ALL,
    MEMORY_USAGE_OPTS_DEF,
    MEMORY_USAGE_OPTS_ALL,
    DISK_USAGE_OPTS_DEF,
    DISK_USAGE_OPTS_ALL,
    TEMP_OPTS_DEF,
    TEMP_OPTS_ALL,
)
from .mqtt import (
    mqtt_get_error_opts,
    mqtt_get_output_opts,
    mqtt_get_client_opts,
    mqtt_is_connected,
)
from .monitor import Monitor
from .util import check_opts, inherit_opts, merge, read_file, slugify
from .debug import is_debug_level

_LOGGER = logging.getLogger(APP_NAME)


class Sensor(Monitor):
    """Sensor base class."""

    def __init__(self, opts, config):
        super().__init__(opts=opts, config=config)
        self.refresh_interval = opts[OPT_REFRESH_INTERVAL]
        self.refresh_countdown = 0
        self.force_refresh = False

    def update(self, *args):
        """Stub update method."""
        raise RuntimeError(
            "Stub Sensor.update() called for "
            f"{str(self)}({type(self).__name__}) object"
        )

    def get_mqtt_device_data(self):
        """Device info for Home Assistant MQTT discovery config."""
        config = self.config
        device_data = {
            "device": {
                "identifiers": [APP_NAME + "_" + slugify(config.hostname)],
                "manufacturer": config.system_os,
                "model": config.system_hardware,
                "name": config.hostname,
                "sw_version": config.system_version,
            },
        }

        client_opts = mqtt_get_client_opts()
        birth_msg = client_opts[OPT_BIRTH]
        close_msg = client_opts[OPT_WILL]
        # close_prefix = close_msg[OPT_MQTT_PREFIX]
        # close_topic = close_msg[OPT_TOPIC]
        ## NOTE: assumes MQTT close and birth topics are the same, and
        ##       MQTT close and will payloads are the same
        birth_topic = birth_msg[OPT_TOPIC]
        birth_prefix = birth_msg[OPT_MQTT_PREFIX]
        if birth_topic is not None:
            device_data["availability"] = [
                {
                    "topic": self.get_topic(birth_topic, birth_prefix, ""),
                    "payload_available": birth_msg[OPT_PAYLOAD],
                    "payload_not_available": close_msg[OPT_PAYLOAD],
                },
            ]
        return device_data


class GlobalRefresh(Sensor):
    """Pseudo-sensor to refresh all sensors every global refresh_interval."""

    def __init__(self, refresh_interval, config):
        # super().__init__(opts, config)
        if is_debug_level(8):
            _LOGGER.debug(type(self).__name__ + "()")
        self.config = config
        self.refresh_interval = refresh_interval
        self.refresh_countdown = 0

    def update(self):
        """Flag force refresh for all sensors on next update."""
        config = self.config
        sensors = config.sensors
        assert isinstance(sensors, list) and len(sensors) >= 1

        if is_debug_level(4):
            _LOGGER.debug("GlobalRefresh: force refreshing all sensors")
        for sensor in sensors:
            if sensor != self and issubclass(type(sensor), Sensor):
                sensor.force_refresh = True
        config.force_check = True


class MQTTClientSensor(Sensor):
    """Pseudo-sensor represeting MQTT client. Sends birth message periodically."""

    def __init__(self, client_opts, config):
        client_opts[OPT_MQTT_TOPIC] = ""  # dummy topic
        client_opts[OPT_MQTT_QOS] = DEF_MQTT_QOS  # dummy qos
        super().__init__(client_opts, config)
        self._client_opts = client_opts

        ## Inconsistent close and will payloads causes issues with MQTT
        ## discovery as only one payload_not_available can be specified.
        payload_close = client_opts[OPT_CLOSE][OPT_PAYLOAD]
        payload_will = client_opts[OPT_WILL][OPT_PAYLOAD]
        if payload_close != payload_will:
            _LOGGER.warning("inconsistent MQTT close and will payloads")

    def update(self):
        """Send MQTT birth message on update."""
        if is_debug_level(4):
            _LOGGER.debug("MQTTClientSensor: publishing birth message")
        birth_opts = self._client_opts[OPT_BIRTH]
        topic = self.get_topic(birth_opts[OPT_TOPIC], birth_opts[OPT_MQTT_PREFIX])
        self.publish(
            birth_opts[OPT_PAYLOAD],
            topic=topic,
            qos=birth_opts[OPT_QOS],
            retain=birth_opts[OPT_RETAIN],
        )

    def get_mqtt_discovery_config(self, device_name, device_id, device_data):
        """System status Home Assistant MQTT discovery config."""
        if self.mqtt_topic is None:
            return None

        entity_name = "System Status"
        entity_slug = slugify(entity_name)
        birth_msg = self._client_opts[OPT_BIRTH]
        birth_topic = self.get_topic(birth_msg[OPT_TOPIC], birth_msg[OPT_MQTT_PREFIX])
        close_msg = self._client_opts[OPT_CLOSE]
        return {
            "binary_sensor": {
                entity_slug: {
                    "device": device_data["device"],  ## exclude availability
                    "unique_id": device_id + "_" + entity_slug,
                    "name": device_name + " " + entity_name,
                    "state_topic": birth_topic,
                    "device_class": "connectivity",
                    "payload_on": birth_msg[OPT_PAYLOAD],
                    "payload_off": close_msg[OPT_PAYLOAD],
                },
            },
        }


class CPULoadAverageSensor(Sensor):
    """CPU load average sensor."""

    def __init__(self, opts, config):
        super().__init__(opts, config)
        self._cpu_load_format = opts[OPT_CPU_LOAD_FORMAT]
        self._cpu_load_file = opts[OPT_CPU_LOAD_FILE]

    def update(self):
        """Update CPU load average sensor."""
        try:
            metrics = read_file(self._cpu_load_file).split(" ")
            load_1m = float(metrics[0])
            load_5m = float(metrics[1])
            load_15m = float(metrics[2])
        except Exception as e:
            if is_debug_level(4):
                _LOGGER.debug("CPULoadAverageSensor: error=%s", e)
            self.publish_error("Could not update CPU load average sensor", str(e))
        else:
            payload = json.dumps(
                {
                    "cpu_load_1m": self._cpu_load_format % load_1m,
                    "cpu_load_5m": self._cpu_load_format % load_5m,
                    "cpu_load_15m": self._cpu_load_format % load_15m,
                }
            )
            self.publish(payload)
            if is_debug_level(4):
                _LOGGER.debug("CPULoadAverageSensor: status=%s", payload)

    def get_mqtt_discovery_config(self, device_name, device_id, device_data):
        """CPU load average sensor Home Assistant MQTT discovery config."""
        cpu_load_icon = "mdi:chart-line"
        cpu_load_unit_of_measurement = "load"

        load_1m_name = "CPU Load (1m)"
        load_5m_name = "CPU Load (5m)"
        load_15m_name = "CPU Load (15m)"
        load_1m_slug = slugify(load_1m_name)
        load_5m_slug = slugify(load_5m_name)
        load_15m_slug = slugify(load_15m_name)
        topic = self.get_topic()
        return {
            "sensor": {
                load_1m_slug: {
                    **device_data,
                    "unique_id": device_id + "_" + load_1m_slug,
                    "icon": cpu_load_icon,
                    "name": device_name + " " + load_1m_name,
                    "state_topic": topic,
                    "unit_of_measurement": cpu_load_unit_of_measurement,
                    "value_template": "{{ value_json." + load_1m_slug + "}}",
                },
                load_5m_slug: {
                    **device_data,
                    "unique_id": device_id + "_" + load_5m_slug,
                    "icon": cpu_load_icon,
                    "name": device_name + " " + load_5m_name,
                    "state_topic": topic,
                    "unit_of_measurement": cpu_load_unit_of_measurement,
                    "value_template": "{{ value_json." + load_5m_slug + "}}",
                },
                load_15m_slug: {
                    **device_data,
                    "unique_id": device_id + "_" + load_15m_slug,
                    "icon": cpu_load_icon,
                    "name": device_name + " " + load_15m_name,
                    "state_topic": topic,
                    "unit_of_measurement": cpu_load_unit_of_measurement,
                    "value_template": "{{ value_json." + load_15m_slug + "}}",
                },
            },
        }


class MemoryUsageSensor(Sensor):
    """Memory usage sensor."""

    def __init__(self, opts, config):
        super().__init__(opts, config)
        self._memory_usage_file = opts[OPT_MEMORY_USAGE_FILE]

    def update(self):
        """Update memory usage sensor."""
        try:
            metrics = read_file(self._memory_usage_file).splitlines()
            metrics_list = list(
                map(lambda x: {x.split(":", 1)[0]: x.rsplit(" ", 2)[-2]}, metrics)
            )
            metrics_map = reduce(lambda x, y: dict(x, **y), metrics_list)
        except Exception as e:
            if is_debug_level(4):
                _LOGGER.debug("MemoryUsageSensor: error=%s", e)
            self.publish_error("Could not update memory usage sensor", str(e))
        else:
            self.publish(json.dumps(metrics_map))
            if is_debug_level(4):
                _LOGGER.debug("MemoryUsageSensor: status=%s", metrics_map)

    def get_mqtt_discovery_config(self, device_name, device_id, device_data):
        """Memory usage sensor Home Assistant MQTT discovery config."""
        entity_name = "Memory Usage"
        entity_slug = slugify(entity_name)
        entity_icon = "mdi:memory"
        entity_unit_of_measurement = "% memory"
        return {
            "sensor": {
                entity_slug: {
                    **device_data,
                    "unique_id": device_id + "_" + entity_slug,
                    "icon": entity_icon,
                    "name": device_name + " " + entity_name,
                    "state_topic": self.get_topic(),
                    "json_attributes_topic": self.get_topic(),
                    "unit_of_measurement": entity_unit_of_measurement,
                    "value_template": "{% if 'MemTotal' in value_json and 'MemAvailable' in value_json and value_json.MemTotal|int and value_json.MemAvailable|int(-1) > 0 %}{{ ((value_json.MemTotal|int-value_json.MemAvailable|int)/value_json.MemTotal|int*100)|round(2) }}{% else %}None{% endif %}",
                },
            },
        }


class DiskUsageSensor(Sensor):
    """Disk usage sensor."""

    def __init__(self, opts, config):
        super().__init__(opts, config)
        self._disk_usage_command = opts[OPT_DISK_USAGE_COMMAND]

    def update(self):
        """Update disk usage sensor."""
        try:
            self.queue_command(self._disk_usage_command)
        except Exception as e:
            self.publish_error("Could not queue update for disk usage sensor", str(e))

    def on_command_exit(self, com):
        """Parse output of disk usage command."""
        if com.err_msg:
            if is_debug_level(4):
                _LOGGER.debug("DiskUsageSensor: error=%s", com.err_msg)
            self.publish_error("Could not determine disk usage", com.err_msg)
        else:
            metrics = com.output.splitlines()
            try:
                metrics_header = metrics[0].lower().split(maxsplit=5)
                metrics_obj = {}
                for metric in metrics[1:]:
                    data = metric.split(maxsplit=5)
                    metrics_obj[data[5]] = {
                        metrics_header[1]: data[1],
                        metrics_header[2]: data[2],
                        metrics_header[3]: data[3],
                        metrics_header[0]: data[0],
                    }
            except Exception as e:
                if is_debug_level(4):
                    _LOGGER.debug("DiskUsageSensor: error=%s", e)
                self.publish_error("Could not update disk usage sensor", str(e))
            else:
                self.publish(json.dumps(metrics_obj))
                if is_debug_level(4):
                    _LOGGER.debug("DiskUsageSensor: status=%s", metrics_obj)

    def get_mqtt_discovery_config(self, device_name, device_id, device_data):
        """Disk usage sensor Home Assistant MQTT discovery config."""
        entity_name = "Disk Usage (root)"
        entity_slug = slugify(entity_name)
        entity_icon = "mdi:harddisk"
        entity_unit_of_measurement = "% disk"
        return {
            "sensor": {
                entity_slug: {
                    **device_data,
                    "unique_id": device_id + "_" + entity_slug,
                    "icon": entity_icon,
                    "name": device_name + " " + entity_name,
                    "state_topic": self.get_topic(),
                    "json_attributes_topic": self.get_topic(),
                    "unit_of_measurement": entity_unit_of_measurement,
                    "value_template": "{% if '/' in value_json and '1m-blocks' in value_json['/'] and 'used' in value_json['/'] and (value_json['/']['1m-blocks'])|int and value_json['/']['used']|int(-1) >= 0 %}{{ (value_json['/']['used']|int/value_json['/']['1m-blocks']|int*100)|round(2) }}{% else %}None{% endif %}",
                },
            },
        }


class TemperatureSensor(Sensor):
    """Temperature sensor."""

    def __init__(self, opts, config):
        super().__init__(opts, config)
        self._temp_sensor_file = opts[OPT_TEMP_SENSOR_FILE]
        self.current_temp = 0

    def update(self):
        """Update temperature sensor."""
        try:
            metric = read_file(self._temp_sensor_file)
            temp = round(float(re.sub(r"temp=([\d\.]*)..$", "\\1", metric)) / 1000, 1)
        except Exception as e:
            if is_debug_level(4):
                _LOGGER.debug("TemperatureSensor: error=%s", e)
            self.publish_error("Could not update temperature sensor", str(e))
        else:
            if self.force_refresh or temp != self.current_temp:
                self.publish("%.1f" % temp)
                self.current_temp = temp
                self.force_refresh = False
                if is_debug_level(4):
                    _LOGGER.debug("TemperatureSensor: temp=%.1f", temp)
            else:
                if is_debug_level(4):
                    _LOGGER.debug(
                        "TemperatureSensor: temp=%.1f (unchanged, skip publish)", temp
                    )

    def get_mqtt_discovery_config(self, device_name, device_id, device_data):
        """Temperature sensor Home Assistant MQTT discovery config."""
        entity_slug = "cpu_temperature"
        entity_icon = "mdi:thermometer"
        entity_unit_of_measurement = "°C"
        return {
            "sensor": {
                entity_slug: {
                    **device_data,
                    "unique_id": device_id + "_" + entity_slug,
                    "icon": entity_icon,
                    "name": device_name + " " + entity_slug,
                    "state_topic": self.get_topic(),
                    "unit_of_measurement": entity_unit_of_measurement,
                },
            },
        }


def _create_system_sensor(
    opt_class, opt_name, opts, opts_def, opts_all, base_opts, config
):  # -> Monitor|None
    err = False
    section = OPT_SYSTEM_SENSORS + " > " + opt_name
    sensor_opts = opts_def
    sensor = None
    if opts is None:  ## only section header supplied
        opts = {}
    if check_opts(opts, opts_all, section=section):
        merge(sensor_opts, opts, limit=0)
        inherit_opts(sensor_opts, base_opts)
    else:
        err = True

    ## Check service level mqtt_output and mqtt_error options
    mqtt_output_opts = mqtt_get_output_opts(
        opts.get(OPT_MQTT_OUTPUT),
        base_opts.get(OPT_MQTT_OUTPUT),
        section,
    )
    mqtt_error_opts = mqtt_get_error_opts(
        opts.get(OPT_MQTT_ERROR),
        base_opts.get(OPT_MQTT_ERROR),
        section,
    )
    if mqtt_output_opts is None or mqtt_error_opts is None:
        err = True
    else:
        sensor_opts[OPT_MQTT_OUTPUT] = mqtt_output_opts
        sensor_opts[OPT_MQTT_ERROR] = mqtt_error_opts

    if not err:
        sensor = opt_class(sensor_opts, config)

    return (sensor, sensor_opts) if not err else (None, None)


def setup_system_sensors(opts, top_opts, config):  # -> [Monitor]|None
    """Set up CPU load, memory/disk usage and temperature sensors."""
    if is_debug_level(8):
        _LOGGER.debug("setup_system_sensors(opts=%s)", opts)
    err = False
    sensors = []
    sensors_opts = SYSTEM_SENSORS_OPTS_DEF
    section = OPT_SYSTEM_SENSORS
    if not opts:
        return (sensors, sensors_opts)

    if check_opts(opts, SYSTEM_SENSORS_OPTS_ALL, section=OPT_SYSTEM_SENSORS):
        merge(sensors_opts, opts, limit=0)
        inherit_opts(sensors_opts, top_opts)
    else:
        err = True

    ## Check system_sensors level mqtt_output and mqtt_error options
    mqtt_output_opts = mqtt_get_output_opts(
        opts.get(OPT_MQTT_OUTPUT),
        top_opts[OPT_MQTT_OUTPUT],
        section=section,
    )
    mqtt_error_opts = mqtt_get_error_opts(
        opts.get(OPT_MQTT_ERROR),
        top_opts[OPT_MQTT_ERROR],
        section=section,
    )
    if mqtt_output_opts is None or mqtt_error_opts is None:
        err = True
    else:
        sensors_opts[OPT_MQTT_OUTPUT] = mqtt_output_opts
        sensors_opts[OPT_MQTT_ERROR] = mqtt_error_opts

    if not err:
        ## Set up global refresh sensor
        refresh_interval = config.refresh_interval
        sensors.append(GlobalRefresh(refresh_interval, config))

        ## Set up MQTT client sensor
        client_opts = top_opts[OPT_MQTT].get(OPT_CLIENT)
        if client_opts and client_opts[OPT_BIRTH][OPT_TOPIC]:
            sensors.append(MQTTClientSensor(client_opts, config))

    if OPT_CPU_LOAD_AVERAGE in opts:
        (cpu_load_sensor_obj, cpu_load_opts) = _create_system_sensor(
            CPULoadAverageSensor,
            OPT_CPU_LOAD_AVERAGE,
            opts[OPT_CPU_LOAD_AVERAGE],
            CPU_LOAD_OPTS_DEF,
            CPU_LOAD_OPTS_ALL,
            sensors_opts,
            config,
        )
        if cpu_load_sensor_obj is None:
            err = True
        else:
            sensors_opts[OPT_CPU_LOAD_AVERAGE] = cpu_load_opts
            sensors.append(cpu_load_sensor_obj)

    if OPT_MEMORY_USAGE in opts:
        (memory_usage_sensor_obj, memory_usage_opts) = _create_system_sensor(
            MemoryUsageSensor,
            OPT_MEMORY_USAGE,
            opts[OPT_MEMORY_USAGE],
            MEMORY_USAGE_OPTS_DEF,
            MEMORY_USAGE_OPTS_ALL,
            sensors_opts,
            config,
        )
        if memory_usage_sensor_obj is None:
            err = True
        else:
            sensors_opts[OPT_MEMORY_USAGE] = memory_usage_opts
            sensors.append(memory_usage_sensor_obj)

    if OPT_DISK_USAGE in opts:
        (disk_usage_sensor_obj, disk_usage_opts) = _create_system_sensor(
            DiskUsageSensor,
            OPT_DISK_USAGE,
            opts[OPT_DISK_USAGE],
            DISK_USAGE_OPTS_DEF,
            DISK_USAGE_OPTS_ALL,
            sensors_opts,
            config,
        )
        if disk_usage_sensor_obj is None:
            err = True
        else:
            sensors_opts[OPT_DISK_USAGE] = disk_usage_opts
            sensors.append(disk_usage_sensor_obj)

    if OPT_CPU_TEMP in opts:
        (temp_sensor_obj, temp_opts) = _create_system_sensor(
            TemperatureSensor,
            OPT_CPU_TEMP,
            opts[OPT_CPU_TEMP],
            TEMP_OPTS_DEF,
            TEMP_OPTS_ALL,
            sensors_opts,
            config,
        )
        if temp_sensor_obj is None:
            err = True
        else:
            sensors_opts[OPT_CPU_TEMP] = temp_opts
            sensors.append(temp_sensor_obj)

    return (sensors, sensors_opts) if not err else (None, None)


def update_sensors(config, sensors, slept_time=0):  # -> sleep_interval
    """Update list of sensors, calculate time to next refresh."""
    assert mqtt_is_connected()

    sleep_interval = config.refresh_interval
    if is_debug_level(8):
        _LOGGER.debug("update_sensors(force_check=%s)", config.force_check)
    for sensor in sensors:
        if issubclass(type(sensor), Sensor):
            sensor.refresh_countdown -= slept_time
            if sensor.refresh_countdown <= 0 or (
                config.force_check and not isinstance(sensor, GlobalRefresh)
            ):
                sensor.update()
                sensor.refresh_countdown = sensor.refresh_interval
            if sleep_interval > sensor.refresh_countdown:
                sleep_interval = sensor.refresh_countdown
        else:
            _LOGGER.warning("skipping update for %s", type(sensor).__name__)
    config.force_check = False
    return sleep_interval


def schedule_refresh_all_sensors(config, delay=0):
    """Flag force refresh of all sensors on next update."""
    sensors = config.sensors
    assert isinstance(sensors, list) and len(sensors) >= 1
    assert isinstance(sensors[0], GlobalRefresh)
    sensors[0].refresh_countdown = delay  ## Flag GlobalRefresh sensor
    config.force_check = True  ## Force next update to be full check
