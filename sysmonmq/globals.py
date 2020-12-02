"""SysMonMQ global classes."""

import logging
import socket
import subprocess
from threading import Lock, Event
from abc import ABC

from .const import APP_NAME, DEF_MQTT_RECONNECT_DELAY_MIN, DEF_MQTT_RECONNECT_DELAY_MAX

_LOGGER = logging.getLogger(APP_NAME)

## Globals class
class SysMonMQ:
    """SysMon global class."""

    lock = Lock()
    event = Event()
    events = []

    def __init__(self):
        self.hostname = socket.gethostname().split(".")[0]
        self.system_hardware = (
            subprocess.run(["uname", "-m"], capture_output=True)
            .stdout.rstrip()
            .decode(errors="ignore")
        )
        self.system_os = (
            subprocess.run(["uname", "-s"], capture_output=True)
            .stdout.rstrip()
            .decode(errors="ignore")
        )
        self.system_version = (
            subprocess.run(["uname", "-v"], capture_output=True)
            .stdout.rstrip()
            .decode(errors="ignore")
        )
        self.mqtt_prefix = None

        ## Monitors
        self.sensors = []
        self.actions = []
        self.watchers = []

        ## Globals
        self.opts = None  ## top level options
        self.discovery_opts = None  ## top level MQTT discovery options
        self.refresh_interval = None  ## global refresh interval
        self.force_check = False  ## force check on next refresh
        self.mqtt_debug = False  ## Enable MQTT debugging


## Event classes
class Event(ABC):
    def __init__(self):
        with SysMonMQ.lock:
            SysMonMQ.events.append(self)
            SysMonMQ.event.set()


class MQTTEvent(Event):
    def __init__(self, mqttc, state, rc, errmsg):
        self.mqttc = mqttc
        self.state = state
        self.rc = rc
        self.errmsg = errmsg
        super().__init__()


class MQTTConnectEvent(MQTTEvent):
    pass


class MQTTDisconnectEvent(MQTTEvent):
    pass


class MessageEvent(Event):
    def __init__(self, action, message):
        self.action = action
        self.message = message
        super().__init__()


class CommandEvent(Event):
    def __init__(self, com, monitor):
        self.com = com
        self.monitor = monitor
        super().__init__()


class WatcherEvent(Event):
    def __init__(self, watcher, sensors):
        self.watcher = watcher
        self.sensors = sensors
        super().__init__()
