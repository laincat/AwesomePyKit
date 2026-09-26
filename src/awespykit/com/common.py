# coding: utf-8

from typing import *

from fastpip import PyEnv
from PyQt5.QtCore import *

EMPTY_STR = ""


class VerInfo:
    """包装 PyInstaller 版本号的类"""

    defver = "0.0.0"

    def __init__(self, ver=defver):
        assert isinstance(ver, str)
        self.__ver = ver

    def __repr__(self):
        if not self.__ver:
            return self.defver
        return self.__ver

    __str__ = __repr__

    def is_null(self):
        return self.__ver == self.defver

    def set(self, ver: str):
        assert isinstance(ver, str)
        if ver:
            self.__ver = ver
        else:
            self.__ver = self.defver
        return self.__ver


class QThreadModel(QThread):
    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs
        self.__at_start = list()
        self.__at_finish = list()

    def run(self):
        self.__target(*self.__args, **self.__kwargs)

    def __repr__(self):
        return (
            f"{self.__target} with args: {self.__args}, kwargs: {self.__kwargs}"
        )

    __str__ = __repr__

    def before_starting(self, *callable_objs):
        for cab in callable_objs:
            self.started.connect(cab)
        self.__at_start.extend(callable_objs)

    def after_completion(self, *callable_objs):
        for cab in callable_objs:
            self.finished.connect(cab)
        self.__at_finish.extend(callable_objs)

    def no_signal(self):
        for cab in self.__at_start:
            self.started.disconnect(cab)
        for cab in self.__at_finish:
            self.finished.disconnect(cab)


class ThreadRepo:
    def __init__(self, interval):
        """interval: 清理已结束线程的时间间隔，单位毫秒。"""
        self._thread_repo = []
        self._timer_clths = QTimer()
        self._mutex = QMutex()
        self._timer_clths.timeout.connect(self.clean)
        self._timer_clths.start(interval)
        self._flag_cleaning = False

    def put(self, threadhandle, level=0):
        """将(线程句柄、重要等级)元组加入线程仓库。"""
        self._mutex.lock()
        self._thread_repo.append((threadhandle, level))
        self._mutex.unlock()

    def clean(self):
        """清除已结束的线程。"""
        if self._flag_cleaning:
            return
        self._mutex.lock()
        index = 0
        self._flag_cleaning = True
        while index < len(self._thread_repo):
            if self._thread_repo[index][0].isRunning():
                index += 1
                continue
            del self._thread_repo[index]
        self._flag_cleaning = False
        self._mutex.unlock()

    def stop_all(self):
        """请求停止所有线程；返回 True 表示全部已确认停止。"""
        # 请求停止所有线程，并返回「是否真的停下来了」。
        #
        # 这里有个必须说清楚的事实：quit() 只能停掉「跑着 Qt 事件循环」的线程。
        # 而本程序里的工作线程都是 QThreadModel(一个普通函数)，run() 直接执行
        # 函数体、从不调用 exec()，所以 quit() 对它们**没有任何效果**。
        #
        # 后果不是小问题：界面文案写着「已停止」，用户便会放心强退程序，
        # 而此时 pip 可能正处在安装/卸载的关键步骤上，中断会留下装了一半的包、
        # 损坏的环境。因此对等级 0（重要）的线程同样使用 terminate()，
        # 并且把真实结果如实报告给调用方，让界面能提示用户等待。
        #
        # 等级约定：0 重要、1 不重要、其它未知（一律按重要处理）。
        stopped_all = True
        for thread, level in list(self._thread_repo):
            thread.no_signal()
            if level == 1:
                thread.terminate()
            else:
                # 先给线程一个自行退出的机会（若它内部监听取消标志），
                # 再强制终止；terminate() 之后必须 wait()，否则线程可能
                # 在后续代码里继续访问已经失效的对象。
                thread.quit()
                if not thread.wait(200):
                    thread.terminate()
                    thread.wait(2000)
            if thread.isRunning():
                stopped_all = False
        return stopped_all

    def kill_all(self):
        """立即终止所有线程。"""
        # 立即强制终止所有线程（用于「强制退出」这类用户明确要求立刻结束的场景）。
        # terminate() 之后等待线程真正结束，避免它在窗口销毁后还去触碰界面对象。
        for thread, _ in list(self._thread_repo):
            thread.no_signal()
            thread.terminate()
            thread.wait(2000)

    def is_empty(self):
        """返回线程仓库是否为空。"""
        return not self._thread_repo


class EnvDisplayPair(QObject):
    __signal_setinfo = pyqtSignal([str], [int, str])

    def __init__(self, environ: PyEnv):
        super().__init__()
        self.__environ = environ
        self.__i = None
        self.__discard = False
        self.__thread: Union[QThreadModel, None] = None
        self.__display = None
        self.__mutex = QMutex()

    def signal_connect(self, callback, index=None, clean=True):
        self.__i = index
        if clean:
            if index is None:
                if self.receivers(self.__signal_setinfo[str]):
                    self.__signal_setinfo[str].disconnect()
            else:
                if self.receivers(self.__signal_setinfo[int, str]):
                    self.__signal_setinfo[int, str].disconnect()
        if index is None:
            self.__signal_setinfo[str].connect(callback)
        else:
            self.__signal_setinfo[int, str].connect(callback)

    def disconnect_all(self):
        if self.receivers(self.__signal_setinfo[str]):
            self.__signal_setinfo[str].disconnect()
        if self.receivers(self.__signal_setinfo[int, str]):
            self.__signal_setinfo[int, str].disconnect()

    def disconnect_1(self, callback):
        self.__signal_setinfo[str].disconnect(callback)

    def disconnect_2(self, callback):
        self.__signal_setinfo[int, str].disconnect(callback)

    def discard(self):
        self.__mutex.lock()
        self.__discard = True
        if self.__thread is not None and self.__thread.isRunning():
            self.__thread.terminate()
        self.__mutex.unlock()

    def load_real_display(self):
        self.__mutex.lock()
        current_display_name = self.__display
        self.__mutex.unlock()
        if current_display_name is not None:
            return current_display_name

        def load_display_name():
            __display = str(self.__environ)
            self.__mutex.lock()
            self.__display = __display
            if not self.__discard:
                if self.__i is None:
                    self.__signal_setinfo[str].emit(__display)
                else:
                    self.__signal_setinfo[int, str].emit(self.__i, __display)
            self.__mutex.unlock()

        self.__mutex.lock()
        if not self.__discard:
            self.__thread = QThreadModel(load_display_name)
            self.__thread.start()
        self.__mutex.unlock()

    @property
    def display(self):
        self.__mutex.lock()
        __display = self.__display
        self.__mutex.unlock()
        if __display is None:
            __display = f"loading info ... @ {self.__environ.path}"
        return __display

    @property
    def env_path(self):
        return self.__environ.env_path

    @property
    def environ(self):
        return self.__environ

    @property
    def completed(self):
        return self.__display is not None
