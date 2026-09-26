# coding: utf-8
'''回归测试：关闭窗口不能导致进程崩溃。

这里锁住的是两个真实出现过的崩溃：

1. closeEvent 里调用了未导入的名字（save_config_or_warn），抛 NameError。
   异常发生在 Qt 的 C++ 事件处理中，无法向上传播，表现为**点右上角关闭按钮
   直接崩溃**（退出码 0xC0000409），而不是显示 Python 报错。

2. thread_repo.is_empty() 只检查列表长度、不检查线程是否还在运行。已结束但
   尚未被清理定时器移除的线程会让它返回 False，于是 closeEvent 误判为「还有
   任务在运行」而弹出模态对话框 —— 在 closeEvent 里 exec_() 会让 Qt 重入事件
   循环，同样导致崩溃。是否触发取决于清理定时器有没有恰好跑过，所以表现为
   「不定时崩溃」。

这类问题的共同点是：崩溃发生在 C++ 层，Python 侧的普通单元测试抓不到，必须
真的把窗口关一次。因此这里在独立子进程里执行，进程退出码非 0 即视为失败。
'''
import os
import subprocess
import sys
import textwrap
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / 'src'

# 依次打开并关闭每个子窗口；只要有一个崩溃，进程就会以非 0 退出
PROBE = textwrap.dedent(
    '''
    import os, sys
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    sys.path.insert(0, sys.argv[1])

    import awespykit.runpykit as rpk

    app = rpk._App
    main = rpk.MainEntrance()

    windows = [
        ('包管理器', main._MainEntrance__pkgmgr_win),
        ('程序打包工具', main._MainEntrance__pyitool_win),
        ('镜像源设置', main._MainEntrance__indexmgr_win),
        ('安装包下载器', main._MainEntrance__pkgdl_win),
        ('云函数打包', main._MainEntrance__cloudfunction_win),
        ('关于', main._MainEntrance__about_window),
    ]

    # 反复开关，覆盖「清理定时器尚未触发」这类时序相关的路径
    for round_no in range(3):
        for name, window in windows:
            window.display()
            app.processEvents()
            window.close()
            app.processEvents()
    print('no-crash')
    '''
)


def test_closing_every_window_does_not_crash():
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    # 不要用仓库根目录，避免把 src 之外的同名包引进来
    env.pop('PYTHONPATH', None)
    result = subprocess.run(
        [sys.executable, '-c', PROBE, str(SRC_ROOT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert result.returncode == 0, (
        f'关闭窗口时进程崩溃（退出码 {result.returncode}）。\n'
        '这类崩溃发生在 Qt 的 C++ 层，通常是 closeEvent 里抛了异常，'
        '或是在 closeEvent 里弹出了模态对话框。\n'
        f'stdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'no-crash' in result.stdout


def test_thread_repo_is_empty_ignores_finished_threads():
    '''已结束但尚未清理的线程不应让 is_empty() 返回 False。

    这是上面第 2 个崩溃的直接原因。这里用真实的 QThread 验证，而不是只测
    列表长度。
    '''
    import time

    sys.path.insert(0, str(SRC_ROOT))
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PyQt5.QtWidgets import QApplication

    from awespykit.com.common import QThreadModel, ThreadRepo

    app = QApplication.instance() or QApplication([])

    finished_flag = []

    def quick():
        finished_flag.append(True)

    repo = ThreadRepo(interval=60_000)  # 定时器故意设得很久，确保不会自动清理
    thread = QThreadModel(quick)
    thread.start()
    repo.put(thread, 1)

    # 等线程真正结束
    deadline = time.time() + 10
    while thread.isRunning() and time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
    assert not thread.isRunning(), '后台线程未能结束'

    # 此刻线程仍在仓库列表里（未被清理），但已不在运行
    assert repo._thread_repo, '线程应仍在仓库中，用于验证 is_empty 的语义'
    assert repo.is_empty(), (
        'is_empty() 把「已结束但未清理」的线程当成运行中，'
        '会导致关闭窗口时误弹对话框并崩溃'
    )
    thread.wait(2000)
