# coding: utf-8

__doc__ = "检查项目导入的所有模块所需的类、函数等。"

import ast
import re
from pathlib import PurePath
from os import walk
from os.path import basename, join
from typing import *

from fastpip import PyEnv

try:
    # chardet 5.x 起把 UniversalDetector 提到顶层了，旧的子模块路径已弃用
    from chardet import UniversalDetector
except ImportError:  # pragma: no cover - 兼容 chardet 4.x
    from chardet.universaldetector import UniversalDetector


class FindImport(ast.NodeVisitor):
    def __init__(self, out=None):
        if isinstance(out, set):
            self.__result = out
        else:
            self.__result = set()

    def visit_ImportFrom(self, node):
        # 相对导入（from . import x / from .models import Y）永远指向项目自身的
        # 模块，不可能是需要安装的第三方包，因此整条跳过。
        #
        # 原实现在这里对 node.module 调用 split，而相对导入的 node.module 可能
        # 是 None（例如 from . import x），会抛 AttributeError；调用方又把整个
        # 文件的解析包在 try 里，于是「含相对导入的文件」其全部依赖会被静默
        # 丢弃 —— 用户看不到任何缺失模块的提示（漏报），这是导入检查的核心功能。
        if node.level == 0 and node.module:
            self.__result.add(self.split(node.module))
        self.generic_visit(node)

    def visit_Import(self, node):
        self.__result.update(self.split(n.name) for n in node.names)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id == "__import__":
                self.add_call_node_arg(node.args[0])
        elif isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            name = node.func.value
            if isinstance(name, ast.Name) and name.id == "importlib":
                if attr == "__import__" or attr == "import_module":
                    self.add_call_node_arg(node.args[0])
        self.generic_visit(node)

    def getresult(self):
        return self.__result

    @staticmethod
    def split(string: str):
        return string.split(".", 1)[0]

    def add_call_node_arg(self, arg):
        # Python 3.8+ 的字符串字面量是 ast.Constant；Python 3.7 是 ast.Str。
        # ast.Str / ast.Num 已在 Python 3.12 中移除，因此不能直接引用。
        if isinstance(arg, ast.Constant):
            if isinstance(arg.value, str):
                self.__result.add(self.split(arg.value))
            return
        str_node = getattr(ast, "Str", None)
        if str_node is not None and isinstance(arg, str_node):
            self.__result.add(self.split(arg.s))


def to_be_excluded(_dirpath: str, exclude_dirs):
    # 原来的实现用 startswith 做前缀比较，会把 C:\project 误判成 C:\proj 的
    # 子目录。这里改成按路径分量比较：只有当 _dirpath 确实位于某个排除目录
    # 之下（或正好是它本身）时才算排除。
    if not _dirpath:
        return False
    target = PurePath(_dirpath.lower())
    for p in exclude_dirs:
        if not p:
            continue
        excluded = PurePath(p.lower())
        try:
            target.relative_to(excluded)
        except ValueError:
            continue
        return True
    return False


def file_codings(program_root, exclude_dirs):
    pattern = re.compile(r"^.+\.pyw?$")
    path_coding_groups = []
    for root, _, files in walk(program_root):
        if to_be_excluded(root, exclude_dirs):
            continue
        for name in files:
            if not pattern.match(name):
                continue
            path_coding_groups.append(join(root, name))
    coding_detector = UniversalDetector()
    for index, file_path in enumerate(path_coding_groups):
        coding_detector.reset()
        try:
            with open(file_path, "rb") as sf:
                for line in sf:
                    coding_detector.feed(line)
                    if coding_detector.done:
                        break
            coding_detector.close()
            if coding_detector.result["confidence"] < 0.9:
                coding = "utf-8"
            else:
                coding = coding_detector.result["encoding"]
            path_coding_groups[index] = (file_path, coding)
        except Exception:
            path_coding_groups[index] = file_path, None
    return path_coding_groups


class ImportInspector:
    def __init__(self, python_dir, program_root, excludes=None):
        self._root = program_root
        self._excludes = list()
        if isinstance(excludes, (list, tuple)):
            self._excludes.extend(excludes)
        self.importables = self.__project_importables()
        self.importables.update(PyEnv(python_dir).names_for_import())

    @staticmethod
    def __modules_tobe_imported(string):
        """查找并返回 string 中所有需要导入的模块集合"""
        try:
            node = ast.parse(string, "<string>", "exec")
        except SyntaxError:
            return set()
        abstract_syntax_tree_visit = FindImport()
        abstract_syntax_tree_visit.visit(node)
        return abstract_syntax_tree_visit.getresult()

    def __project_importables(self):
        """项目目录下可导入的包、模块。"""
        pkg_pattern = re.compile(r"^[A-Za-z0-9_]+$")
        mod_pattern = re.compile(r"^([A-Za-z0-9_]+).*(?<!_d)\.py[cdw]?$", re.I)
        project_importables = set()
        for root, _, files in walk(self._root):
            if to_be_excluded(root, self._excludes):
                continue
            if "__init__.py" in files:
                project_importables.add(basename(root))
            module_in_dir = False
            for file_name in files:
                matched = mod_pattern.match(file_name)
                if not matched:
                    continue
                module_in_dir = True
                project_importables.add(matched.group(1))
            if module_in_dir:
                pkg_name = pkg_pattern.match(basename(root))
                if pkg_name:
                    project_importables.add(pkg_name.group())
        return project_importables

    def get_missing_items(self):
        """
        查找指定目录内源码所有需要导入的模块，并计算哪些模块未在指定环境中安装
        返回值类型：[(源码文件路径, {源码导入的模块}, {环境中未安装的模块})...]
        """
        results: List[Tuple[Union[str, None], Set, Set]] = list()
        for p, c in file_codings(self._root, self._excludes):
            if c is None:
                continue
            try:
                with open(p, encoding=c) as f:
                    file_string = f.read()
                imps = self.__modules_tobe_imported(file_string)
                results.append((p, imps, imps - self.importables))
            except Exception:
                results.append((p, set(), set()))
        if not results:
            results.append((None, set(), set()))
        return results
