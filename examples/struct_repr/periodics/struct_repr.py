import sys
sys.path.append('../../..')
import fct


# TOOL CONFIG

SKIP_FIELDS_OF_UNREGISTERED_STRUCT_TYPES = False
"""
if false, fields of type struct (but struct without "struct_repr" note)
are represented as `struct_name(...)` instead of detailed repr (field-by-field)
"""


fa = fct.analysis
CppPieceBuilder = fct.CppPieceBuilder
cindex = fct.clang.cindex
CursorKind = cindex.CursorKind
TranslationUnit = cindex.TranslationUnit
ClangNode = fa.ClangNode


cpp = fct.CppBuilder("repr", ["<string>", "<sstream>"])
tagged_structs: list[ClangNode]


def emit_field_repr_to_pb(pb: CppPieceBuilder, f: ClangNode) -> None:
    global tagged_structs

    fvalue = f"self.{f.spelling}"

    alias_type = fa.get_fully_qualified_name(f.type.get_declaration())
    t = f.type.get_canonical()
    tk = fa.typekind(t)

    match tk:
        case "bool":
            pb.add_flat(f'({fvalue} ? "true" : "false")')

        case "uchar" | "schar" | "char_s" | "char_u":
            match alias_type:
                case "int8_t":
                    pb.add_flat(f"int({fvalue})")
                case "uint8_t":
                    pb.add_flat(f"uint({fvalue})")
                case _:
                    pb.add_flat(f"'\\''; normalize_char(ss, {fvalue}); ss << '\\''")
    
        case "pointer":
            # c string
            if fa.typekind(t.get_pointee()) in ["char_s", "char_u"]:
                pb.add_flat(f"repr_s(std::string({fvalue}))")
            else:
                # generic pointer
                # TODO: pointers to struct should be fully printed with `&<...>`
                #       but pay attention to infinite recursion
                pb.add_flat(f"(void*){fvalue}")
    
        case "record":
            if alias_type == "std::string" and t.spelling == "std::basic_string<char>":
                pb.add_flat(f'"std::string(" << repr_s({fvalue}) << ")"')
            else:
                decl = t.get_declaration()
                if decl not in tagged_structs and SKIP_FIELDS_OF_UNREGISTERED_STRUCT_TYPES:
                    pb.add_flat(f'"{fa.get_fully_qualified_name(decl)}(...)"')
                else:
                    emit_struct_repr_to_cb(decl)
                    pb.add_flat(f'repr({fvalue}, indent + 4)')
        
        case _:
            # delegate the type binding to cout
            # TODO: remove this case, handle most manually and raise error with unhandled types
            #       (for example, add all ints, floats, etc)
            pb.add_flat(fvalue)


def gen_struct_repr(fqn: str, cls: ClangNode) -> CppPieceBuilder:
    needs_inline = fa.hastag(cls, "struct_repr_inline")
    pb = CppPieceBuilder(
        f'std::string repr({fqn} const& self, size_t indent)',
        head=f'std::string repr({fqn} const& self, size_t indent = 0)'
    )

    if needs_inline:
        pb.line('char const* sindent = "";')
        pb.line('char const* padding = "";')
        pb.line('char const* fields_sep = " ";')
    else:
        pb.line('std::string sindent = std::string(PRECOMPUTED_INDENT, indent);')
        pb.line('char const* padding = "    ";')
        pb.line('char const* fields_sep = "\\n";')

    pb.line("std::stringstream ss;")
    pb.line("ss")
    pb.indent()
    pb.line(f'<< "{fqn}" << fields_sep')
    pb.line(f'<< sindent << "{{" << fields_sep')
    
    for f in fa.get_fields(cls):
        pb.add_indented(f'<< sindent << padding << ".{f.spelling} = " << ')
        emit_field_repr_to_pb(pb, f)
        pb.add_flat(' << "," << fields_sep')
        pb.line()
    
    pb.line(f'<< sindent << "}}";')
    pb.unindent()
    pb.line(f'return ss.str();')

    return pb


def emit_struct_repr_to_cb(cls: ClangNode) -> None:
    global cpp

    fqn = fa.get_fully_qualified_name(cls)
    if cpp.has(fqn):
        return

    cpp.add(fqn, gen_struct_repr(fqn, cls))


def execute(tu: TranslationUnit) -> list[fct.CppBuilder]:
    global cpp

    repr_s = CppPieceBuilder()
    repr_s.add_flat(
r"""
void normalize_char(std::stringstream& ss, char c)
{
    switch (c) {
        case '"':  ss << "\\\""; break;
        case '\\': ss << "\\\\"; break;
        case '\n': ss << "\\n";  break;
        case '\t': ss << "\\t";  break;
        case '\r': ss << "\\r";  break;
        case '\0': ss << "\\0";  break;
        default:   ss << c;      break;
    }
}

std::string repr_s(std::string const& s)
{
    std::stringstream ss;
    ss << "\"";
    for (char c : s)
        normalize_char(ss, c);
        
    ss << "\"";
    return ss.str();
}
""")
    cpp.add("std::string and char repr", repr_s)

    # static precomputed indent
    cpp.add(
        "PRECOMPUTED_INDENT",
        CppPieceBuilder(f'static char const PRECOMPUTED_INDENT[] = "{" " * (2**8 - 1)}"', is_def=False)
    )

    global tagged_structs
    tagged_structs = fa.collect_tagged_decls(tu.cursor, ["struct_repr", "struct_repr_inline"], ["struct_decl"])

    for cls in tagged_structs:
        emit_struct_repr_to_cb(cls)

    return [cpp]
