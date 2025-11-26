import sys
sys.path.append('../../..')
import fct


# TOOL CONFIG
# /


fa = fct.analysis
CppPieceBuilder = fct.CppPieceBuilder
cindex = fct.clang.cindex
CursorKind = cindex.CursorKind
TranslationUnit = cindex.TranslationUnit
ClangNode = fa.ClangNode


cpp = fct.CppBuilder("enum_info", ["<string>", "<sstream>"])


def collect_enum_members(enum: ClangNode) -> list[ClangNode]:
    return list(filter(
        lambda c: fa.kindof(c) == "enum_constant_decl",
        enum.get_children()
    ))


def gen_enum_info(fqn: str, enum: ClangNode) -> CppPieceBuilder:
    members = collect_enum_members(enum)

    repr_pb = CppPieceBuilder(f"static std::string repr({fqn} self)")
    repr_pb.line("switch (self)")
    repr_pb.body()
    
    for m in members:
        repr_pb.line(f"case {fqn}::{m.spelling}:")
        repr_pb.indent()
        repr_pb.line(f'return "{fqn}::{m.spelling}";')
        repr_pb.unindent()

    repr_pb.unbody()
    repr_pb.line(f'return (std::stringstream() << "{fqn}::(" << (int)self << ")").str();')

    pb = CppPieceBuilder()
    pb.add_flat(
f"""
template<>
struct EnumInfo<{fqn}>
{{
    static constexpr uint Count = {len(members)};

    {repr_pb.build()}
}};
""")

    return pb


def emit_enum_info_to_cb(cls: ClangNode) -> None:
    global cpp

    fqn = fa.get_fully_qualified_name(cls)
    cpp.add(fqn, gen_enum_info(fqn, cls))


def execute(tu: TranslationUnit) -> list[fct.CppBuilder]:
    global cpp

    unbound_enum_info = CppPieceBuilder()
    unbound_enum_info.add_flat(
r"""
template<typename EnumT>
struct EnumInfo
{
    
};
""")
    cpp.add("unbound_enum_info", unbound_enum_info)

    tagged_enums = fa.collect_tagged_decls(tu.cursor, ["enum_info"], ["enum_decl"])
    for en in tagged_enums:
        emit_enum_info_to_cb(en)

    return [cpp]
