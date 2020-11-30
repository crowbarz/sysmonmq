"""SysMonMQ mqtt functions."""

import logging
import ssl
import paho.mqtt.client as mqtt_client

from .const import APP_NAME
from .config import (
    MQTT_DISCOVERY_OPTS_ALL,
    MQTT_DISCOVERY_OPTS_DEF,
    MQTT_STATUS_OPTS_ALL,
    MQTT_STATUS_OPTS_DEF,
    OPT_DISCOVERY,
    OPT_MQTT,
    OPT_DEBUG,
    OPT_HOST,
    OPT_PORT,
    OPT_CLIENT,
    OPT_CLIENT_ID,
    OPT_KEEPALIVE,
    OPT_CLEAN_SESSION,
    OPT_MQTT_PREFIX,
    OPT_STATUS,
    OPT_TOPIC,
    OPT_PAYLOAD,
    OPT_RETAIN,
    OPT_QOS,
    OPT_RECONNECT_DELAY_MIN,
    OPT_RECONNECT_DELAY_MAX,
    OPT_USERNAME,
    OPT_PASSWORD,
    OPT_ENABLE_SSL,
    OPT_SSL,
    OPT_CAFILE,
    OPT_CERTFILE,
    OPT_KEYFILE,
    OPT_KEYFILE_PASSWORD,
    OPT_TLS_INSECURE,
    OPT_BIRTH,
    OPT_CLOSE,
    OPT_WILL,
    OPT_MQTT_OUTPUT,
    OPT_MQTT_ERROR,
    MQTT_OPTS_ALL,
    MQTT_OPTS_DEF,
    SSL_OPTS_ALL,
    CLIENT_OPTS_ALL,
    BIRTH_OPTS_ALL,
    CLOSE_OPTS_ALL,
    WILL_OPTS_ALL,
    MQTT_ERROR_OPTS_DEF,
    MQTT_ERROR_OPTS_ALL,
    MQTT_OUTPUT_OPTS_DEF,
    MQTT_OUTPUT_OPTS_ALL,
)
from .globals import MQTTConnectEvent, MQTTDisconnectEvent
from .util import check_opts, inherit_opts, merge
from .debug import is_debug_level

_LOGGER = logging.getLogger(APP_NAME)

## Module globals
mqtt_opts = None
client_opts = None
discovery_opts = None
mqttc = None
mqtt_connected = None


# birth_msg = None
# close_msg = None
# will_msg = None


def mqtt_setup(opts, top_opts, config) -> dict:
    """Parse mqtt configuration options."""
    global mqtt_opts, discovery_opts, client_opts  # birth_msg, close_msg, will_msg
    if is_debug_level(7):
        _LOGGER.debug("mqtt_setup(opts=%s)", opts)
    mqtt_opts = MQTT_OPTS_DEF
    err = False

    ## Validate mqtt config
    ssl_section = OPT_MQTT + " > " + OPT_SSL
    client_section = OPT_MQTT + " > " + OPT_CLIENT
    if opts is None:
        opts = {}
    if not check_opts(opts, MQTT_OPTS_ALL, section=OPT_MQTT):
        err = True
    opt_ssl = opts.get(OPT_SSL)
    if opt_ssl is not None:
        if not check_opts(opt_ssl, SSL_OPTS_ALL, section=ssl_section):
            err = True
    opt_client = opts.get(OPT_CLIENT)
    mqtt_output_opts = None
    mqtt_error_opts = None
    if opt_client is None and OPT_CLIENT in opts:
        ## Disable client if null specified for client
        del mqtt_opts[OPT_CLIENT]
    else:
        if opt_client is None:
            opt_client = {}
        if not check_opts(opt_client, CLIENT_OPTS_ALL, section=client_section):
            err = True
        opt_client_birth = opt_client.get(OPT_BIRTH)
        if opt_client_birth is not None:
            if not check_opts(
                opt_client_birth,
                BIRTH_OPTS_ALL,
                section=client_section + " > " + OPT_BIRTH,
            ):
                err = True
        opt_client_close = opt_client.get(OPT_CLOSE)
        if opt_client_close is not None:
            if not check_opts(
                opt_client_close,
                CLOSE_OPTS_ALL,
                section=client_section + " > " + OPT_CLOSE,
            ):
                err = True
        opt_client_will = opt_client.get(OPT_WILL)
        if opt_client_will is not None:
            if not check_opts(
                opt_client_will,
                WILL_OPTS_ALL,
                section=client_section + " > " + OPT_WILL,
            ):
                err = True

        ## Check mqtt_client level mqtt_output and mqtt_error options
        mqtt_output_opts = mqtt_get_output_opts(
            opt_client.get(OPT_MQTT_OUTPUT),
            top_opts[OPT_MQTT_OUTPUT],
            section=client_section,
        )
        mqtt_error_opts = mqtt_get_error_opts(
            opt_client.get(OPT_MQTT_ERROR),
            top_opts[OPT_MQTT_ERROR],
            section=client_section,
        )
        if mqtt_output_opts is None or mqtt_error_opts is None:
            err = True

    opt_discovery = None
    if OPT_DISCOVERY in opts:
        opt_discovery = opts.get(OPT_DISCOVERY)
        if opt_discovery is None:
            opt_discovery = {}
        if not check_opts(
            opt_discovery,
            MQTT_DISCOVERY_OPTS_ALL,
            section=OPT_MQTT + " > " + OPT_DISCOVERY,
        ):
            err = True
    opt_status = None
    if OPT_STATUS in opts:
        opt_status = opts.get(OPT_STATUS)
        if opt_status is None:
            opt_status = {}
        if not check_opts(
            opt_status,
            MQTT_STATUS_OPTS_ALL,
            section=OPT_MQTT + " > " + OPT_STATUS,
        ):
            err = True

    if err:
        return None

    ## Handle client options defaults and inheritance
    ## NOTE: multi-level merge() after check_opts() for all levels
    merge(mqtt_opts, opts)
    if OPT_CLIENT in mqtt_opts:
        client_opts = mqtt_opts[OPT_CLIENT]
        inherit_opts(client_opts, top_opts)
        client_opts[OPT_MQTT_OUTPUT] = mqtt_output_opts
        client_opts[OPT_MQTT_ERROR] = mqtt_error_opts

        ## Handle birth/close/will options defaults and inheritance
        inherit_opts(client_opts[OPT_BIRTH], client_opts)
        inherit_opts(client_opts[OPT_CLOSE], client_opts)
        inherit_opts(client_opts[OPT_WILL], client_opts)

        ## Generate birth, close and will topics
        ## 20201127 DEPRECATED - use client_opts
        # if mqtt_opts[OPT_CLIENT][OPT_BIRTH][OPT_TOPIC]:
        #     birth_msg = mqtt_opts[OPT_CLIENT][OPT_BIRTH]
        # if mqtt_opts[OPT_CLIENT][OPT_CLOSE][OPT_TOPIC]:
        #     close_msg = mqtt_opts[OPT_CLIENT][OPT_CLOSE]
        # if mqtt_opts[OPT_CLIENT][OPT_WILL][OPT_TOPIC]:
        #     will_msg = mqtt_opts[OPT_CLIENT][OPT_WILL]

    ## Handle discovery options and create Action
    if opt_discovery is not None:
        discovery_opts = MQTT_DISCOVERY_OPTS_DEF
        mqtt_opts[OPT_DISCOVERY] = discovery_opts
        merge(discovery_opts, opt_discovery)
    if opt_status is not None:  ## NOTE: status now has defaults
        # status_opts = MQTT_STATUS_OPTS_DEF
        # mqtt_opts[OPT_STATUS] = status_opts
        status_opts = mqtt_opts[OPT_STATUS]
        merge(status_opts, opt_status)

    return mqtt_opts


def mqtt_get_client_opts() -> dict:
    """Get MQTT client opts."""
    return client_opts


def mqtt_get_output_opts(opts, base_opts, section) -> dict:
    """Get MQTT output subsection options."""
    mqtt_output_opts = dict(MQTT_OUTPUT_OPTS_DEF)
    subsection = section + " > " + OPT_MQTT_OUTPUT
    if opts is None:
        opts = {}
    elif not check_opts(opts, MQTT_OUTPUT_OPTS_ALL, section=subsection):
        return None
    merge(mqtt_output_opts, opts)
    if base_opts is not None:
        inherit_opts(mqtt_output_opts, base_opts)
    return mqtt_output_opts


def mqtt_get_error_opts(opts, base_opts, section) -> dict:
    """Get MQTT error subsection options."""
    mqtt_error_opts = dict(MQTT_ERROR_OPTS_DEF)
    subsection = section + " > " + OPT_MQTT_ERROR
    if opts is None:
        opts = {}
    elif not check_opts(opts, MQTT_ERROR_OPTS_ALL, section=subsection):
        return None
    merge(mqtt_error_opts, opts)
    if base_opts is not None:
        inherit_opts(mqtt_error_opts, base_opts)
    return mqtt_error_opts


def mqtt_on_connect(var_mqttc, state, flags, rc):
    """Handle MQTT connection."""
    global mqtt_connected
    if is_debug_level(7):
        _LOGGER.debug(">> mqtt_on_connect(state=%s, flags=%s, rc=%s)", state, flags, rc)
    assert var_mqttc == mqttc
    errmsg = None
    if rc:
        errmsg = "MQTT connect error: " + mqtt_client.connack_string(rc)
    else:
        mqtt_connected = True
    MQTTConnectEvent(mqttc, state, rc, errmsg)
    ## NOTE: publish birth message in main thread (not callback)


def mqtt_on_disconnect(var_mqttc, state, rc):
    """Handle MQTT disconnection."""
    global mqtt_connected
    if is_debug_level(7):
        _LOGGER.debug(">> mqtt_on_disconnect(state=%s, rc=%d)", state, rc)
    assert var_mqttc == mqttc
    errmsg = None
    if rc:
        errmsg = "MQTT connect error: " + mqtt_client.connack_string(rc)
    mqtt_connected = False
    MQTTDisconnectEvent(mqttc, state, rc, errmsg)


def mqtt_is_connected() -> bool:
    """Return state of MQTT connection."""
    return mqtt_connected


def _mqtt_create(config, debug=False) -> mqtt_client.Client:
    """Create MQTT client."""
    global mqttc
    if is_debug_level(7):
        _LOGGER.debug(">> _mqtt_create()")
    assert mqttc is None
    mqttc = mqtt_client.Client(
        client_id=mqtt_opts[OPT_CLIENT_ID],
        clean_session=mqtt_opts[OPT_CLEAN_SESSION],
    )
    ## Set up MQTT client
    mqttc.on_connect = mqtt_on_connect
    mqttc.on_disconnect = mqtt_on_disconnect
    mqttc.reconnect_delay_set(
        min_delay=mqtt_opts[OPT_RECONNECT_DELAY_MIN],
        max_delay=mqtt_opts[OPT_RECONNECT_DELAY_MAX],
    )
    mqtt_username = mqtt_opts[OPT_USERNAME]
    mqtt_password = mqtt_opts[OPT_PASSWORD]
    if mqtt_username is not None and mqtt_password is not None:
        mqttc.username_pw_set(mqtt_username, mqtt_password)

    if mqtt_opts[OPT_ENABLE_SSL]:
        _LOGGER.info("enabling SSL on MQTT connection")
        cafile = mqtt_opts[OPT_SSL][OPT_CAFILE]
        certfile = mqtt_opts[OPT_SSL][OPT_CERTFILE]
        keyfile = mqtt_opts[OPT_SSL][OPT_KEYFILE]
        password = mqtt_opts[OPT_SSL][OPT_KEYFILE_PASSWORD]
        try:
            ssl_context = ssl.create_default_context()
            if cafile:
                ssl_context.load_verify_locations(cafile=cafile)
            if certfile:
                ssl_context.load_cert_chain(
                    certfile=certfile, keyfile=keyfile, password=password
                )
            mqttc.tls_set_context(ssl_context)
        except Exception as e:
            _LOGGER.error("could not create SSL context: %s", e)
        if mqtt_opts[OPT_SSL][OPT_TLS_INSECURE]:
            mqttc.tls_insecure_set(True)

    if debug or mqtt_opts[OPT_DEBUG]:
        _LOGGER.info("enabling MQTT client debugging")
        mqttc.enable_logger()
    return mqttc


def mqtt_connect(config, debug=False) -> mqtt_client.Client:
    """Connect to the MQTT broker."""
    global mqttc
    if is_debug_level(7):
        _LOGGER.debug(">> mqtt_connect()")
    assert mqttc is None

    ## Create MQTT client
    if _mqtt_create(config, debug) is None:
        return None
    host = mqtt_opts[OPT_HOST]
    port = mqtt_opts[OPT_PORT]

    ## Set client will message
    if client_opts is not None:
        will_msg = client_opts[OPT_WILL]
        will_topic = will_msg[OPT_TOPIC]
        if will_msg and will_topic:
            topic = mqtt_get_topic(will_topic, will_msg[OPT_MQTT_PREFIX])
            payload = will_msg[OPT_PAYLOAD]
            if is_debug_level(7):
                _LOGGER.debug(
                    'registering will message "%s": "%s"',
                    topic,
                    payload,
                )
            mqttc.will_set(
                topic, payload, qos=will_msg[OPT_QOS], retain=will_msg[OPT_RETAIN]
            )

    _LOGGER.info("connecting to MQTT broker %s:%d", host, port)
    mqttc.connect_async(host=host, port=port, keepalive=mqtt_opts[OPT_KEEPALIVE])
    mqttc.loop_start()
    return mqttc


def mqtt_close():
    """Close the MQTT connection."""
    global mqttc
    if is_debug_level(7):
        _LOGGER.debug(">> mqtt_close()")
    if not mqttc:
        return

    ## Publish client close message
    if client_opts:
        close_msg = client_opts[OPT_CLOSE]
        close_topic = close_msg[OPT_TOPIC]
        if close_msg and close_topic:
            mqtt_publish(
                topic=mqtt_get_topic(close_topic, close_msg[OPT_MQTT_PREFIX]),
                payload=close_msg[OPT_PAYLOAD],
                qos=close_msg[OPT_QOS],
                retain=close_msg[OPT_RETAIN],
            )

    ## Disconnect from MQTT server
    _LOGGER.info("disconnecting from MQTT server")
    mqttc.loop_stop()
    mqttc.disconnect()
    mqttc.loop_forever()  ## wait for disconnect to complete
    if is_debug_level(7):
        _LOGGER.debug("disconnected from MQTT server")
    mqttc = None


def mqtt_get_topic(
    topic, prefix, topic_prefix=None, type_prefix=None, type_suffix=None
) -> str:
    """Generate MQTT topic from components."""
    return (
        ((prefix + "/") if prefix else "")
        + ((type_prefix + "/") if type_prefix else "")
        + ((topic_prefix + "/") if topic_prefix else "")
        + topic
        + (("/" + type_suffix) if type_suffix else "")
    )


def mqtt_publish(topic, payload, qos, retain):
    """Publish a message to the MQTT server and wait for publish."""
    if is_debug_level(7):
        _LOGGER.debug('publishing to MQTT: "%s": "%s"', topic, payload)
    assert mqttc is not None

    msgInfo = mqttc.publish(topic, payload, qos, retain)
    if msgInfo.rc == mqtt_client.MQTT_ERR_SUCCESS:
        ## NOTE: don't block on publish - queue if disconnected
        # msgInfo.wait_for_publish()
        pass
    else:
        _LOGGER.error("could not publish MQTT message: %d", msgInfo.rc)


def mqtt_message_callback_add(sub, callback):
    """Set callback for subscription."""
    assert mqttc is not None

    mqttc.message_callback_add(sub, callback)


def mqtt_subscribe(subs) -> bool:
    """Subscribe to list of subscriptions."""
    assert mqttc is not None

    (rc, _) = mqttc.subscribe(subs)
    return True if rc == mqtt_client.MQTT_ERR_SUCCESS else False
