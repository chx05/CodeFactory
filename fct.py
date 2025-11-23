import os
import sys
import subprocess
import clang
import clang.cindex
import clang.enumerations
import clang.native
import analysis

from types import ModuleType
from genericpath import isdir
from importlib import util
from os.path import join as joinpath
from pathlib import Path
from glob import glob
from dataclasses import dataclass, field as dcfield


def get_prjname() -> str:
    prj_dir = Path(os.getcwd())
    return prj_dir.parts[-1]


@dataclass
class BuildOptions:
    prjname: str = dcfield(default_factory=get_prjname)
    output_folder: str = "o"
    gen_folder: str = "g"
    sources: list[str] = dcfield(default_factory=list)
    # index pointing to self.sources
    entry_source: int = 0

    cc: str = "gcc"
    cpp: bool = True
    flags: list[str] = dcfield(default_factory=lambda:[
        "-std=c++17",
        "-Wno-attributes",
        "-I/usr/include/c++/11",
        "-I/usr/include/x86_64-linux-gnu/c++/11",
        "-I/usr/include/c++/11/backward",
        "-I/usr/lib/gcc/x86_64-linux-gnu/11/include",
        "-I/usr/local/include",
        "-I/usr/include/x86_64-linux-gnu",
        "-I/usr/include",
    ])

    periodics: list[str] = dcfield(default_factory=list)
    manuals: list[str] = dcfield(default_factory=list)


args: list[str] = []
args_i: int = 0

bopt = BuildOptions()
bopt.periodics = []


HELP = """
Commands
    Help
        Shows this message
    Build
        Runs the build script to the end
    Run
        Builds and runs the executable
    Apply(tool_name)
        Runs a manual script named <tool_name>.py
    Prepare(header_name)
        Creates empty header <header_name>.g.h in folder `g/`
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


def install_tools(periodics: str | list[str] = "periodics", manuals: str | list[str] = "manuals") -> None:
    """
    periodics:
        either a path to a folder containing the tools or a list of the tools filenames.
        these are the tools that run before every compilation `fct build` or any command building under the hood

    manuals:
        either a path to a folder containing the tools or a list of the tools filenames.
        tools that run only when manually applied with command `fct apply tool_name`
    """

    global bopt

    if isinstance(periodics, str) and isdir(periodics):
        bopt.periodics += glob(f"{periodics}/*.py")

    
    if isinstance(manuals, str) and isdir(manuals):
        bopt.manuals += glob(f"{manuals}/*.py")


def run_argv() -> None:
    """
    runs the requests contained in argv.
    eventual generations will be outputed to `g/` folder
    """

    global bopt

    os.makedirs(bopt.output_folder, exist_ok=True)
    os.makedirs(bopt.gen_folder, exist_ok=True)

    global args
    global args_i
    args = sys.argv[1:]
    
    match fetch_arg().lower():
        case "help":
            print(HELP)
        
        case "build":
            build()
            return
        
        case "run":
            print("Building:")
            out_path = build()
            if out_path != None:
                print("Running:")
                subprocess.run([out_path] + args[args_i:])
            return
        
        case "prepare":
            # TODO: check if header already exists and
            #       alert the user about replacement
            header_name = fetch_arg()
            header_path = joinpath(bopt.gen_folder, header_name + ".g.h")
            with open(header_path, "w") as h:
                h.write(PREPARED_HEADER)
                h.write("\n")
        
        case "apply":
            raise NotImplementedError()

        case _:
            error("Command Not Found")
    
    finish()
    

def fetch_arg() -> str:
    global args
    global args_i

    if args_i >= len(args):
        error("Arg expected")

    arg = args[args_i]
    args_i += 1

    return arg


def cmd(s: str) -> int:
    """
    runs a manual shell command
    """
    
    return os.system(s)


def error(msg: str) -> None:
    print(f"Error: {msg}")
    sys.exit(1)


def finish(msg: str = "") -> None:
    if msg != "":
        print(f"Finished: {msg}")
    
    sys.exit(0)


def import_mod_from_path(tool_path: str) -> ModuleType:
    p = Path(tool_path).resolve()
    modname = p.stem

    spec = util.spec_from_file_location(modname, p)
    assert spec != None and spec.loader != None

    m = util.module_from_spec(spec)

    original_setting = sys.dont_write_bytecode
    sys.dont_write_bytecode = True

    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = original_setting

    return m


def execute_periodics() -> None:
    global bopt

    try:
        index = clang.cindex.Index.create()
        # TODO why parse doesn't work without single source?
        #unsaved_files = list(map(
        #    lambda p: (p, open(p).read()),
        #    bopt.sources
        #))
        tu = index.parse(bopt.sources[bopt.entry_source], bopt.flags)
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
    for tool_path in bopt.periodics:
        try:
            m = import_mod_from_path(tool_path)
            gs: list[CppBuilder] = m.execute(tu)
            for g in gs:
                hpath = joinpath(bopt.gen_folder, g.name + ".g.h")
                with open(hpath, "w") as h:
                    th = TEMPLATE_HEADER
                    th = th.replace("<includes>", g.build_includes())
                    th = th.replace("<content>", g.build())
                    h.write(th)
                    h.write("\n")
        except Exception as e:
            error(f"Exception from periodic tool, {repr(tool_path)} says {e.__class__} {e.args}")


def add_sources(sources: list[str] = []) -> None:
    global bopt

    exts = ["c"]
    if bopt.cpp:
        exts.append("cpp")

    if sources == []:
        for e in exts:
            sources += glob(f"**/*.{e}", recursive=True)
    
    bopt.sources += sources


def build() -> str | None:
    """
    builds input c/c++ sources to `o/` folder.
    returns the output path of the executable, None if compilation failed.
    the user can replace this function at runtime with a custom one that calls this under the hood,
    but it needs to be done before calling `run_tools`.
    """

    global bopt
    
    output_path = joinpath(bopt.output_folder, bopt.prjname)
    sources_joined = " ".join(bopt.sources)
    flags_joined = " ".join(bopt.flags)
    cc = bopt.cc
    if bopt.cpp and bopt.cc == "gcc":
        cc = "g++"

    execute_periodics()
    r = cmd(f"{cc} {sources_joined} -o {output_path}.out {flags_joined}")

    return output_path if r == 0 else None


class CppBuilder:
    def __init__(self, name: str, includes: list[str] = [], single_indent: str = "    ") -> None:
        self.name: str = name
        self.includes: list[str] = includes
        self.data: list[str] = []
        self.indent_level: int = 0
        self.single_indent: str = single_indent
    
    def line(self, l: str) -> None:
        self.data.append(self.single_indent * self.indent_level)
        self.data.append(l)
        self.data.append("\n")

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
        return "".join(self.data)
    
    def build_includes(self) -> str:
        b = []
        for incl in self.includes:
            if not incl.startswith("<"):
                incl = '"' + incl + '"'
            
            b.append(f"#include {incl}")
        
        return "\n".join(b)
