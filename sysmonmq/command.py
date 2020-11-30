"""SysMonMQ asynchronous command execution."""

import logging
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor

from .globals import CommandEvent
from .const import (
    APP_NAME,
    DEF_COMMAND_TIMEOUT,
    DEF_THREAD_MAX_WORKERS,
    DEF_THREAD_POOL_PREFIX,
)
from .debug import is_debug_level

_LOGGER = logging.getLogger(APP_NAME)


class Command:
    """Execute commands in a ThreadPoolExecutor."""

    threadpool = ThreadPoolExecutor(
        max_workers=DEF_THREAD_MAX_WORKERS, thread_name_prefix=DEF_THREAD_POOL_PREFIX
    )

    def __init__(self, monitor, command, timeout=DEF_COMMAND_TIMEOUT, ignore_rc=False):
        self.monitor = monitor
        self.command = command
        self.timeout = timeout
        self.ignore_rc = ignore_rc
        self.output = ""
        self.err_msg = None
        self.rc = 0
        self.future = self.threadpool.submit(self.run)

    # def __del__(self):
    #     if is_debug_level(5):
    #         _LOGGER.debug('deleting Command(command="%s)', self.command)
    #     # del self.thread

    def run(self):
        """Function to be run in a separate thread."""
        if is_debug_level(5):
            _LOGGER.debug('executing Command(command="%s")', self.command)
        try:
            self.output = str(
                subprocess.run(
                    shlex.split(self.command),
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=self.timeout,
                ).stdout,
                encoding="utf-8",
                errors="ignore",
            ).strip()
        except subprocess.CalledProcessError as e:
            self.output = str(e.output, encoding="utf-8", errors="ignore").strip()
            self.rc = e.returncode
            if not self.ignore_rc:
                self.err_msg = f'command "{self.command}" returned code ' f"{self.rc}"
        except subprocess.TimeoutExpired as e:
            self.rc = 254
            self.err_msg = 'execution of command "%s" exceeded timeout %ds' % (
                self.command,
                self.timeout,
            )
        except Exception as e:
            self.rc = 255
            self.err_msg = f'error executing command "{self.command}": {e}'
        finally:
            if is_debug_level(5):
                _LOGGER.debug(
                    'Command(command="%s"): output="%s", rc=%d, err_msg="%s"',
                    self.command,
                    self.output,
                    self.rc,
                    self.err_msg,
                )
            CommandEvent(self, self.monitor)
