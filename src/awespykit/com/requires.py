# coding: utf-8

REQ_FPVER = (1, 7, 0)  # 对 fastpip 版本号的要求


# 版本号约定（主版本号.次版本号.修订号）：
#   1. 主版本号必须与要求一致；
#   2. 次版本号需 ≥ 要求；
#   3. 次版本号相同时，修订号需 ≥ 要求。


def check_fastpip_version(vernum, required=REQ_FPVER):
    """检查 fastpip 版本是否符合要求。

    符合则返回空串；不符合则返回一段可直接展示给用户的说明。

    单独放在这里（而不是写在入口模块里）有两个好处：不依赖 Qt，方便测试；
    入口模块可以只在真正需要时才弹窗。
    """
    required_text = '.'.join(str(part) for part in required)
    current_text = '.'.join(str(part) for part in vernum)
    if vernum[0] != required[0]:
        return (
            f"fastpip 主版本号不符。\n\n"
            f"  当前安装：{current_text}\n"
            f"  本程序要求：{required_text}（主版本号必须一致）\n\n"
            f"主版本号不同通常意味着接口已不兼容，本程序无法在此版本上运行。"
        )
    too_old = vernum[1] < required[1] or (
        vernum[1] == required[1] and vernum[2] < required[2]
    )
    if too_old:
        return (
            f"fastpip 版本过低。\n\n"
            f"  当前安装：{current_text}\n"
            f"  本程序要求：{required_text} 或更高（主版本号需相同）\n\n"
            f"请升级后重试：  pip install -U fastpip"
        )
    return ""