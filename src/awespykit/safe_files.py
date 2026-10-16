"""Owned build workspaces and atomic file publication (Python 3.9+)."""
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import uuid
import zipfile


def atomic_write(path, data):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def owned_workspace(parent, source):
    parent, source = Path(parent).resolve(), Path(source).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="awespykit-build-", dir=parent))
    token = uuid.uuid4().hex
    (root / ".awespykit-owner").write_text(token, encoding="ascii")
    return root, parent, source, token


def _is_link(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400
    )


def remove_owned_workspace(workspace):
    root, parent, source, token = workspace
    if (_is_link(root) or root.resolve() != root or root.parent != parent
            or root == source or root in source.parents
            or root == Path(root.anchor)):
        raise ValueError("Refusing unsafe build cleanup target")
    marker = root / ".awespykit-owner"
    if _is_link(marker) or marker.read_text(encoding="ascii") != token:
        raise ValueError("Build workspace ownership changed")
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            if _is_link(Path(directory) / name):
                raise ValueError("Refusing symlink or junction in build workspace")
    shutil.rmtree(root)


def filtered_files(root, excludes):
    root = Path(root).resolve()
    excluded = [Path(p).resolve() for p in excludes]
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if root not in resolved.parents:
            raise ValueError("Source symlink escapes archive root: " + str(path))
        if any(resolved == p or p in resolved.parents for p in excluded):
            continue
        yield path


def atomic_zip(destination, sources, exclusions=()):
    """Validate all names before replacing a good archive; never change cwd."""
    destination = Path(destination).resolve()
    members = {}
    for root, excludes in sources:
        root = Path(root).resolve()
        for path in filtered_files(root, [destination, *excludes, *exclusions]):
            name = path.relative_to(root).as_posix()
            # ZIPs are commonly unpacked on case-insensitive Windows filesystems.
            key = name.casefold()
            if key in members:
                raise ValueError("Duplicate archive member: " + name)
            members[key] = (name, path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".zip", delete=False) as stream:
            temporary = Path(stream.name)
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, path in members.values():
                archive.write(path, name)
        with temporary.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_json_with_backup(path, value):
    data = json.dumps(value, ensure_ascii=False).encode("utf-8")
    path = Path(path)
    if path.exists():
        previous = path.read_bytes()
        # Never replace the recovery copy with a malformed main file.
        try:
            decoded = json.loads(previous)
        except (ValueError, UnicodeError):
            pass
        else:
            if isinstance(decoded, dict):
                atomic_write(str(path) + ".bak", previous)
    atomic_write(path, data)
