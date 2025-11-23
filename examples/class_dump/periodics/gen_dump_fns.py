import sys
sys.path.append('../../..')
import fct

from typing import Any

fa = fct.analysis
cindex = fct.clang.cindex
CursorKind = cindex.CursorKind
TranslationUnit = cindex.TranslationUnit

def execute(tu: TranslationUnit) -> list[fct.CppBuilder]:
    cpp = fct.CppBuilder("printables", ["<iostream>"])

    tagged_classes = fa.collect_tagged_decls(tu.cursor, ["printable"], ["struct_decl"])
    for cls in tagged_classes:
        fqn = fa.get_fully_qualified_name(cls)
        cpp.line(f"void print_class({fqn}& self)")
        cpp.body()
        cpp.line("std::cout")
        cpp.indent()
        cpp.line(f'<< "{fqn}\\n"')
        cpp.line(f'<< "{{\\n"')
        
        for f in fa.get_fields(cls):
            cpp.line(f'<< "    .{f.spelling} = " << self.{f.spelling} << ",\\n"')
        
        cpp.line(f'<< "}}" << std::endl;')
        cpp.unindent()
        cpp.unbody()

    return [cpp]