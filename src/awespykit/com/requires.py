# coding: utf-8

REQ_FPVER = (1, 7, 1)  # 对 fastpip 的最低版本要求

# fastpip 已 vendored 到本仓库（src/fastpip/），随程序一起打包安装，不再是用户需要
# 自行升级的第三方依赖。所以这项检查的用途变了：从「要求用户装对版本」变成
# 「确认实际加载到的 fastpip 至少与我们的副本同版」。
#
# 之所以保留：若环境里残留了 PyPI 上的 fastpip（例如从旧版本升级上来，旧目录
# 未被清掉），sys.path 的先后顺序可能让程序加载到那份旧代码。此时明确报错，
# 比在后续操作里出现难以理解的失败要好。
#
# 版本号约定（主版本号.次版本号.修订号）：
#   1. 主版本号必须与要求一致；
#   2. 次版本号需 >= 要求；
#   3. 次版本号相同时，修订号需 >= 要求。


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
            f"  当前加载：{current_text}\n"
            f"  本程序自带：{required_text}（主版本号须一致）\n\n"
            f"主版本号不同通常意味着接口已不兼容，程序无法在此版本上运行。"
        )
    too_old = vernum[1] < required[1] or (
        vernum[1] == required[1] and vernum[2] < required[2]
    )
    if too_old:
        return (
            f"fastpip 版本过低。\n\n"
            f"  当前加载：{current_text}\n"
            f"  本程序自带：{required_text}\n\n"
            f"程序已自带 fastpip，正常情况下不该出现此提示。"
            f"多半是环境里残留了旧版 fastpip 目录，或安装顺序异常。\n"
            f"可尝试重新安装本程序；若曾单独装过 fastpip，请先卸载：\n"
            f"    pip uninstall fastpip"
        )
    return ""