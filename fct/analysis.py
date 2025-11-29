# This module is part of fct.py, it will be accessible from there,
# this servs as an helper module to interact with clang syntax tree

from clang.cindex import CursorKind
from typing import Any


ClangNode = Any


STATIC_CONTAINERS_KINDS = [
    "class_decl",
    "struct_decl",
    "union_decl",
    "namespace",
    "translation_unit",
    "linkage_spec", # extern "C" blocks
]


def collect_tagged_decls(root: ClangNode, tags: list[str], accepted_node_kinds: list[str]) -> list[ClangNode]:
    """
    Recursively collects all nodes that are decls and tagged with at least one of the provided tags.

    tags
        must be all lower case, tags are case insensitive
    
    accepted_node_kinds
        must be all decl kinds
    """

    assert len(tags) > 0

    for k in accepted_node_kinds:
        if not k.endswith('_decl'):
            raise ValueError(f"Node kind {repr(k)} is not a decl node kind, therefore it doesn't support tagging")
    
    return _collect_tagged_nodes(root, tags, accepted_node_kinds)


def _collect_tagged_nodes(node: ClangNode, tags: list[str], kinds: list[str]) -> list[ClangNode]:
    k = kindof(node)
    is_static_container = k in STATIC_CONTAINERS_KINDS

    if k not in kinds and not is_static_container:
        return []

    collected = []
    is_tagged_right = False

    for c in node.get_children():
        if not is_tagged_right and kindof(c) == "annotate_attr":
            is_tagged_right = c.displayname.lower() in tags

        if is_static_container:
            collected.extend(_collect_tagged_nodes(c, tags, kinds))
    
    if k in kinds and is_tagged_right:
        collected.append(node)
    
    return collected


def get_fully_qualified_name(node: ClangNode, use_spelling_instead: bool = False) -> str:
    return "::".join(get_fully_qualified_name_parts(node, use_spelling_instead))


def get_fully_qualified_name_parts(node: ClangNode, use_spelling_instead: bool = False) -> list[str]:
    parts = []
    
    while node and is_decl(node):
        parts.append(node.spelling if use_spelling_instead else node.displayname)
        node = node.semantic_parent
    
    return list(reversed(parts))


def is_decl(node: ClangNode) -> bool:
    return node.kind.is_declaration()


def kindof(node: ClangNode) -> str:
    return node.kind.name.lower()


def get_fields(node: ClangNode) -> list[ClangNode]:
    assert kindof(node) in ["class_decl", "struct_decl"]
    fields = []

    for c in node.get_children():
        if kindof(c) == "field_decl":
            fields.append(c)

    return fields


def typekind(clang_type: Any) -> str:
    return clang_type.kind.name.lower()


def hastag(node: ClangNode, tag: str) -> bool:
    return len(hastags(node, [tag])) == 1


def hastags(node: ClangNode, tags: list[str]) -> list[str]:
    matching_tags = []
    found_tags = collect_tags(node)
    for t in tags:
        if t in found_tags:
            matching_tags.append(t)
    
    return matching_tags


def collect_tags(node: ClangNode) -> list[str]:
    tags = []
    for c in node.get_children():
        if kindof(c) == "annotate_attr":
            tags.append(c.displayname.lower())

    return tags            
