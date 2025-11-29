import os
import sys
import subprocess
import clang
import clang.cindex
import clang.enumerations
import clang.native
import analysis
import shutil

from types import ModuleType
from genericpath import isdir, isfile
from importlib import util
from os.path import join as joinpath
from pathlib import Path
from glob import glob
from dataclasses import dataclass, field as dcfield


def get_prjname() -> str:
    prj_dir = Path(os.getcwd())
    return prj_dir.parts[-1]


class FctError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)

    @property
    def msg(self) -> str:
        return self.args[0]


@dataclass
class BuildOptions:
    prjname: str = dcfield(default_factory=get_prjname)
    output_folder: str = "o"
    gen_folder: str = "g"
    templs_folder: str = "t"
    source: str = "main.cpp"
    # index pointing to self.sources
    entry_source: int = 0

    cc: str = "gcc"
    cpp: bool = True
    flags: list[str] = dcfield(default_factory=lambda:[
        "-std=c++23",
        "-Wno-attributes",
        "-I/usr/include/c++/11",
        "-I/usr/include/x86_64-linux-gnu/c++/11",
        "-I/usr/include/c++/11/backward",
        "-I/usr/lib/gcc/x86_64-linux-gnu/11/include",
        "-I/usr/local/include",
        "-I/usr/include/x86_64-linux-gnu",
        "-I/usr/include",
    ])

    periodics: list[ModuleType] = dcfield(default_factory=list)
    manuals: list[ModuleType] = dcfield(default_factory=list)

    run_returncode: int | None = None
    use_exceptions_instead_of_exit: bool = False


args: list[str] = []
args_i: int = 0

bopt = BuildOptions()


HELP = """
Commands
    Help
        Shows this message
    Build
        Runs the build script to the end
    Run
        Builds and runs the executable
    Apply(tool_name)
        Runs a manual tool named <tool_name>.py, use `.` to apply all manuals
    Prepare(header_name)
        Creates empty header <header_name>.g.h in folder `g/`
    Clear
        Removes the cached contents from `g/` and `o/` folders
""".strip()


TEMPLATE_HEADER = """
#pragma once

<includes>

namespace g
{
<content>
}
""".strip()


PREPARED_HEADER = TEMPLATE_HEADER.replace("<includes>", "").replace("<content>", "")


def install_tools(periodics: list[ModuleType], manuals: list[ModuleType]) -> None:
    """
    periodics:
        either a path to a folder containing the tools or a list of the tools filenames.
        these are the tools that run before every compilation `fct build` or any command building under the hood

    manuals:
        either a path to a folder containing the tools or a list of the tools filenames.
        tools that run only when manually applied with command `fct apply tool_name`
    """

    global bopt

    bopt.periodics.extend(periodics)
    bopt.manuals.extend(manuals)


def run_argv() -> None:
    """
    runs the requests contained in argv.
    eventual generations will be outputed to `g/` folder.
    """

    global bopt

    bopt.run_returncode = None
    make_dirs()

    global args
    global args_i
    args = sys.argv[1:]
    
    match fetch_arg("Use `fct help`."):
        case "help":
            print(HELP)
        
        case "build":
            build()
        
        case "run":
            print("Building:")
            out_path = build()
            if out_path != None:
                print("Running:")
                p = subprocess.run([out_path] + args[args_i:])
                bopt.run_returncode = p.returncode
        
        case "prepare":
            header_name = fetch_arg("Expected header name")
            header_path = joinpath(bopt.gen_folder, header_name + ".g.h")

            if isfile(header_path):
                fa = fetch_arg("Header already exists, use `fct prepare <header_name> force` instead")
                if fa != "force":
                    error(f"Expected 'force' instead of {repr(fa)}")

            with open(header_path, "w") as h:
                h.write(PREPARED_HEADER)
                h.write("\n")
        
        case "apply":
            tool_name = fetch_arg("Expected tool name")

            if tool_name == ".":
                execute_tools(bopt.manuals)
            else:
                found_ones = list(filter(lambda m: m.__name__ == tool_name, bopt.manuals))

                if len(found_ones) == 0:
                    error("No manual tool was found, check the installed ones")

                execute_tools(found_ones)
        
        case "clear":
            remove_dirs()
            make_dirs()

        case _:
            error("Command not found")
    

def remove_dirs() -> None:
    global bopt

    shutil.rmtree(bopt.output_folder, ignore_errors=True)
    shutil.rmtree(bopt.gen_folder, ignore_errors=True)


def make_dirs() -> None:
    global bopt

    os.makedirs(bopt.output_folder, exist_ok=True)
    os.makedirs(bopt.gen_folder, exist_ok=True)


def fetch_arg(err_msg: str) -> str:
    return fetch_arg_case_sensitive(err_msg).lower()


def fetch_arg_case_sensitive(err_msg: str) -> str:
    global args
    global args_i

    if args_i >= len(args):
        error(err_msg)

    arg = args[args_i]
    args_i += 1

    return arg


def cmd(s: str) -> int:
    """
    runs a manual shell command
    """
    
    return os.system(s)


def error(msg: str) -> None:
    global bopt

    if bopt.use_exceptions_instead_of_exit:
        raise FctError(msg)

    print(f"Error: {msg}")
    sys.exit(1)


def execute_tools(tools: list[ModuleType]) -> None:
    global bopt

    if len(tools) == 0:
        return

    try:
        index = clang.cindex.Index.create()
        tu = index.parse(bopt.source, bopt.flags)
    except clang.cindex.TranslationUnitLoadError:
        error("Clang Call Failed")
        return # unreachable

    #if tu.diagnostics:
    #    print("Errors:")
    #    for diag in tu.diagnostics:
    #        print(diag)
    #
    #    error("Compilation Failed")

    # we execute the scripts even if there are analysis errors
    # from libclang, this is a wanted behavior because those errors
    # might be caused by a missing symbol, and that symbol may be missing
    # because it has still to be generated by one of these periodic scripts
    for tool in tools:
        try:
            gs: list[CppBuilder] = tool.execute(tu)
            for g in gs:
                hpath = joinpath(bopt.gen_folder, g.name + ".g.h")
                with open(hpath, "w") as h:
                    th = TEMPLATE_HEADER
                    th = th.replace("<includes>", g.build_includes())
                    th = th.replace("<content>", g.build())
                    h.write(th)
                    h.write("\n")
        except Exception as e:
            error(f"Exception from periodic tool, {tool.__name__} says {e.__class__} {e.args}")


def add_source(source: str) -> None:
    global bopt
    bopt.source = source


def build() -> str | None:
    """
    builds input c/c++ sources to `o/` folder.
    returns the output path of the executable, None if compilation failed.
    the user can replace this function at runtime with a custom one that calls this under the hood,
    but it needs to be done before calling `run_tools`.
    """

    global bopt
    
    output_path = joinpath(bopt.output_folder, bopt.prjname) + ".out"
    flags_joined = " ".join(bopt.flags)
    cc = bopt.cc
    if bopt.cpp and bopt.cc == "gcc":
        cc = "g++"

    execute_tools(bopt.periodics)
    r = cmd(f"{cc} {bopt.source} -o {output_path} {flags_joined}")

    return output_path if r == 0 else None


class CppPieceBuilder:
    def __init__(self,
        decl: str = "",
        head: str | None = None,
        enclose_in_body: bool = True,
        is_def: bool = True,
        initial_indent_level: int = 1,
        single_indent: str = " " * 4,
    ) -> None:
        if decl == "":
            # free pieces can't have an automatic body
            enclose_in_body = False
        
        self.decl: str = decl
        self.head: str = decl if head == None else head
        self.single_indent: str = single_indent
        self.indent_level: int = initial_indent_level
        self.data: list[str] = []
        self.enclose_in_body: bool = enclose_in_body
        self.is_def: bool = is_def

        if self.enclose_in_body:
            self.body()
    
    def line(self, l: str = "") -> None:
        if l != "":
            self.add_indented(l)
        
        self.add_flat("\n")
    
    def add_indented(self, s: str) -> None:
        self.add_flat(self.single_indent * self.indent_level)
        self.add_flat(s)
    
    def add_flat(self, s: str) -> None:
        self.data.append(s)
    
    def add_pb(self, pb: "CppPieceBuilder") -> None:
        self.add_flat(pb.build())

    def sep(self) -> None:
        self.line("")
        self.line("")

    def body(self) -> None:
        self.line("{")
        self.indent()
    
    def unbody(self) -> None:
        self.unindent()
        self.line("}")
    
    def indent(self) -> None:
        self.indent_level += 1

    def unindent(self) -> None:
        self.indent_level -= 1
    
    def build(self) -> str:
        if self.enclose_in_body:
            self.unbody()
        
        return self.single_indent + self.decl + "\n" + "".join(self.data)


class CppBuilder:
    def __init__(self, name: str, includes: list[str] = [], single_indent: str = " " * 4) -> None:
        self.name: str = name
        self.includes: list[str] = includes
        self.data: dict[str, CppPieceBuilder] = {}
        self.single_indent: str = single_indent
    
    @property
    def pieces(self) -> list[CppPieceBuilder]:
        return list(self.data.values())
    
    def add(self, key: str, piece: CppPieceBuilder) -> None:
        assert not self.has(key), f"Piece builder with key=`{key}` is already registered in cpp builder"
        self.data[key] = piece
    
    def has(self, key: str) -> bool:
        return key in self.data

    def build(self) -> str:
        ind = self.single_indent
        declarations = []
        definitions = []

        for p in self.pieces:
            declarations.append(ind)
            declarations.append(p.head)
            declarations.append(";\n")

            if not p.is_def:
                continue

            definitions.append(p.build())
            definitions.append("\n")

        DECL_SEP_DEF = f"\n{ind}// ------------- //\n\n"
        return "".join(declarations) + DECL_SEP_DEF + "".join(definitions)
    
    def build_includes(self) -> str:
        b = []
        for incl in self.includes:
            if not incl.startswith("<"):
                incl = '"' + incl + '"'
            
            b.append(f"#include {incl}")
        
        return "\n".join(b)


_cached_templs = {}
def templ(name: str, params: list[tuple[str, str]] = []) -> CppPieceBuilder:
    global _cached_templs
    global bopt

    if name in _cached_templs:
        return _cached_templs[name]

    pb = CppPieceBuilder()
    _cached_templs[name] = pb

    fct_start_token = f"/*FCT_START_TEMPLATE*/"
    with open(joinpath(bopt.templs_folder, name + ".t.h")) as t:
        templ = t.read()

        try:
            templ_start_idx = templ.index(fct_start_token)
        except ValueError:
            templ_start_idx = 0
            fct_start_token = ""

        templ = templ[templ_start_idx+len(fct_start_token):]

        for pname, pvalue in params:
            pvalue = pvalue.replace("\n", "\\\n").strip().removesuffix("\\")
            pb.add_flat(f"#define {pname} {pvalue}\n")

        pb.add_flat(templ)

        for pname, _ in params:
            pb.add_flat(f"#undef {pname}\n")

    return pb


def piece(c: str) -> CppPieceBuilder:
    pb = CppPieceBuilder()
    pb.add_flat(c)
    return pb
