from pathlib import Path
import shutil
import os
import subprocess
import sys


def test_missing_csharp_frontend_explains_the_local_dependency(tmp_path):
    source = Path(__file__).resolve().parents[1] / "src" / "dryer"
    package = tmp_path / "standalone" / "src" / "dryer"
    shutil.copytree(source, package, ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "sample.cs").write_text("class C { int M() => 1; }", encoding="utf-8")
    script = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from dryer.cli import run; "
        "raise SystemExit(run(['--root', sys.argv[2], 'sample.cs']))"
    )
    result = subprocess.run(
        [sys.executable, "-S", "-c", script, str(package.parent), str(tmp_path)],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", check=False,
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "C# analysis requires the matching Crapper compiler front end" in result.stderr
    assert "Install Crapper in this environment or clone it next to Dryer" in result.stderr


def test_sibling_frontend_takes_precedence_after_broken_installed_package(tmp_path, monkeypatch):
    import crapper
    from dryer import crapper_link

    sibling = Path(crapper.__file__).resolve().parent.parent
    monkeypatch.setattr(crapper_link, '_sibling_src', lambda: sibling)
    broken = tmp_path / 'crapper'
    broken.mkdir()
    (broken / '__init__.py').write_text('raise ImportError("broken installation")', encoding='utf-8')
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, 'crapper', raising=False)
    monkeypatch.delitem(sys.modules, 'crapper.frontend', raising=False)
    document = crapper_link.parse_document('class Fallback { int Run() => 1; }', 'csharp', 'Fallback.cs')
    assert [(unit.namespace, unit.name) for unit in document.units] == [('Fallback', 'Run')]


def test_missing_frontend_raises_actionable_error_in_current_process(tmp_path, monkeypatch):
    import builtins
    import pytest
    from dryer import crapper_link

    real_import = builtins.__import__
    def without_crapper(name, *args, **kwargs):
        if name == 'crapper':
            raise ImportError('unavailable')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', without_crapper)
    monkeypatch.setattr(crapper_link, '_sibling_src', lambda: tmp_path / 'missing')
    with pytest.raises(ImportError, match='Install Crapper in this environment or clone it next to Dryer'):
        crapper_link.parse_document('class C {}', 'csharp', 'C.cs')


def test_top_level_statements_remain_a_single_ordered_candidate():
    from dryer.extract import entries_in_source

    found, warning = entries_in_source('csharp', 'Read();\nWrite();\n', 'sample.cs', 'sample.cs')
    assert warning is None
    assert len(found) == 1
    assert ('[:executable_unit [:GlobalStatement [:ExpressionStatement [:InvocationExpression '
            '[:symbol "Read"] [:ArgumentList]]]] [:GlobalStatement [:ExpressionStatement '
            '[:InvocationExpression [:symbol "Write"] [:ArgumentList]]]]]') in found[0].fingerprints


def test_single_top_level_statement_keeps_its_native_root():
    from dryer.extract import entries_in_source

    found, warning = entries_in_source('csharp', 'Read();', 'sample.cs', 'sample.cs')
    assert warning is None
    assert len(found) == 1
    assert ':executable_unit' not in found[0].fingerprints
    assert '[:GlobalStatement [:ExpressionStatement [:InvocationExpression [:symbol "Read"] [:ArgumentList]]]]' in found[0].fingerprints
