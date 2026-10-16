"""Subprocess ownership, complete pipe draining and cooperative cancellation."""
from contextlib import contextmanager
import os
import queue
import signal
import subprocess
import threading
import time

_context = threading.local()


@contextmanager
def cancellation_scope(event):
    previous = getattr(_context, "cancel", None)
    _context.cancel = event
    try:
        yield
    finally:
        _context.cancel = previous


class _WindowsJob:
    """Own descendants even if their parent exits before cancellation."""
    def __init__(self, process):
        import win32api
        import win32job
        self.api, self.job_api = win32api, win32job
        self.handle = win32job.CreateJobObject(None, None)
        try:
            info = win32job.QueryInformationJobObject(
                self.handle, win32job.JobObjectExtendedLimitInformation
            )
            info["BasicLimitInformation"]["LimitFlags"] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(
                self.handle, win32job.JobObjectExtendedLimitInformation, info
            )
            win32job.AssignProcessToJobObject(self.handle, int(process._handle))
        except Exception:
            self.close()
            raise

    def terminate(self):
        self.job_api.TerminateJobObject(self.handle, 1)

    def close(self):
        if self.handle is not None:
            self.api.CloseHandle(self.handle)
            self.handle = None


def _terminate_tree(process, job=None):
    if job is not None:
        job.terminate()
    elif os.name == "nt":
        # The handle stays owned until wait(), so this PID cannot be recycled.
        result = subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=15,
        )
        if result.returncode and process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait()


def run_process(args, *, callback=None, timeout=None, cancel=None, **kwargs):
    """Return (all stdout bytes, exit code); cancellation/timeout returns code 1.

    A reader drains to EOF independently of the deadline loop. Every child is
    waited on, including callback errors and cancellation. A cancelled worker
    cannot spawn another child on its next loop iteration.
    """
    cancel = cancel if cancel is not None else getattr(_context, "cancel", None)
    if cancel is not None and cancel.is_set():
        return b"", 1
    if os.name == "nt":
        kwargs.setdefault("creationflags", subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        kwargs.setdefault("start_new_session", True)
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
    job = None
    if os.name == "nt":
        try:
            job = _WindowsJob(process)
        except Exception:
            # An immediately completed child needs no assignment. If a live
            # child cannot be contained, fail closed instead of running unowned.
            if process.poll() is None:
                _terminate_tree(process)
                process.stdout.close()
                raise
    events = queue.Queue()

    def read():
        try:
            for line in iter(process.stdout.readline, b""):
                events.put(line)
        finally:
            events.put(None)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    deadline = None if timeout is None else time.monotonic() + timeout
    output, stopped, eof = [], False, False
    try:
        while not eof or process.poll() is None:
            if not stopped and (
                (cancel is not None and cancel.is_set())
                or (deadline is not None and time.monotonic() >= deadline)
            ):
                _terminate_tree(process, job)
                stopped = True
            try:
                line = events.get(timeout=0.05)
            except queue.Empty:
                continue
            if line is None:
                eof = True
            else:
                output.append(line)
                if callback is not None:
                    callback(line)
        code = process.wait()
        return b"".join(output), 1 if stopped else code
    except BaseException:
        _terminate_tree(process, job)
        raise
    finally:
        if job is not None:
            job.close()
        reader.join()
        process.stdout.close()
