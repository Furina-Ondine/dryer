import pytest

from dryer.cli import run
from dryer.discover import iter_source_files, language_of
from dryer.extract import entries_in_source
from dryer.scan import find_duplicates


def entries(source: str, file: str = "sample.cs"):
    found, warning = entries_in_source("csharp", source, file, file)
    assert warning is None
    return found


def score(left: str, right: str) -> float:
    found = find_duplicates(entries(left, "left.cs") + entries(right, "right.cs"), 0.0)
    assert len(found) == 1
    return found[0].score


def test_csharp_extracts_executable_members_and_keeps_nested_code_inside():
    source = """\
abstract class Box {
  abstract int Declared(int value);
  int Auto { get; set; }
  Box(int value) : base(value) { Save(value); }
  ~Box() { Dispose(); }
  int Method(int value) {
    int Local(int item) => item + 1;
    System.Func<int, int> callback = item => item + 2;
    return Local(value);
  }
  int Expression(int value) => value + 1;
  int Property => Expression(1);
  int this[int index] => Expression(index);
  int Explicit {
    get { return Expression(1); }
    set => Save(value);
    init { Save(value); }
  }
  public static Box operator +(Box left, Box right) => left;
  public static implicit operator int(Box value) => 1;
  event Action Changed { add => Subscribe(value); remove { Unsubscribe(value); } }
}
"""
    assert [(entry.start_line, entry.end_line) for entry in entries(source)] == [
        (4, 4), (5, 5), (6, 10), (11, 11), (12, 12), (13, 13),
        (15, 15), (16, 16), (17, 17), (19, 19), (20, 20), (21, 21), (21, 21),
    ]


def test_csharp_renamed_locals_and_members_have_identical_structure():
    left = """class Left {
  int Alpha(IEnumerable<int> numbers) {
    var selected = numbers.Where<int>(odd);
    selected.Add(this.total);
    return selected.Sum();
  }
}"""
    right = """class Right {
  int Beta(IEnumerable<int> items) {
    var kept = items.Where<int>(even);
    kept.Add(this.count);
    return kept.Sum();
  }
}"""
    assert score(left, right) == 1.0
    printed = " ".join(entries(left)[0].fingerprints)
    for callee in ("Where", "Add", "Sum"):
        assert callee in printed
    assert "total" not in printed


@pytest.mark.parametrize("call", ["Select<int>(value)", "Filter<int>(value, value)", "Other.Create(value)"])
def test_csharp_distinct_called_operations_keep_different_fingerprints(call):
    left = "class C { int First(int value) => Filter<int>(value); }"
    right = f"class C {{ int Second(int value) => {call}; }}"
    assert score(left, right) < 1.0


def test_csharp_constructed_type_is_kept_but_type_arguments_are_normalized():
    left = "class C { object First() => new List<int>(); }"
    renamed = "class C { object Second() => new List<string>(); }"
    other = "class C { object Third() => new HashSet<int>(); }"
    assert score(left, renamed) == 1.0
    assert score(left, other) < 1.0


@pytest.mark.parametrize("literal", ['@"text"', '"""raw"""', "'x'", "1.5", "true", "null"])
def test_csharp_literals_do_not_change_the_normalized_shape(literal):
    left = "class C { object First() => 123; }"
    right = f"class C {{ object Second() => {literal}; }}"
    assert score(left, right) == 1.0


def test_csharp_different_control_flow_is_not_reported_as_a_duplicate():
    simple = "class C { int First(int value) => value + 1; }"
    loop = "class C { int Second(int value) { while (value > 0) { value--; } return value; } }"
    assert score(simple, loop) < 0.8


def test_csharp_source_discovery_leaves_out_dotnet_build_outputs(tmp_path):
    for name in ("src/Real.cs", "bin/Built.cs", "obj/Generated.cs", "TestResults/Probe.cs",
                 "src/Widget.g.cs", "src/Widget.g.i.cs", "src/Widget.Designer.cs"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("class C {}", encoding="utf-8")
    assert language_of("Source.cs") == "csharp"
    assert language_of("Widget.g.cs") is None
    assert [path.relative_to(tmp_path).as_posix() for path in iter_source_files([tmp_path])] == ["src/Real.cs"]


def test_csharp_cli_reports_structural_duplicates_and_writes_csharp_metrics(tmp_path, capsys):
    for name, method, variable in (("left.cs", "Alpha", "numbers"), ("right.cs", "Beta", "items")):
        (tmp_path / name).write_text(
            f"class C {{\n int {method}(int[] {variable}) {{\n"
            f"  var kept = Filter({variable});\n  var mapped = Map(kept);\n"
            "  return Count(mapped);\n }\n}\n", encoding="utf-8",
        )
    assert run(["--root", str(tmp_path), "--threshold", "0.8"]) == 0
    captured = capsys.readouterr()
    assert "DUPLICATE score=1.00" in captured.out
    assert "left.cs:2-6" in captured.out
    assert "right.cs:2-6" in captured.out
    metrics = (tmp_path / ".metrics" / "dry.edn").read_text(encoding="utf-8")
    assert ':language "csharp"' in metrics


def test_csharp_top_level_statements_form_one_candidate_with_local_functions_inside():
    source = """using System;
var input = Read();
int Adjust(int value) => value + 1;
var callback = (int value) => value + 2;
Console.WriteLine(Adjust(input));
class C {
  int Member() => 1;
}
"""
    assert [(entry.start_line, entry.end_line) for entry in entries(source)] == [(2, 5), (7, 7)]
    renamed = source.replace("input", "argument").replace("callback", "transform").replace("value", "item")
    left = entries(source, "left.cs")[0]
    right = entries(renamed, "right.cs")[0]
    assert find_duplicates([left, right], 0.99)[0].score == 1.0
    assert entries("using System;\nclass C { int Automatic { get; set; } }\n") == []


@pytest.mark.parametrize("operation", ["Filter(value)", "Filter<int>(value)"])
def test_csharp_conditional_calls_preserve_called_operations(operation):
    source = f"class C {{ object First(object source, int value) => source?.{operation}; }}"
    renamed = source.replace("First", "Second").replace("source", "items").replace("value", "item")
    changed = source.replace("Filter", "Select")
    assert score(source, renamed) == 1.0
    assert score(source, changed) < 1.0
