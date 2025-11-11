CodeFactory is a C scriptable framework written in Python for source generation and compile time C code inspection.
CodeFactory also supports a Python build script for your C project.
It's easy to use, no configuration or prerequisite needed.

A few examples of what can be achieved throught this framework are available in the `examples` folder, but here are some listed:
* Auto header generation on the fly based on the definitions found in the source files, a watcher tool is provided to keep headers updated as any C source in the projects change.
* Quick manual generation of any templated type, tools like StructOfArrays can be scripted and used for any chosen type (SOA is already available in the base framework anyway). Once the user has scripted the tool, it can be applied to any type in the project using the shell command `cfac apply script_name type_t` where `cfac` is the shell command for invoking codefactory, `script_name` is the name of the tool available in the `scripts/` folder of a project, and `type_t` is any type available in the C project on which will be applied the indicated tool.
* Building a cfac project without bothering with nonsense building systems, either just follow the conventions for a normal building process or script your own building process. No private-sourcing mechanism will be tolerated, such as `cc main.c source1.c source2.c` as this just kills your runtime performance, however a build-once and use later mechanism like this is still available but it should be used for huge standalone components of a project, such as a big base layer for interacting with something.
* The [Megazine](https://github.com/chx05/megazine) library is powered by this framework. It is a meta library that allows creating a database-like binary file simply from in-language defined structs, without writing a single line of code.

<br>

---

<br>

<p align="center">developed @ ancient_labs</p>