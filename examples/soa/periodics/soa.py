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


cpp = fct.CppBuilder("soa", ["<stddef.h>"])


def gen_soa(fqn: str, cls: ClangNode) -> CppPieceBuilder:
    pb = CppPieceBuilder()

    pb.add_flat(
f"""
template<size_t Capacity>
struct Soa<{fqn}, Capacity>
{{
"""
    )

    full_getter = CppPieceBuilder(f"inline {fqn} get(size_t idx)")
    full_setter = CppPieceBuilder(f"inline void set(size_t idx, {fqn} value)")

    full_getter.line(f"{fqn} r;")

    for c in cls.get_children():
        if fa.kindof(c) != "field_decl":
            continue

        ftype = c.type.spelling
        fname = c.spelling
        farrname = f"arr_{fname}"

        # field
        pb.line()
        pb.line(f"// array for field `{fqn}.{fname}`")
        pb.line(f"{ftype} {farrname}[Capacity];")
        
        # nth getter for field
        pb.line(f"inline {ftype} get_{fname}(size_t idx)")
        pb.body()
        pb.line(f"return {farrname}[idx];")
        pb.unbody()
        
        # nth setter for field
        pb.line(f"inline void set_{fname}(size_t idx, {ftype} value)")
        pb.body()
        pb.line(f"{farrname}[idx] = value;")
        pb.unbody()

        # contribution to full getter
        full_getter.line(f"r.{fname} = get_{fname}(idx);")
        # contribution to full setter
        full_setter.line(f"set_{fname}(idx, value.{fname});")
    
    full_getter.line(f"return r;")

    pb.add_flat(
f"""
    // full getter
{full_getter.build()}

    // full setter
{full_setter.build()}
}};
"""
    )

    return pb


def emit_enum_info_to_cb(cls: ClangNode) -> None:
    global cpp

    fqn = fa.get_fully_qualified_name(cls)
    cpp.add(fqn, gen_soa(fqn, cls))


def execute(tu: TranslationUnit) -> list[fct.CppBuilder]:
    global cpp

    cpp.add("unbound_soa", fct.piece(
"""
template<typename StructT, size_t capacity>
struct Soa
{
    
};
"""
    ))

    tagged_enums = fa.collect_tagged_decls(tu.cursor, ["soa"], ["struct_decl"])
    for en in tagged_enums:
        emit_enum_info_to_cb(en)

    return [cpp]
