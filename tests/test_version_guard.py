# coding: utf-8
'''回归测试：fastpip 版本不符时要给出可读提示，而不是静默退出。

打包成 exe 后 console=False，没有控制台窗口。原实现在版本不符时直接 raise，
异常信息写进 stderr 却没人看得到 —— 用户双击图标只见进程一闪而过，完全不知道
发生了什么（典型的「双击没反应」）。

现在改为弹出对话框说明原因与解决办法，判断逻辑放在这里以便单独测试。
'''
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(SRC_ROOT))

from awespykit.com.requires import REQ_FPVER, check_fastpip_version  # noqa: E402


def test_matching_version_is_accepted():
    assert check_fastpip_version(REQ_FPVER) == ''


def test_newer_minor_version_is_accepted():
    '''次版本号更高应当接受（接口向后兼容）。'''
    assert check_fastpip_version((REQ_FPVER[0], REQ_FPVER[1] + 1, 0)) == ''


def test_newer_patch_version_is_accepted():
    assert check_fastpip_version((REQ_FPVER[0], REQ_FPVER[1], REQ_FPVER[2] + 1)) == ''


def test_older_version_is_rejected_with_guidance():
    message = check_fastpip_version((REQ_FPVER[0], REQ_FPVER[1] - 1, 0))
    assert message, '版本过低时必须返回提示'
    # fastpip 已 vendored 进本程序，正常情况下不该出现版本过低。
    # 提示要指向「环境里残留了旧版本」这个真实原因，并给出卸载命令。
    assert 'pip uninstall' in message, '提示里应给出可执行的解决办法'


def test_different_major_version_is_rejected():
    message = check_fastpip_version((REQ_FPVER[0] + 1, REQ_FPVER[1], REQ_FPVER[2]))
    assert message, '主版本号不符时必须返回提示'
    assert str(REQ_FPVER[0]) in message


def test_same_minor_but_older_patch_is_rejected():
    message = check_fastpip_version((REQ_FPVER[0], REQ_FPVER[1], 0))
    if REQ_FPVER[2] > 0:
        assert message, '次版本号相同但修订号更低时必须拒绝'
