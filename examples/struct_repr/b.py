import fct

from fct_toolbox import struct_repr
struct_repr.SKIP_FIELDS_OF_UNREGISTERED_STRUCT_TYPES = True

fct.install_tools(periodics=[struct_repr], manuals=[])
fct.run_argv()
