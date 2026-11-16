"""Contracts for normalized call shapes from actual source syntax."""

import pytest

from dryer.astnorm import normalize
from dryer.shape import pr
from dryer.treesitter import descendants, parse


@pytest.mark.parametrize(('source', 'kind', 'expected'), [
    ('class C { void f() { target.call(value); } }', 'method_invocation',
     '[:method_invocation :symbol [:symbol "call"] [:argument_list :symbol]]'),
    ('class C { void f() { new Box(value) { int n; }; } }', 'object_creation_expression',
     '[:object_creation_expression [:symbol "Box"] [:argument_list :symbol] '
     '[:class_body [:field_declaration [:integral_type] [:variable_declarator :symbol]]]]'),
])
def test_java_calls_normalize_each_part_once(source, kind, expected):
    data, tree = parse(source, 'java')
    assert not tree.root_node.has_error
    call = next(node for node in descendants(tree.root_node) if node.type == kind)
    assert pr(normalize(call, data)) == expected
