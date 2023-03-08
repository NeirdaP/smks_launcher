import functools
import subprocess
import threading
import time
from queue import Queue, Empty

from qtpy import QtCore

_LOCK = False


class ProcessWatcher(QtCore.QObject):

    def __init__(
            self, process, window=None, timeout=-1,
            end_callback=None, watch_timeout=-1
    ):
        super(ProcessWatcher, self).__init__(window)
        self._process = process
        self._window = window
        self._timeout = timeout
        self._watch_timeout = watch_timeout
        self._end_callback = end_callback
        self._ended = False

        self._reader = None
        self._read_queue = Queue()

        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)

        self._start_time = 0
        self._end_time = 0

    def handle_process_output(self):
        import time
        import random

        global _LOCK

        while _LOCK:
            time.sleep(0.1)
        _LOCK = True

        lines = []

        while True:
            try:
                line = self._read_queue.get_nowait()  # or q.get(timeout=.1)
            except Empty:
                break
            lines.append(line)
            time.sleep(0.01)

        if self._window:
            for line in lines:
                low_line = line.lower()
                if 'error' in low_line or ' end' in low_line or random.randint(0, 2) == 0:
                    self._window.showMessage(line)
                else:
                    print(line)
        _LOCK = False

    def _end(self):
        self._ended = True
        self._timer.stop()
        self._timer.deleteLater()
        self.deleteLater()

    def _handle_os_error(self):
        import time
        print("Cannot fetch outputs of process {}".format(self._process))
        while self._process and self._process.poll() is None:
            if (time.time() - self._start_time) > self._watch_timeout > 0:
                break
            if (time.time() - self._start_time) > self._timeout > 0:
                raise RuntimeError('Timeout reached: process aborted')
        self._end()
        return self._process.returncode or -1

    def _handle_process_error(self):
        import traceback
        traceback.print_exc()
        self._process.poll()
        if self._process and self._process.returncode is None:
            try:
                self._process.terminate()
            except OSError:
                pass
        print("Ended with status {}".format(self._process.returncode))
        self._end()
        return self._process.returncode or -1

    def _handle_process_unfinished(self):
        print("Watch is ending before the process end")

        self._process.poll()
        if self._end_callback is not None:
            try:
                self._end_callback(self._process.returncode)
            except TypeError as e:
                print(e)
                self._end_callback()
        self._end()
        return self._process.returncode

    def _handle_process_normal_end(self):
        self.handle_process_output()
        out, err = self._process.communicate()
        if out:
            out = out.decode("latin-1")
            if self._window and out:
                self._window.showMessage(out)
        if out or err:
            print(out, err)
        print("Ended with status {}".format(self._process.returncode))

        if self._end_callback is not None:
            try:
                self._end_callback(self._process.returncode)
            except TypeError as e:
                print(e)
                self._end_callback()
        self._end()
        return self._process.returncode

    def watch_process(self):
        import time

        if not self._process:
            raise RuntimeError("Process to watch does not exist !")

        try:
            if self._process.poll() is None:
                if (time.time() - self._start_time) > self._watch_timeout > 0:
                    return self._handle_process_unfinished()
                if (time.time() - self._start_time) > self._timeout > 0:
                    raise RuntimeError('Timeout reached: process aborted')
                self.handle_process_output()
        except OSError:
            return self._handle_os_error()
        except (IOError, RuntimeError):
            return self._handle_process_error()

        if self._process.returncode is not None:
            return self._handle_process_normal_end()

        self._timer.start(500)
        return None

    def _read(self):
        while True:
            time.sleep(0.1)
            for stream in [self._process.stderr, self._process.stdout]:
                if not stream:
                    continue

                try:
                    line = stream.readline()
                except ValueError:  # closed file
                    return
                while line:
                    try:
                        line = line[:-1].decode("latin-1")
                    except ValueError:
                        line = "\n"
                    self._read_queue.put(line)
                    if self._process.poll() is not None:
                        return
                    try:
                        line = stream.readline()
                    except ValueError:  # closed file
                        return
                    time.sleep(0.06)

    def run(self):
        import time
        self._start_time = time.time()

        self._reader = Thread(target=self._read)
        self._reader.finished.connect(self._reader.deleteLater)
        self._reader.start()

        self._timer.timeout.connect(self.watch_process)
        self._timer.start(30)

    def start(self):
        self.run()

    def wait(self):
        while self.is_alive():
            time.sleep(0.01)

    def join(self):  # alias
        self.wait()

    def is_alive(self):
        return not self._ended


class ProcessAgent(object):
    _processes = []  # type: list[subprocess.Popen]
    _processes_pools = dict()  # type: dict[int, list[ProcessAgent]]
    _threads = []  # type: list[threading.Thread]
    _count = 0

    def __init__(self, command, kwargs, timeout=-1, end_callback=None,
                 watch_timeout=-1, pool=0):
        super().__init__()
        self.command = command
        self.kwargs = kwargs
        self.timeout = timeout
        self.watch_timeout = watch_timeout
        self.end_callback = end_callback
        self.pool = pool
        self.process = None
        self.watcher = None
        self._id = self.__class__._count

    @classmethod
    def wait_for_remaining_processes(cls):
        for process in cls._processes:
            process.wait()
        for process in cls._threads:
            process.join()

    @classmethod
    def register_thread(cls, thread):
        cls._threads.append(thread)

    @classmethod
    def processes_are_running(cls):
        for process in cls._processes:
            process.poll()

        cls._processes = [process for process in cls._processes if process.returncode is None]
        cls._threads = [thread for thread in cls._threads if thread.is_alive()]

        return any(cls._processes) or any(cls._threads)

    @classmethod
    def watch_process(
        cls, process, end_callback=None, timeout=-1, window=None,
        watch_timeout=-1
    ):
        watcher = ProcessWatcher(
            process, window=window, end_callback=end_callback,
            timeout=timeout, watch_timeout=watch_timeout
        )
        watcher.start()

        cls._processes.append(process)
        cls._threads.append(watcher)
        return watcher

    @classmethod
    def process_end_callback(cls, process_agent, window, return_code):
        """
        :param ProcessAgent process_agent:
        :param QWidget window:
        """
        if process_agent.end_callback:
            process_agent.end_callback(return_code)
        try:
            cls._processes_pools[process_agent.pool].remove(process_agent)
        except ValueError:
            return
        if cls._processes_pools[process_agent.pool]:
            new_process = cls._processes_pools[process_agent.pool].pop(0)
            end_callback = functools.partial(cls.process_end_callback, new_process, window)
            new_process.process = subprocess.Popen(new_process.command, **new_process.kwargs)
            new_process.watcher = new_process.__class__.watch_process(
                new_process.process, end_callback=end_callback,
                window=window, timeout=new_process.timeout
            )

    def run_process(self, window=None, end_callback=None):
        if end_callback:
            self.end_callback = end_callback
        if self.pool:
            if self.pool not in self._processes_pools:
                self._processes_pools[self.pool] = [self]
                end_callback = functools.partial(self.process_end_callback, self, window)
            else:
                self._processes_pools[self.pool].append(self)
                return
        self.process = subprocess.Popen(self.command, **self.kwargs)
        self.watcher = self.__class__.watch_process(
            self.process, end_callback=end_callback, window=window,
            timeout=self.timeout, watch_timeout=self.watch_timeout
        )

    def __hash__(self):
        return self._id

    def __eq__(self, other):
        return self._id == other._id


class Thread(QtCore.QThread):

    def __init__(self, target=None, args=None, kwargs=None):
        super(Thread, self).__init__()
        self.target = target
        self._args = args or []
        self._kwargs = kwargs or dict()
        self._ended = False

    def deleteLater(self):
        super().deleteLater()

    def run(self):
        try:
            import pydevd
        except ImportError:
            pass
        else:
            pydevd.settrace(suspend=False, trace_only_current_thread=True)

        self.target(*self._args, **self._kwargs)
        self._ended = True
        self.exec_()

    def is_alive(self):
        return self.isRunning() and not self._ended
