"""SysMonMQ main loop."""

import signal
from threading import main_thread
import logging
import time
import traceback

import yaml

from .const import APP_NAME, DEF_THREAD_MAIN
from .config import (
    OPT_DUMP_CONFIG,
    OPT_MQTT,
    OPT_RECONNECT_DELAY_MAX,
    OPT_REFRESH_INTERVAL,
)
from .globals import (
    MQTTSubscribeEvent,
    SysMonMQ,
    MQTTError,
    MQTTConnectEvent,
    MQTTDisconnectEvent,
    MQTTSubscribeEvent,
    MQTTDiscoveryEvent,
    CommandEvent,
    MessageEvent,
    WatcherEvent,
)
from .options import parse_opts
from .mqtt import mqtt_close, mqtt_connect, mqtt_is_connected, mqtt_error_string
from .action import send_mqtt_discovery, subscribe_actions
from .sensor import update_sensors
from .debug import is_debug_level

_LOGGER = logging.getLogger(APP_NAME)


def sigterm_handler(signal, frame):
    raise Exception("SIGTERM caught, exiting")


def get_event():
    """Retrieve next event from the event queue."""
    with SysMonMQ.lock:
        if SysMonMQ.events:
            ## Retrieve event queue
            event = SysMonMQ.events.pop(0)
            if not SysMonMQ.events:
                SysMonMQ.event.clear()
            return event
    return None


def handle_event(config, event):
    """Handle SysMonitor events."""
    if is_debug_level(5):
        _LOGGER.debug("handling event %s", type(event).__name__)
    if isinstance(event, MQTTConnectEvent):
        if event.rc != 0:
            raise MQTTError("could not connect to broker: %s", event.errmsg)
        _LOGGER.info("connected to MQTT broker")
        MQTTSubscribeEvent()
        MQTTDiscoveryEvent()

        ## TODO: queue new event
    elif isinstance(event, MQTTDisconnectEvent):
        if event.rc != 0:
            raise MQTTError("error disconnecting from broker: %s", event.errmsg)
        else:
            _LOGGER.info("disconnected from MQTT broker")
            ## TODO: stop or ignore watchers
    elif not mqtt_is_connected():
        _LOGGER.warning(
            "not connected to MQTT broker, ignoring event %s", type(event).__name__
        )
    elif isinstance(event, MQTTSubscribeEvent):
        rc = subscribe_actions(config.actions)
        if rc is not True:
            raise MQTTError("could not subscribe: %s", mqtt_error_string(rc))
    elif isinstance(event, MQTTDiscoveryEvent):
        send_mqtt_discovery(config)  ## will trigger sensor refresh
    elif isinstance(event, MessageEvent):
        event.action.on_message(event.message)
    elif isinstance(event, CommandEvent):
        event.monitor.process_command(event.com)
    elif isinstance(event, WatcherEvent):
        config.force_check = True
        # update_sensors(config, event.sensors)
    else:
        raise RuntimeError(f"Unhandled event: {type(event).__name__}")


def main():
    main_thread().name = DEF_THREAD_MAIN
    config = SysMonMQ()
    top_opts = parse_opts(config)
    if top_opts is None:  ## config error
        exit(1)
    elif top_opts.get(OPT_DUMP_CONFIG):
        print("Generated configuration:\n" + yaml.dump(top_opts))
        exit(0)

    mqtt_opts = top_opts[OPT_MQTT]
    mqttc = mqtt_connect(config.mqtt_debug)
    if mqttc is None:
        exit(1)
    signal.signal(signal.SIGTERM, sigterm_handler)

    ## Wait MQTT_RECONNECT_DELAY_MAX seconds before initial connection
    reconnect_delay_max = mqtt_opts[OPT_RECONNECT_DELAY_MAX]
    sleep_interval = reconnect_delay_max

    ## Main loop
    while True:
        sleep_start = time.time()
        if is_debug_level(6):
            _LOGGER.debug("sleeping for %ds", sleep_interval)
        SysMonMQ.event.wait(timeout=sleep_interval)
        slept_time = int(time.time() - sleep_start)
        if is_debug_level(6):
            _LOGGER.debug("slept for %ds", slept_time)
        sleep_interval = config.refresh_interval

        event = get_event()
        connected = mqtt_is_connected()
        if event:
            ## Handle event queue
            config.force_check = False
            try:
                handle_event(config, event)
            except MQTTError as exc:
                _LOGGER.error("MQTT error: %s", exc)
                if mqtt_is_connected() is None:
                    break  ## exit on initial connection failure

            ## re-run event loop until events are cleared
            sleep_interval = 0
        elif connected is None:

            _LOGGER.error("initial connection to MQTT broker timed out")
            break  ## exit on initial connection timeout
        elif not connected:
            ## Disconnected state, waiting for reconnection
            _LOGGER.warning("waiting for MQTT broker reconnection")
            sleep_interval = reconnect_delay_max
        else:
            ## Handle sensor updates
            sleep_interval = update_sensors(config, config.sensors, slept_time)

    ## Abnormally exited main loop
    exit(1)


def entry_point():
    try:
        main()
        exit(0)
    except KeyboardInterrupt:
        _LOGGER.warning("keyboard interrupt, exiting")
        mqtt_close()
        exit(255)
    except Exception as e:
        _LOGGER.error("Exception: %s", e)
        # if is_debug_level(2):
        traceback.print_exc()
        mqtt_close()
        exit(1)
