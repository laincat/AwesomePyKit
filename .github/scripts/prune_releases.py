"""Keep the latest stable release only, after validating its uploaded assets."""
import json
import os
import subprocess


def api(endpoint, paginate=False):
    command = ["gh", "api", endpoint]
    if paginate:
        command.extend(["--paginate", "--slurp"])
    return json.loads(subprocess.run(
        command, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout)


def validate_assets(release, version):
    required = {
        f"awespykit-{version}-py3-none-any.whl",
        f"awespykit-{version}.tar.gz",
        "Awespykit.exe",
        "Awespykit.exe.sha256",
        "python-dist.sha256",
    }
    uploaded = {
        asset["name"] for asset in release["assets"]
        if asset["state"] == "uploaded" and asset["size"] > 0
    }
    missing = required - uploaded
    if missing:
        raise RuntimeError(f"Release assets missing or incomplete: {sorted(missing)}")


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    tag = os.environ["RELEASE_TAG"]
    current = api(f"repos/{repo}/releases/tags/{tag}")
    if current["draft"] or current["prerelease"]:
        raise RuntimeError("Cleanup requires a published stable release")
    validate_assets(current, os.environ["RELEASE_VERSION"])
    latest = api(f"repos/{repo}/releases/latest")
    if latest["id"] != current["id"]:
        print("A different release is latest; skipping cleanup")
        return
    pages = api(f"repos/{repo}/releases?per_page=100", paginate=True)
    for page in pages:
        for release in page:
            if release["id"] == current["id"] or release["draft"]:
                continue
            # A delayed workflow must not delete a release published after it.
            if release["published_at"] > current["published_at"]:
                continue
            subprocess.run([
                "gh", "release", "delete", release["tag_name"],
                "--repo", repo, "--cleanup-tag", "--yes",
            ], check=True)
            print(f"Removed superseded release {release['tag_name']}")


if __name__ == "__main__":
    main()
