import fct

from fct_toolbox import soa, struct_repr
fct.install_tools(periodics=[soa, struct_repr], manuals=[])
fct.run_argv()
