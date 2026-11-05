"""Exercise the real publishing shell with a local fake GitHub CLI, never a network."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/chinese-apk.yml"
FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, shutil, sys
p = pathlib.Path(os.environ["FAKE_STATE"])
s = json.loads(p.read_text())
a = sys.argv[1:]
s["commands"].append(a)
def save():
    p.write_text(json.dumps(s))
def option(name):
    return a[a.index(name) + 1]
def missing():
    save()
    print("gh: Not Found (HTTP 404)", file=sys.stderr)
    sys.exit(1)
if a[0] == "api":
    endpoint = a[1]
    if s.get("api_failure"):
        save()
        print("gh: Forbidden (HTTP 403)", file=sys.stderr)
        sys.exit(1)
    if endpoint == "graphql":
        print("12345" if s.get("release") else "")
    elif "/releases/tags/" in endpoint:
        if s.get("release") is None or s["release"]["draft"]:
            missing()
        print(json.dumps(s["release"]))
    elif endpoint.endswith("/releases/12345"):
        assert s.get("release") is not None
        print(json.dumps(s["release"]))
    elif "/git/ref/tags/" in endpoint:
        if not s.get("tag_sha"):
            missing()
        print(json.dumps({"object": {"type": "commit", "sha": s["tag_sha"]}}))
    elif "/git/ref/heads/main" in endpoint:
        print(s.get("head_sha", os.environ["GITHUB_SHA"]))
    else:
        raise AssertionError(a)
elif a[:2] == ["release", "create"]:
    assert s.get("release") is None
    assert "--draft" in a
    s["release"] = {"tag_name": a[2], "target_commitish": option("--target"),
        "draft": True, "prerelease": "--prerelease" in a, "assets": [],
        "html_url": "https://github.com/zhuiyun/cleanyourtv-app/releases/tag/" + a[2]}
elif a[:2] == ["release", "upload"]:
    assert "--clobber" not in a
    src = pathlib.Path(a[3])
    assert not any(x["name"] == src.name for x in s["release"]["assets"])
    dst = p.parent / "remote" / src.name
    dst.parent.mkdir(exist_ok=True)
    shutil.copyfile(src, dst)
    s["release"]["assets"].append({"name": src.name})
elif a[:2] == ["release", "download"]:
    dest = pathlib.Path(option("--dir"))
    for i, v in enumerate(a):
        if v == "--pattern":
            name = a[i + 1]
            shutil.copyfile(p.parent / "remote" / name, dest / name)
    if s.get("corrupt_download"):
        (dest / os.environ["APK_FILE"]).write_bytes(b"corrupt")
elif a[:2] == ["release", "edit"]:
    assert "--draft=false" in a
    s["release"]["draft"] = False
    s["tag_sha"] = s["release"]["target_commitish"]
    s["latest"] = "--latest=true" in a
else:
    raise AssertionError(a)
save()
'''


@unittest.skipUnless(shutil.which("jq"), "jq is required by the GitHub runner")
class ChineseReleaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        (self.path / "bin").mkdir()
        gh = self.path / "bin/gh"
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        self.dist = self.path / "dist"
        self.dist.mkdir()
        self.apk = "CleanYourTV-zh-CN-0.4.8.apk"
        data = b"test signed APK fixture"
        self.digest = hashlib.sha256(data).hexdigest()
        (self.dist / self.apk).write_bytes(data)
        (self.dist / "SHA256SUMS.txt").write_text(f"{self.digest}  {self.apk}\n")
        self.state = self.path / "state.json"
        self.state.write_text(json.dumps({"commands": []}))
        self.sha = "a" * 40
        self.env = dict(os.environ, PATH=str(self.path / "bin") + os.pathsep + os.environ["PATH"],
                        FAKE_STATE=str(self.state), VERSION="0.4.8", VERSION_CODE="30",
                        APK_FILE=self.apk, APK_SHA256=self.digest, CERT_SHA256="b" * 64,
                        GH_REPO="zhuiyun/cleanyourtv-app", GH_TOKEN="local-test-only",
                        GITHUB_SHA=self.sha, GITHUB_REF="refs/heads/main", GITHUB_REF_NAME="main",
                        GITHUB_RUN_NUMBER="44", GITHUB_RUN_ATTEMPT="1", GITHUB_RUN_ID="123",
                        GITHUB_SERVER_URL="https://github.com", GITHUB_STEP_SUMMARY=str(self.path / "summary"))
        source = WORKFLOW.read_text().split("      - name: Publish verified APK\n", 1)[1]
        self.script = textwrap.dedent(source.split("        run: |\n", 1)[1])

    def change_state(self, **changes):
        state = json.loads(self.state.read_text())
        state.update(changes)
        self.state.write_text(json.dumps(state))

    def run_publish(self, success=True):
        result = subprocess.run(["bash", "-c", self.script], cwd=self.path, env=self.env,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(self.state.read_text())

    def test_main_release_is_verified_then_published(self):
        state = self.run_publish()
        self.assertFalse(state["release"]["draft"])
        self.assertEqual(state["tag_sha"], self.sha)
        self.assertTrue(state["latest"])
        commands = [x[:2] for x in state["commands"]]
        self.assertLess(commands.index(["release", "download"]), commands.index(["release", "edit"]))
        self.assertEqual(state["release"]["tag_name"], "zh-v0.4.8-build.44.1")

    def test_feature_release_is_prerelease_not_latest(self):
        self.env.update(GITHUB_REF="refs/heads/feature/zh-cn-localization",
                        GITHUB_REF_NAME="feature/zh-cn-localization")
        state = self.run_publish()
        self.assertTrue(state["release"]["prerelease"])
        self.assertFalse(state["latest"])

    def test_older_build_does_not_replace_latest(self):
        self.change_state(head_sha="c" * 40)
        self.assertFalse(self.run_publish()["latest"])

    def test_published_release_retry_does_not_modify_assets(self):
        self.run_publish()
        self.change_state(commands=[])
        state = self.run_publish()
        for command in state["commands"]:
            self.assertNotIn(command[:2], [["release", "create"], ["release", "upload"], ["release", "edit"]])

    def test_corrupt_download_leaves_draft_unpublished(self):
        self.change_state(corrupt_download=True)
        self.assertTrue(self.run_publish(False)["release"]["draft"])

    def test_missing_draft_asset_is_resumed_without_overwrite(self):
        self.change_state(corrupt_download=True)
        state = self.run_publish(False)
        state["release"]["assets"] = [x for x in state["release"]["assets"] if x["name"] != "SHA256SUMS.txt"]
        self.change_state(release=state["release"], commands=[], corrupt_download=False)
        state = self.run_publish()
        uploads = [x for x in state["commands"] if x[:2] == ["release", "upload"]]
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0][3], "dist/SHA256SUMS.txt")

    def test_existing_different_asset_is_not_overwritten(self):
        self.run_publish()
        (self.path / "remote" / self.apk).write_bytes(b"different")
        self.change_state(commands=[])
        state = self.run_publish(False)
        self.assertFalse(any(x[:2] == ["release", "upload"] for x in state["commands"]))

    def test_wrong_tag_commit_fails(self):
        self.run_publish()
        self.change_state(tag_sha="d" * 40, commands=[])
        self.run_publish(False)

    def test_extra_remote_asset_is_not_published(self):
        self.change_state(corrupt_download=True)
        state = self.run_publish(False)
        state["release"]["assets"].append({"name": "unexpected.txt"})
        self.change_state(release=state["release"], corrupt_download=False)
        self.assertTrue(self.run_publish(False)["release"]["draft"])

    def test_forbidden_api_is_not_treated_as_missing(self):
        self.change_state(api_failure=True)
        state = self.run_publish(False)
        self.assertFalse(any(x[0] == "release" for x in state["commands"]))

    def test_unsafe_version_and_branch_are_rejected_before_api(self):
        self.env["VERSION"] = "0.4.8;echo bad"
        self.assertEqual(self.run_publish(False)["commands"], [])
        self.env.update(VERSION="0.4.8", GITHUB_REF="refs/heads/untrusted")
        self.assertEqual(self.run_publish(False)["commands"], [])

    def test_bad_local_hash_is_rejected_before_api(self):
        (self.dist / self.apk).write_bytes(b"changed")
        self.assertEqual(self.run_publish(False)["commands"], [])


if __name__ == "__main__":
    unittest.main()
