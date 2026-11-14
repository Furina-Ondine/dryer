import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from dryer.cli import _changed_files
from dryer.treesitter import parser_for


def test_bundled_language_pack_does_not_require_download(monkeypatch):
    parser = object()
    monkeypatch.setitem(
        sys.modules, "tree_sitter_language_pack", SimpleNamespace(get_parser=lambda _: parser)
    )
    parser_for.cache_clear()
    try:
        assert parser_for("python") is parser
    finally:
        parser_for.cache_clear()


def test_downloadable_language_pack_prepares_the_requested_language(monkeypatch):
    requests = []
    parser = object()
    pack = SimpleNamespace(
        download=requests.append,
        get_parser=lambda _: parser,
    )
    monkeypatch.setitem(sys.modules, "tree_sitter_language_pack", pack)
    parser_for.cache_clear()
    try:
        assert parser_for("java") is parser
        assert parser_for("java") is parser
        assert requests == [["java"]]
    finally:
        parser_for.cache_clear()


def _project(tmp_path):
    root = tmp_path / "项目 with spaces 🧪"
    root.mkdir()
    (root / "左 边🧪.clj").write_text(
        "(defn alpha [xs]\n  (let [ys (filter odd? xs)]\n    (map inc ys)))\n",
        encoding="utf-8",
    )
    (root / "右 边.clj").write_text(
        "(defn beta [items]\n  (let [kept (filter even? items)]\n    (map dec kept)))\n",
        encoding="utf-8",
    )
    return root


@pytest.mark.parametrize("encoding", ["utf-8", "gbk"])
@pytest.mark.parametrize("output", ["--text", "--edn"])
def test_module_cli_handles_unicode_paths_with_a_legacy_console(tmp_path, encoding, output):
    root = _project(tmp_path)
    env = dict(os.environ, PYTHONIOENCODING=f"{encoding}:strict", PYTHONUTF8="0")
    result = subprocess.run(
        [sys.executable, "-m", "dryer", "--root", str(root), "--min-lines", "3",
         "--min-nodes", "1", output],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    report = result.stdout.decode("utf-8")
    assert "左 边" in report and "右 边.clj" in report
    assert "🧪" in report
    assert "Wrote" in result.stderr.decode("utf-8")
    metrics = (root / ".metrics" / "dry.edn").read_text(encoding="utf-8")
    assert ':file "左 边🧪.clj"' in metrics
    assert ':file "右 边.clj"' in metrics


def test_changed_files_preserves_unicode_project_and_source_names(tmp_path):
    root = _project(tmp_path)
    subprocess.run(["git", "init", str(root)], capture_output=True, check=True)
    assert set(_changed_files(root)) == {
        (root / "左 边🧪.clj").resolve(),
        (root / "右 边.clj").resolve(),
    }


def test_native_launcher_preserves_arguments_and_exit_codes(tmp_path):
    root = _project(tmp_path)
    repository = Path(__file__).resolve().parents[1]
    if sys.platform == "win32":
        command = ["pwsh", "-NoProfile", "-File", str(repository / "dryer.ps1")]
    else:
        command = ["sh", str(repository / "dryer")]
    env = dict(os.environ, PYTHONIOENCODING="utf-8:strict")
    result = subprocess.run(
        [*command, "--root", str(root), "--min-lines", "3", "--min-nodes", "1"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert "左 边🧪.clj" in result.stdout.decode("utf-8")
    bad_option = subprocess.run(
        [*command, "--format", "invalid"], capture_output=True, env=env, check=False
    )
    assert bad_option.returncode == 2


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell launcher")
def test_powershell_launcher_preserves_native_arguments_and_the_callers_directory(tmp_path):
    shim = tmp_path / "native shim"
    shim.mkdir()
    (shim / "dryer.py").write_text(
        "import json, os, pathlib, sys\n"
        "pathlib.Path(os.environ['DRYER_ARGUMENTS']).write_text(\n"
        "    json.dumps({'args': sys.argv[1:], 'cwd': os.getcwd()}, ensure_ascii=False),\n"
        "    encoding='utf-8')\n"
        "raise SystemExit(37)\n",
        encoding="utf-8",
    )
    root = _project(tmp_path)
    capture = tmp_path / "arguments.json"
    env = dict(os.environ, PYTHONPATH=str(shim), DRYER_ARGUMENTS=str(capture))
    launcher = Path(__file__).resolve().parents[1] / "dryer.ps1"
    arguments = [
        "--root", str(root), "a&b; Write-Output pwned", "%PATH%", "$HOME", "bang!",
        "`literal", 'quoted"value', "C:\\trailing\\", "", "中文 🧪",
    ]
    result = subprocess.run(
        [shutil.which("pwsh") or "pwsh", "-NoProfile", "-File", str(launcher), *arguments],
        cwd=root,
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 37, result.stderr.decode("utf-8", errors="replace")
    import json

    captured = json.loads(capture.read_text(encoding="utf-8"))
    assert captured["args"] == arguments
    assert Path(captured["cwd"]) == root
