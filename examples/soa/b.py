import fct

from periodics import soa
from examples.struct_repr.periodics import struct_repr

#fct.bopt.use_exceptions_instead_of_exit = True
fct.install_tools(periodics=[soa, struct_repr], manuals=[])
fct.run_argv()
