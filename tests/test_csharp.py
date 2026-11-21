import subprocess
import sys
from pathlib import Path

import pytest

from dryer.cli import parse_args, run, select_files
from dryer.extract import entries_in_source


def extract(source: str, file: str = "sample.cs"):
    entries, warning = entries_in_source("csharp", source, file, file)
    assert warning is None
    return entries


def fingerprints(source: str) -> frozenset[str]:
    entry, = extract(source)
    return entry.fingerprints


def test_reports_shared_executable_units():
    source = """\
using System;
var input = Read();
int Local(int value) => value + 1;
Write(Local(input));
abstract class C {
  abstract int Abstract();
  int Auto { get; set; }
  C() { Save(); }
  int M(int input) {
    int Nested() => input;
    return Nested();
  }
  int Value => Read();
  int Other { get { return Read(); } }
}
"""
    assert [(entry.start_line, entry.end_line) for entry in extract(source)] == [
        (2, 4), (8, 8), (9, 12), (13, 13), (14, 14),
    ]


@pytest.mark.parametrize("call", [
    "items.Filter(input)", "items?.Filter(input)",
    "items.Filter<int>(input)", "items?.Filter<int>(input)",
])
def test_preserves_called_names_but_not_receiver_or_argument_names(call):
    source = f"class C {{ object Run(int input) => {call}; }}"
    normalized = fingerprints(source)
    assert '[:symbol "Filter"]' in normalized
    renamed = source.replace("items", "values").replace("input", "value").replace("Run", "Work")
    assert fingerprints(renamed) == normalized
    assert fingerprints(source.replace("Filter", "Select")) != normalized


def test_scan_reports_duplicate_candidates(tmp_path: Path, capsys):
    source = 'class C { int M(int value) { return Transform(value); } }'
    (tmp_path / "left.cs").write_text(source, encoding="utf-8")
    (tmp_path / "right.cs").write_text(source.replace("value", "input"), encoding="utf-8")
    assert run(["--root", str(tmp_path), "--min-lines", "1", "--min-nodes", "1"]) == 0
    assert "DUPLICATE score=1.00" in capsys.readouterr().out
    assert ':language "csharp"' in (tmp_path / ".metrics" / "dry.edn").read_text(encoding="utf-8")


@pytest.mark.parametrize("changed", [False, True])
def test_csharp_discovery_keeps_other_languages_in_same_directories(tmp_path: Path, changed):
    for name in ("src/Keep.cs", "src/SkipTests.cs", "bin/Skip.cs", "bin/keep.py",
                 "Unit.Tests/Skip.cs", "Unit.Tests/keep.py", "src/Generated.g.cs"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    args = ["--root", str(tmp_path)]
    if changed:
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        args.append("--changed")
    options = parse_args(args)
    assert [path.relative_to(tmp_path).as_posix() for path in select_files(options)] == [
        "Unit.Tests/keep.py", "bin/keep.py", "src/Keep.cs",
    ]
    explicit = parse_args(["--root", str(tmp_path), "src/SkipTests.cs"])
    assert select_files(explicit) == [tmp_path / "src" / "SkipTests.cs"]


def test_invalid_csharp_is_diagnosed_without_writing_metrics(tmp_path: Path, capsys):
    (tmp_path / "broken.cs").write_text("class C { int Broken( => 1; }", encoding="utf-8")
    assert run(["--root", str(tmp_path)]) == 1
    error = capsys.readouterr().err
    assert "broken.cs" in error
    assert "Tree-sitter could not parse C# syntax" in error
    assert not (tmp_path / ".metrics" / "dry.edn").exists()


def test_csharp_dependency_is_loaded_only_for_csharp(tmp_path, capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "crapper", None)
    (tmp_path / "okay.py").write_text("def f(): return 1", encoding="utf-8")
    assert run(["--root", str(tmp_path)]) == 0
    capsys.readouterr()
    (tmp_path / "source.cs").write_text("class C {}", encoding="utf-8")
    assert run(["--root", str(tmp_path)]) == 1
    assert "C# analysis requires Crapper with C# support" in capsys.readouterr().err
