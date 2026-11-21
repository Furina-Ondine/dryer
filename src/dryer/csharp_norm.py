"""Normalize Roslyn syntax according to Dryer's structural fingerprint rules."""

from functools import partial

from dryer.astnorm import _PENDING, _normalize
from dryer.shape import K
from dryer.treesitter import node_text


def _leaf(data, node, mode, _head):
    roles = node.roles
    if "metadata" in roles:
        return None
    if mode == "callee" and ("identifier" in roles or node.type == "PredefinedType"):
        return [K("symbol"), node_text(data, node)]
    if "identifier" in roles:
        return K("symbol")
    if "literal" in roles:
        return K("literal")
    if "operator" in roles:
        return [K("symbol"), node_text(data, node)]
    return _PENDING if node.is_named else None


def _grouped(node):
    return "group" in node.roles and len(node.named_children) == 1


def _callee_jobs(node):
    roles = node.roles
    if "member_access" in roles or node.type == "SuppressNullableWarningExpression":
        names = node.named_children
        target = names[-1] if names else None
        return [(child, "callee" if child is target else "norm", False) for child in node.children]
    if "name_path" in roles:
        return [
            (child, "callee" if child.roles.intersection({"identifier", "name_path"}) else "norm", False)
            for child in node.children
        ]
    return None


def _jobs(node, mode, head):
    if _grouped(node):
        return [(node.named_children[0], mode, head)]

    if mode == "callee":
        jobs = _callee_jobs(node)
        if jobs is not None:
            return jobs
    roles = node.roles
    return [
        (child, "callee" if "call" in roles and "callee" in child.roles else "norm", False)
        for child in node.children
    ]


def _assemble(node, mode, head, cache):
    values = [cache[(id(child), child_mode, child_head)] for child, child_mode, child_head in _jobs(node, mode, head)]
    if _grouped(node):
        return values[0]
    return [K(node.type), *(value for value in values if value is not None)]


def normalize(node, data: bytes):
    return _normalize(node, leaf=partial(_leaf, data), jobs=_jobs, assemble=_assemble)
