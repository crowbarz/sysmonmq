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
    SysMonMQ,
    MQTTConnectEvent,
    MQTTDisconnectEvent,
    CommandEvent,
    MessageEvent,
    WatcherEvent,
)
from .options import parse_opts
from .mqtt import mqtt_close, mqtt_connect, mqtt_is_connected
from .action import send_mqtt_discovery, subscribe_actions
from .sensor import schedule_refresh_all_sensors, update_sensors
from .debug import is_debug_level

_LOGGER = logging.getLogger(APP_NAME)


def sigterm_handler(signal, frame):
    raise Exception("SIGTERM caught, exiting")


def handle_events(config):
    # -> type(bool): True==connect event, False==disconnect event
    #    type(NoneType): error
    #    type(int): sleep_interval
    """Handle SysMonitor events."""
    sleep_interval = config.refresh_interval
    while SysMonMQ.events:
        event = SysMonMQ.events.pop()
        if is_debug_level(6):
            _LOGGER.debug("handling event %s", type(event).__name__)
        if isinstance(event, MQTTConnectEvent):
            if event.rc != 0:
                ## MQTT connection error, abort
                _LOGGER.error(event.errmsg)
                return None
            _LOGGER.info("connected to MQTT broker")
            if subscribe_actions(config.actions):
                return True  ## Connect event
            else:
                return None  ## MQTT subscribe error
        elif isinstance(event, MQTTDisconnectEvent):
            if event.rc != 0:
                _LOGGER.error(event.errmsg)
            else:
                _LOGGER.info("disconnected from MQTT broker")
            ## TODO: stop or ignore watchers
            return False  ## Disconnect event
        elif not mqtt_is_connected():
            _LOGGER.warning(
                "not connected to MQTT broker, ignoring event %s", type(event).__name__
            )
        elif isinstance(event, MessageEvent):
            event.action.on_message(event.message)
        elif isinstance(event, CommandEvent):
            event.monitor.process_command(event.com)
        elif isinstance(event, WatcherEvent):
            config.force_check = True
            update_sensors(config, event.sensors)
        else:
            raise RuntimeError(f"Unhandled event: {type(event).__name__}")
    return sleep_interval


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

    while True:
        sleep_start = time.time()
        if is_debug_level(6):
            _LOGGER.debug("sleeping for %ds", sleep_interval)
        SysMonMQ.event.wait(timeout=sleep_interval)
        slept_time = int(time.time() - sleep_start)
        sleep_interval = config.refresh_interval
        if is_debug_level(6):
            _LOGGER.debug("slept for %ds", slept_time)

        with SysMonMQ.lock:
            ## Handle sensor updates
            if mqtt_is_connected():
                sleep_interval = update_sensors(config, config.sensors, slept_time)

            ## Handle event queue
            config.force_check = False
            if SysMonMQ.event.is_set():
                rc = handle_events(config)
                if rc is True:  ## Connect event
                    send_mqtt_discovery(config)  ## will trigger sensor refresh
                    # config.force_check = True
                    # schedule_refresh_all_sensors(config)
                elif rc is False:  ## Disconnect event
                    pass
                elif rc is None:  ## Error
                    if mqtt_is_connected() is None:
                        ## Exit main loop only on initial connection
                        break
                elif not SysMonMQ.events:
                    SysMonMQ.event.clear()

                ## re-run event loop until events are cleared
                sleep_interval = 0

            ## Handle connect timeout and reconnection
            connected = mqtt_is_connected()
            if connected is None:
                ## Timeout on initial connection, exit
                _LOGGER.error("initial connection to MQTT broker timed out")
                break
            elif not connected:
                ## Disconnected state, waiting for reconnection
                _LOGGER.warning("waiting for MQTT broker reconnection")
                sleep_interval = reconnect_delay_max

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
