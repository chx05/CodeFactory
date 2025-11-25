import sys
sys.path.append('../../..')
import fct

from typing import Any

fa = fct.analysis
CppPieceBuilder = fct.CppPieceBuilder
cindex = fct.clang.cindex
CursorKind = cindex.CursorKind
TranslationUnit = cindex.TranslationUnit
ClangNode = fa.ClangNode


cpp = fct.CppBuilder("printables", ["<iostream>", "<string>", "<sstream>"])


def emit_field_print_to_pb(pb: CppPieceBuilder, f: ClangNode) -> None:
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
                    pb.add_flat(f"'\\'' << {fvalue} << '\\''")
    
        case "pointer":
            # c string
            if fa.typekind(t.get_pointee()) in ["char_s", "char_u"]:
                pb.add_flat(f"repr({fvalue})")
            else:
                # generic pointer
                # TODO: pointers to struct should be fully printed with `&<...>`
                pb.add_flat(f"(void*){fvalue}")
    
        case "record":
            if alias_type == "std::string" and t.spelling == "std::basic_string<char>":
                pb.add_flat(f'"std::string(" << repr({fvalue}) << ")"')
            else:
                # TODO
                #emit_printing_fn(t.get_declaration())
                pb.add_flat(f'"{alias_type}(...)"')
        
        case _:
            # delegate the type binding to cout
            # TODO: remove this case, handle most manually and raise error with unhandled types
            #       (for example, add all ints, floats, etc)
            pb.add_flat(fvalue)


def gen_printing_fn(fqn: str, cls: ClangNode) -> CppPieceBuilder:
    pb = CppPieceBuilder(f"void print_class({fqn}& self)")
    pb.line("std::cout")
    pb.indent()
    pb.line(f'<< "{fqn}\\n"')
    pb.line(f'<< "{{\\n"')
    
    for f in fa.get_fields(cls):
        pb.add_indented(f'<< "    .{f.spelling} = " << ')
        emit_field_print_to_pb(pb, f)
        pb.add_flat(' << ",\\n"')
        pb.line()
    
    pb.line(f'<< "}}" << std::endl;')
    pb.unindent()

    return pb


def emit_printing_fn(cls: ClangNode) -> None:
    global cpp

    fqn = fa.get_fully_qualified_name(cls)
    cpp.add(gen_printing_fn(fqn, cls))


def execute(tu: TranslationUnit) -> list[fct.CppBuilder]:
    global cpp

    repr_builder = CppPieceBuilder("std::string repr(const std::string& s)")
    repr_builder.add_flat(r"""
        std::stringstream ss;
        ss << "\""; // Apre virgolette
        for (char c : s) {
            switch (c) {
                case '"':  ss << "\\\""; break;
                case '\\': ss << "\\\\"; break;
                case '\n': ss << "\\n"; break;
                case '\t': ss << "\\t"; break;
                case '\r': ss << "\\r"; break;
                case '\0': ss << "\\0"; break;
                default:   ss << c; break;
            }
        }
        ss << "\""; // Chiude virgolette
        return ss.str();
""")
    cpp.add(repr_builder)

    tagged_classes = fa.collect_tagged_decls(tu.cursor, ["printable"], ["struct_decl"])
    for cls in tagged_classes:
        emit_printing_fn(cls)

    return [cpp]
