# sysmonmq

Daemon that monitors status of system metrics, services and containers, and execution of local actions, via MQTT.

## Features

* Send system metric, service and container status updates via MQTT.
* Trigger status checks via file (eg. syslog) or output of command (eg. `docker events`).
* Subscribe to MQTT topics that invoke execution of local actions via scripts or commands.
* Supports customisable sensors that runs a script or command periodically.
* Supports Home Assistant MQTT discovery auto-configuration for configured monitors.

## Configuration

See the sample `sysmonmq.yaml` for a description of the available configuration options.

The `--dump-config` option will also show the full configuration with all inherited attributes.

## Usage

```
usage: sysmonmq [-h] [-d [DEBUG]] [--dump-config] [-c CONFIG] [-v]

optional arguments:
  -h, --help            show this help message and exit
  -d [DEBUG], --debug [DEBUG]
                        set debugging level
  --dump-config         dump full config and exit
  -c CONFIG, --config CONFIG
                        set config file location
  -v, --version         show application version
  ```
