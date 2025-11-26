import sys
sys.path.append('../..')
import fct

from periodics import enum_count

#fct.bopt.use_exceptions_instead_of_exit = True
fct.install_tools(periodics=[enum_count], manuals=[])
fct.run_argv()
