import copy
import os
import unittest
from unittest.mock import patch

from prune_releases import main


class ReleaseCleanupTests(unittest.TestCase):
    def setUp(self):
        self.current = {
            "id": 2, "tag_name": "2.3.3", "draft": False, "prerelease": False,
            "published_at": "2026-10-12T00:00:00Z",
            "assets": [
                {"name": name, "state": "uploaded", "size": 10}
                for name in (
                    "awespykit-2.3.3-py3-none-any.whl",
                    "awespykit-2.3.3.tar.gz", "Awespykit.exe",
                    "Awespykit.exe.sha256", "python-dist.sha256",
                )
            ],
        }
        self.latest = self.current
        self.old = dict(self.current, id=1, tag_name="2.3.2",
                        published_at="2026-10-07T00:00:00Z")
        self.releases = [self.current, self.old]

    def run_cleanup(self):
        def fake_api(endpoint, paginate=False):
            if "/tags/" in endpoint:
                return self.current
            if endpoint.endswith("/latest"):
                return self.latest
            self.assertTrue(paginate)
            return [self.releases]

        with patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "owner/repo", "RELEASE_TAG": "2.3.3",
            "RELEASE_VERSION": "2.3.3",
        }), patch("prune_releases.api", side_effect=fake_api), \
                patch("prune_releases.subprocess.run") as command:
            main()
            return [call.args[0] for call in command.call_args_list]

    def test_complete_latest_removes_old_release_and_tag(self):
        self.assertEqual(self.run_cleanup(), [[
            "gh", "release", "delete", "2.3.2", "--repo", "owner/repo",
            "--cleanup-tag", "--yes",
        ]])

    def test_incomplete_assets_prevent_deletion(self):
        for field, value in (("size", 0), ("state", "new")):
            current = copy.deepcopy(self.current)
            self.current["assets"][0][field] = value
            with self.assertRaises(RuntimeError):
                self.run_cleanup()
            self.current = current

    def test_missing_asset_prevents_deletion(self):
        self.current["assets"].pop()
        with self.assertRaises(RuntimeError):
            self.run_cleanup()

    def test_outdated_workflow_never_deletes(self):
        self.latest = dict(self.current, id=3)
        self.assertEqual(self.run_cleanup(), [])

    def test_newer_release_and_draft_are_preserved(self):
        self.releases = [
            dict(self.old, draft=True),
            dict(self.old, published_at="2026-10-13T00:00:00Z"),
            self.current,
        ]
        self.assertEqual(self.run_cleanup(), [])

    def test_prerelease_cannot_prune(self):
        self.current["prerelease"] = True
        with self.assertRaises(RuntimeError):
            self.run_cleanup()


if __name__ == "__main__":
    unittest.main()
