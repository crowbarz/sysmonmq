"""SysMonMQ file watchers."""

import logging
import traceback
import time
import shlex
import subprocess
from pathlib import Path
from threading import Lock, Thread, Timer, main_thread
from abc import ABC
import inotify_simple as inotify

from .globals import WatcherEvent
from .const import (
    APP_NAME,
    DEF_COMMAND_TIMEOUT,
    DEF_INOTIFY_FLAGS,
    DEF_INOTIFY_FLAGS_PARENT,
    DEF_INOTIFY_FLAGS_RESTART,
    DEF_INOTIFY_FLAGS_UPDATE,
)
from .config import (
    OPT_COMMANDS,
    OPT_FILES,
    OPT_KEYWORDS,
    OPT_RESTART_DELAY,
    OPT_TRIGGER_DELAY,
    OPT_WATCHERS,
    WATCHERS_OPTS_ALL,
    WATCHERS_OPTS_DEF,
)
from .mqtt import mqtt_is_connected
from .util import checkOptions, check_opts, merge
from .debug import is_debug_level

_LOGGER = logging.getLogger(APP_NAME)


class Watcher(ABC):
    """Watch sensor update triggers asynchronusly and trigger updates. """

    def __init__(self, opts, sensors=[], thread_id=None):
        if is_debug_level(5):
            _LOGGER.debug(">> %s.__init__(opts=%s)", type(self).__name__, opts)
        self.trigger_delay = opts[OPT_TRIGGER_DELAY]
        self.restart_delay = opts[OPT_RESTART_DELAY]
        self.sensors = sensors
        self.thread = None
        if sensors:
            self.thread = Thread(target=self.run, daemon=True)
            if thread_id:
                self.thread.name = type(self).__name__ + "_" + str(thread_id)
            self.thread.start()
        else:
            _LOGGER.error("no sensors to watch, Watcher thread not started")

    def trigger_update(self):
        """Trigger sensor update in main loop."""
        if mqtt_is_connected():
            WatcherEvent(self, self.sensors)

    def stop(self):
        """Stop a Watcher thread."""
        if is_debug_level(5):
            _LOGGER.debug("stopping Watcher()")
        # TODO: figure out how to do this

    def setup(self, *args) -> None:
        raise RuntimeError(
            f"Stub Watcher.setup() called for {type(self).__name__} object"
        )

    def cleanup(self, *args) -> None:
        raise RuntimeError(
            f"Stub Watcher.cleanup() called for {type(self).__name__} object"
        )

    def main_loop(self, *args) -> None:
        raise RuntimeError(
            f"Stub Watcher.main_loop() called for {type(self).__name__} object"
        )

    def run(self):
        """Set up watcher and run main loop."""
        try:
            self.setup()
        except Exception as e:
            _LOGGER.error("Watcher.setup() exception: %s", e)
            if is_debug_level(5):
                traceback.print_exc()
            return

        while True:
            try:
                rc = self.main_loop()
                if is_debug_level(5):
                    _LOGGER.debug("%s.main_loop() = %d", type(self).__name__, rc)
                if rc:
                    continue
            except Exception as e:
                _LOGGER.error("Watcher.run() exception: %s", e)
                if is_debug_level(5):
                    traceback.print_exc()
            if is_debug_level(5):
                _LOGGER.warning(
                    "main loop exited, restarting after %ds delay", self.restart_delay
                )
            self.cleanup()
            time.sleep(self.restart_delay)
            ## NOTE: restart will miss subsequent events within
            ## DEF_WATCHER_READ_DELAY of the event that triggered restart
            ## as well as the delay above, so need to trigger update
            self.setup()
            self.trigger_update()


class FileWatcher(Watcher):
    """Watch files and trigger sensor updates."""

    thread_id = 1

    def __init__(self, files, opts, sensors=[]):
        self.filenames = files
        if type(self.filenames) == str:
            self.filenames = [self.filenames]
        self.keywords = opts.get(OPT_KEYWORDS, None)
        super().__init__(opts, sensors, thread_id=FileWatcher.thread_id)
        FileWatcher.thread_id += 1

    def setup(self):
        """Set up inotify notifier and open files."""
        if is_debug_level(5):
            _LOGGER.debug(">> FileWatcher.setup(filenames=%s)", self.filenames)
        self.inotify = inotify.INotify()
        self.wds = {}
        self.paths = []
        for filename in self.filenames:
            wd = None
            f = None
            path = Path(filename).resolve(strict=False)
            path_str = str(path)

            ## Skip path
            if path_str in self.paths:
                _LOGGER.info('path "%s" already watched, skipping', path)
                continue

            ## Open file for reading and watch if readable
            try:
                f = path.open()
                f.seek(0, 2)  ## EOF
            except Exception as e:
                _LOGGER.error('could not read path "%s": %s', path, e)
            else:
                try:
                    wd = self.inotify.add_watch(path, DEF_INOTIFY_FLAGS)
                except Exception as e:
                    _LOGGER.error('could not watch path "%s": %s', path, e)
                if wd:
                    if is_debug_level(5):
                        _LOGGER.debug(
                            ('watching path "%s"' % path)
                            + (
                                (" with keywords=%s" % self.keywords)
                                if self.keywords
                                else ""
                            )
                        )
                    self.wds[wd] = (path, f)
                    self.paths.append(path_str)
                    continue

            ## Otherwise watch parent directory
            parent = path.parent
            parent_str = str(parent)
            if str(path.parent) in self.paths:
                _LOGGER.info('dir "%s" already watched, skipping', parent)
                continue
            try:
                wd_parent = self.inotify.add_watch(parent, DEF_INOTIFY_FLAGS_PARENT)
                if wd_parent:
                    if is_debug_level(5):
                        _LOGGER.debug('watching parent dir "%s"', parent_str)
                    self.wds[wd_parent] = (parent, None)
                    self.paths.append(parent_str)

            except Exception as e:
                _LOGGER.error("could not watch %s: %s", parent_str, e)
                if is_debug_level(5):
                    traceback.print_exc()

    def cleanup(self):
        """Close notifier and files."""
        if is_debug_level(5):
            _LOGGER.debug("FileWatcher.cleanup(filenames=%s)", self.filenames)
        if self.inotify:
            for wd in self.wds:
                (filename, f) = self.wds[wd]
                try:
                    f.close()
                except:
                    pass

            self.inotify.close()
            del self.inotify
            self.inotify = None
        self.wds = {}
        self.paths = []

    def main_loop(self):
        """Monitor inotify and signal when updates detected."""
        events = self.inotify.read(read_delay=self.trigger_delay * 1000)
        update = False
        restart = False
        trigger_filenames = []
        for event in events:
            (wd, mask, cookie, name) = event
            if is_debug_level(5):
                flags = ""
                separator = ""
                for flag in inotify.flags.from_mask(mask):
                    flags += separator + str(flag)
                    separator = ", "
                _LOGGER.debug("Event(%s, [%s], %s, %s", wd, flags, cookie, name)
            (filename, f) = self.wds[wd]
            if mask & DEF_INOTIFY_FLAGS_UPDATE:
                if self.keywords:
                    line = f.readline()
                    while line:
                        line = line.rstrip()
                        if is_debug_level(5):
                            _LOGGER.debug('%s: read "%s"', filename, line)
                        if any(k in line for k in self.keywords):
                            update = True
                            if filename not in trigger_filenames:
                                trigger_filenames.append(filename)
                        line = f.readline()
                else:
                    update = True
            if mask & DEF_INOTIFY_FLAGS_RESTART:
                ## Trigger update for restart flags as well
                update = True
                restart = True
        if update:
            _LOGGER.debug("triggering update")
            self.trigger_update()
        return True if not restart else False


class CommandWatcher(Watcher):
    """Watch output of command and trigger sensor updates."""

    thread_id = 1

    def __init__(self, command, opts, sensors=[]):
        self.command = command
        self.keywords = opts.get(OPT_KEYWORDS, [])
        self.lock = Lock()
        self.timer = None
        self.proc = None
        super().__init__(opts, sensors, thread_id=CommandWatcher.thread_id)
        CommandWatcher.thread_id += 1

    def setup(self):
        """Run command and set up pipe."""
        if is_debug_level(5):
            _LOGGER.debug(">> CommandWatcher.setup(command=%s)", self.command)
        self.proc = subprocess.Popen(
            shlex.split(self.command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )

    def cleanup(self):
        if is_debug_level(5):
            _LOGGER.debug(">> CommandWatcher.cleanup(command=%s)", self.command)
        with self.lock:
            if self.timer:
                self.timer.cancel()
                self.timer = None
        while self.proc.poll() is None:
            if is_debug_level(5):
                _LOGGER.debug("terminating child process")
            self.proc.terminate()
            try:
                self.proc.wait(timeout=DEF_COMMAND_TIMEOUT)
            except subprocess.TimeoutExpired:
                if is_debug_level(5):
                    _LOGGER.debug("killing child process")
                self.proc.kill()
                time.sleep(1)
        self.proc = None

    def delayed_update(self):
        _LOGGER.debug("triggering delayed update")
        self.trigger_update()
        self.timer = None

    def main_loop(self):
        """Monitor output of command and signal when updates detected."""
        if self.proc is None or self.proc.poll() is not None:
            return False

        update = False
        line = self.proc.stdout.readline()
        while line:
            line = line.rstrip()
            if is_debug_level(5):
                _LOGGER.debug('read "%s"', line)
            if self.keywords:
                if any(k in line for k in self.keywords):
                    update = True
            else:
                update = True
            with self.lock:
                if update and not self.timer:
                    self.timer = Timer(self.trigger_delay, self.delayed_update)
                    self.timer.name = self.thread.name + "_Timer"
                    self.timer.start()
            line = self.proc.stdout.readline()
        return True


def get_watchers_opts(opts, sensors, section):  # -> watchers|None
    """Get watchers section options."""
    if is_debug_level(5):
        _LOGGER.debug(">> get_watchers_opts(opts=%s, section=%s)", opts, section)
    err = False
    watcher_objs = []
    watchers_opts = dict(WATCHERS_OPTS_DEF)
    subsection = section + " > " + OPT_WATCHERS

    if opts is None or sensors is None:
        return (watcher_objs, watchers_opts)
    elif not check_opts(opts, WATCHERS_OPTS_ALL, section=subsection):
        return (None, None)
    merge(watchers_opts, opts)

    files = watchers_opts.get(OPT_FILES)
    if not err and files:
        ## one FileWatcher for all files
        file_watcher = FileWatcher(files, watchers_opts, sensors)
        if file_watcher:
            watcher_objs.append(file_watcher)
        else:
            err = True
    commands = watchers_opts[OPT_COMMANDS]
    if not err and commands:
        if type(commands) == str:
            commands = [commands]
        for command in commands:  ## separate CommandWatcher for each command
            command_watcher = CommandWatcher(command, watchers_opts, sensors)
            if command_watcher:
                watcher_objs.append(command_watcher)
            else:
                err = True
    return (watcher_objs, watchers_opts) if not err else (None, None)
