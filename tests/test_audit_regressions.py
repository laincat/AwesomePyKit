"""Isolated audit regressions. No real builds, installs or user data deletion."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


safe = load_file('audit_safe_files', 'src/awespykit/safe_files.py')
process = load_file('audit_process', 'src/fastpip/utils/process.py')


def extract(path, class_name, method=None, namespace=None):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    if method:
        node = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == method)
        node.decorator_list = []
    namespace = {} if namespace is None else namespace
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), namespace)
    return namespace[node.name]


class FilesTests(unittest.TestCase):
    def test_cleanup_only_owned_child_for_all_work_parents(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'project'
            source.mkdir()
            (source / 'main.py').write_text('preserve', encoding='utf-8')
            for name in ('build', '.', '..', 'shared/nested'):
                parent = (source / name).resolve()
                parent.mkdir(parents=True, exist_ok=True)
                sibling = parent / 'unrelated.txt'
                sibling.write_text('preserve', encoding='utf-8')
                owned = safe.owned_workspace(parent, source)
                (owned[0] / 'artifact').write_text('temporary', encoding='utf-8')
                safe.remove_owned_workspace(owned)
                self.assertFalse(owned[0].exists())
                self.assertTrue(sibling.exists())
                self.assertTrue((source / 'main.py').exists())

    def test_cleanup_refuses_source_and_wrong_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve()
            with self.assertRaises(ValueError):
                safe.remove_owned_workspace((source, source.parent, source, 'fake'))
            owned = safe.owned_workspace(source, source)
            (owned[0] / '.awespykit-owner').write_text('tampered', encoding='ascii')
            with self.assertRaises(ValueError):
                safe.remove_owned_workspace(owned)
            self.assertTrue(owned[0].exists())

    def test_cleanup_refuses_links(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve()
            owned = safe.owned_workspace(source, source)
            link = owned[0] / 'escape'
            try:
                link.symlink_to(source, target_is_directory=True)
            except OSError:
                if os.name != 'nt':
                    raise
                subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(source)], check=True, capture_output=True)
            try:
                with self.assertRaises(ValueError):
                    safe.remove_owned_workspace(owned)
            finally:
                if link.is_symlink():
                    link.unlink()
                else:
                    os.rmdir(link)

    def test_atomic_settings_preserve_previous_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            safe.save_json_with_backup(path, {'old': 1})
            with self.assertRaises(TypeError):
                safe.save_json_with_backup(path, {'bad': object()})
            self.assertEqual(json.loads(path.read_bytes()), {'old': 1})
            with patch.object(safe.os, 'replace', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    safe.save_json_with_backup(path, {'new': 2})
            self.assertEqual(json.loads(path.read_bytes()), {'old': 1})
            safe.save_json_with_backup(path, {'new': 2})
            self.assertEqual(json.loads(Path(str(path) + '.bak').read_bytes()), {'old': 1})
            self.assertEqual(len(list(Path(directory).iterdir())), 2)

    def test_zip_source_and_ancestor_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'project'
            project.mkdir()
            (project / 'handler.py').write_text('hello', encoding='utf-8')
            cwd = os.getcwd()
            for destination in (project / 'out.zip', Path(directory) / 'out.zip'):
                safe.atomic_zip(destination, [(project, [])])
                with zipfile.ZipFile(destination) as archive:
                    self.assertIn('handler.py', archive.namelist())
                    if destination.parent == project:
                        self.assertNotIn('out.zip', archive.namelist())
                self.assertEqual(os.getcwd(), cwd)

    def test_zip_collision_and_write_failure_preserve_previous(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, deps = root / 'source', root / 'deps'
            source.mkdir(); deps.mkdir()
            (source / 'handler.py').write_text('hello', encoding='utf-8')
            (deps / 'handler.py').write_text('collision', encoding='utf-8')
            destination = root / 'out.zip'
            destination.write_bytes(b'old archive')
            with self.assertRaises(ValueError):
                safe.atomic_zip(destination, [(source, []), (deps, [])])
            self.assertEqual(destination.read_bytes(), b'old archive')
            with patch.object(safe.zipfile.ZipFile, 'write', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    safe.atomic_zip(destination, [(source, [])])
            self.assertEqual(destination.read_bytes(), b'old archive')
            self.assertEqual(len(list(root.glob('*.zip'))), 1)


class ProcessTests(unittest.TestCase):
    def test_windows_job_uses_unique_string_name_and_owns_handle(self):
        names, assigned, closed = [], [], []
        def create(security, name):
            self.assertIsInstance(name, str)
            self.assertTrue(name)
            names.append(name)
            return len(names)
        api = types.SimpleNamespace(CloseHandle=closed.append)
        job_api = types.SimpleNamespace(
            CreateJobObject=create,
            QueryInformationJobObject=lambda *a: {"BasicLimitInformation": {"LimitFlags": 0}},
            SetInformationJobObject=lambda *a: None,
            AssignProcessToJobObject=lambda *a: assigned.append(a),
            JobObjectExtendedLimitInformation=9, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE=8192,
        )
        with patch.dict(sys.modules, win32api=api, win32job=job_api):
            for _ in range(2):
                job = process._WindowsJob(types.SimpleNamespace(_handle=123))
                job.close()
                job.close()
        self.assertNotEqual(names[0], names[1])
        self.assertEqual(assigned, [(1, 123), (2, 123)])
        self.assertEqual(closed, [1, 2])

    def test_immediate_exit_large_unicode_and_failure_tail(self):
        for callback_mode in (False, True):
            lines = []
            data, code = process.run_process(
                [sys.executable, '-c', "import sys; sys.stdout.buffer.write(('中文'*50000+'\\nlast error\\n').encode()); sys.exit(7)"],
                callback=lines.append if callback_mode else None, timeout=10,
            )
            self.assertEqual(code, 7)
            self.assertEqual(data, ('中文'*50000+'\nlast error\n').encode())
            if callback_mode:
                self.assertEqual(b''.join(lines), data)

    def test_timeout_reaps_child_and_keeps_output(self):
        started = time.monotonic()
        data, code = process.run_process(
            [sys.executable, '-u', '-c', "import time; print('before timeout'); time.sleep(60)"], timeout=0.5,
        )
        self.assertEqual(code, 1)
        self.assertIn(b'before timeout', data)
        self.assertLess(time.monotonic() - started, 20)

    def test_cancel_scope_blocks_following_children(self):
        event = threading.Event()
        timer = threading.Timer(0.3, event.set)
        timer.start()
        try:
            with process.cancellation_scope(event):
                _, code = process.run_process([sys.executable, '-c', 'import time; time.sleep(60)'])
                self.assertEqual(code, 1)
                with patch.object(process.subprocess, 'Popen', side_effect=AssertionError('must not spawn')):
                    self.assertEqual(process.run_process(['unused']), (b'', 1))
        finally:
            timer.join()

    def test_fast_parent_exit_does_not_escape_process_tree(self):
        script = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); print('spawned',flush=True)"
        started = time.monotonic()
        data, code = process.run_process([sys.executable, '-c', script], timeout=0.5)
        self.assertEqual(code, 1)
        self.assertIn(b'spawned', data)
        self.assertLess(time.monotonic() - started, 20)

    def test_timeout_kills_descendant_holding_pipe(self):
        script = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); print('spawned',flush=True); time.sleep(60)"
        started = time.monotonic()
        data, code = process.run_process([sys.executable, '-c', script], timeout=0.5)
        self.assertEqual(code, 1)
        self.assertIn(b'spawned', data)
        self.assertLess(time.monotonic() - started, 20)


class ParserTests(unittest.TestCase):
    def test_dynamic_import_keywords_preserve_other_imports(self):
        visitor = extract('src/awespykit/utils/cip.py', 'FindImport', namespace={'ast': ast})()
        visitor.visit(ast.parse("import requests\nimportlib.import_module(name='urllib3')\nimportlib.import_module('.local', package='app')\n__import__()\nimportlib.import_module(variable)\nfrom . import local"))
        self.assertEqual(visitor.getresult(), {'requests', 'urllib3'})
        self.assertEqual(visitor.unsupported_dynamic_imports, [4, 5])

    def test_cleanup_captures_workspace_before_thread_starts(self):
        calls = []
        class Worker:
            def __init__(self, target, workspace):
                self.target, self.workspace = target, workspace
            def start(self):
                # Model another build updating mutable tool state before execution.
                tool.owned_work = "new workspace"
                self.target(self.workspace)
        tool = types.SimpleNamespace(owned_work="old workspace", cleanup_workspace=calls.append)
        owner = types.SimpleNamespace(pyi_tool=tool, thread_repo=types.SimpleNamespace(put=lambda _: None))
        cleanup = extract('src/awespykit/logic/pyinstaller_tool.py', 'PyinstallerToolWindow', 'delete_working_dir', {'QThreadModel': Worker})
        cleanup(owner)
        self.assertEqual(calls, ["old workspace"])
        self.assertEqual(tool.owned_work, "new workspace")

    def test_config_loader_recovers_backup_and_exposes_error(self):
        config_class = extract('src/awespykit/settings/abstract_config.py', 'AbstractConfig', namespace={
            'Path': Path, 'config_root': '.', 'json': json,
            'save_json_with_backup': safe.save_json_with_backup,
            'warnings': __import__('warnings'),
        })
        with tempfile.TemporaryDirectory() as directory:
            config_class.root = Path(directory)
            path = Path(directory) / 'settings.json'
            path.write_text('{broken', encoding='utf-8')
            Path(str(path) + '.bak').write_text('{"recovered": true}', encoding='utf-8')
            with self.assertWarns(RuntimeWarning):
                cfg = config_class('settings.json')
            self.assertEqual(cfg, {'recovered': True})
            self.assertIsNotNone(cfg.load_error)
            self.assertEqual(path.read_text(), '{broken')

    def test_thread_stop_never_terminates_and_reports_wait_failure(self):
        stop = extract('src/awespykit/com/common.py', 'ThreadRepo', 'stop_all')
        thread = types.SimpleNamespace(cancel=lambda: None, wait=lambda _: False, isRunning=lambda: True)
        self.assertFalse(stop(types.SimpleNamespace(_thread_repo=[(thread, 0)])))
        thread.isRunning = lambda: False
        self.assertTrue(stop(types.SimpleNamespace(_thread_repo=[(thread, 0)])))

    def test_version_strings_are_data(self):
        with tempfile.TemporaryDirectory() as directory:
            generate = extract('src/awespykit/utils/pyi.py', 'PyiTool', '__generate_infofile', {
                'os': os, 'ast': ast, 're': __import__('re'), 'config_root': directory,
            })
            value = 'A "quoted" company \\ with\nnewline and $ProductName$'
            path = generate({'$filevers$': '(1, 2, 3, 4)', '$prodvers$': '(1, 2, 3, 4)', '$CompanyName$': value})
            tree = ast.parse(Path(path).read_text(encoding='utf-8'))
            strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)]
            self.assertIn(value, strings)
            with self.assertRaises((ValueError, SyntaxError)):
                generate({'$filevers$': '__import__("os").system("bad")'})

    def test_download_filters_and_cross_platform(self):
        configure = extract('src/awespykit/logic/package_download.py', 'PackageDownloadWindow', 'make_configure', {
            'MessageBox': lambda *a: self.fail('valid wheel-only request was rejected'),
        })
        for mode in ('no_binary', 'only_binary'):
            config = types.SimpleNamespace(
                download_deps=False, download_type=mode, include_pre=False,
                ignore_requires_python=False, save_path='', platform='',
                python_version='', implementation='', abis=[], use_index_url=False, index_url='',
            )
            result = configure(types.SimpleNamespace(config=config), ['requests>=2', 'urllib3<3'])
            self.assertEqual(result[mode], [':all:'])
            if mode == 'only_binary':
                config.platform = 'win_amd64'
                config.download_deps = True
                result = configure(types.SimpleNamespace(config=config), ['requests>=2', 'urllib3<3'])
                self.assertEqual(result['platform'], ['win_amd64'])


if __name__ == '__main__':
    unittest.main()
