import sys
sys.path.append('../..')
import fct

from periodics import struct_repr
struct_repr.SKIP_FIELDS_OF_UNREGISTERED_STRUCT_TYPES = True

#fct.bopt.use_exceptions_instead_of_exit = True
fct.install_tools(periodics=[struct_repr], manuals=[])
fct.run_argv()
