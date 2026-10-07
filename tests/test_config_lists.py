# coding: utf-8
"""回归测试：列表型配置项必须支持就地修改。"""

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(SRC_ROOT))

from awespykit.settings.cloud_function import CloudFunctionCFG
from awespykit.settings.package_download import PackageDownloadConfig
from awespykit.settings.package_manager import PackageManagerConfig


def _dict_backed_config(cls):
    cfg = cls.__new__(cls)
    dict.__init__(cfg)
    return cfg


def test_package_manager_pypaths_in_place_mutations_persist():
    cfg = _dict_backed_config(PackageManagerConfig)
    cfg["python_paths"] = ["C:/Python311", 12, "C:/Python312"]

    paths = cfg.pypaths

    assert paths == ["C:/Python311", "C:/Python312"]
    assert paths is cfg["python_paths"]

    cfg.pypaths.append("C:/Python313")
    assert cfg["python_paths"] == [
        "C:/Python311",
        "C:/Python312",
        "C:/Python313",
    ]

    del cfg.pypaths[1]
    assert cfg["python_paths"] == ["C:/Python311", "C:/Python313"]


def test_cloud_function_project_paths_in_place_mutations_persist():
    cfg = _dict_backed_config(CloudFunctionCFG)
    cfg["project_paths"] = ["D:/project-a"]

    cfg.project_paths.append("D:/project-b")
    assert cfg["project_paths"] == ["D:/project-a", "D:/project-b"]

    del cfg.project_paths[0]
    assert cfg["project_paths"] == ["D:/project-b"]


def test_package_download_list_properties_are_config_backed():
    cfg = _dict_backed_config(PackageDownloadConfig)
    cfg["package_names"] = "requests"
    cfg["platform"] = ["win_amd64", 32]
    cfg["abis"] = ["cp314"]

    cfg.package_names.append("urllib3")
    cfg.platform.append("any")
    cfg.abis.clear()

    assert cfg["package_names"] == ["requests", "urllib3"]
    assert cfg["platform"] == ["win_amd64", "any"]
    assert cfg["abis"] == []
