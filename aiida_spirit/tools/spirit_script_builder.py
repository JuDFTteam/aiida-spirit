# -*- coding: utf-8 -*-
"""
Helper class for builder run_spirit script.
"""


class PythonScriptBuilder():
    """Helper class to build python scripts with correct indentation"""

    indentation = ''
    indentation_increment = 4 * ' '

    def __init__(self, indentation=''):
        self.indentation = indentation
        self.body = ''

    def __enter__(self):
        """On entering a with clause we increase the indentation."""
        self.indentation += self.indentation_increment
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """On exiting a with clause we decrease the indentation."""
        self.indentation = self.indentation[0:-len(self.indentation_increment)]
        return False  # return False so that exceptions inside the with block are re-raised

    def __str__(self):
        """String representation."""
        return self.body

    def __iadd__(self, contents):
        """Operator += appends to script body and respects indentation.
        Ignores leading empty lines. Automatically appends '\n'.
        IMPORTANT: When appending multiline strings, make sure that the first non-empty line
        has a correct *relative* indentation to the rest of the lines.
        This is because the first non-empty line will be used to figure out how much
        leading whitespace to remove from the rest of the lines.
        """
        split_at_newline = contents.split('\n')

        # Ignore the leading empty lines
        i = 0
        while split_at_newline[i].strip() == '':
            i += 1
        split_at_newline = split_at_newline[i:]

        # Use the leading whitespace of the first non empty line
        l = split_at_newline[0]
        n_leading_whitespace = len(l) - len(l.lstrip())

        for l in split_at_newline:
            self.body += self.indentation + l[n_leading_whitespace:] + '\n'
        return self

    def empty_line(self):
        """Append an empty line to the script body"""
        self.body += '\n'

    def block(self, header):
        """"
         Start a block with a header.
         e.g::

             with s.block("for i in range(10):"):
                    print(i)
        """
        self += header
        return self

    def write(self, file):
        """Write script to file"""
        with open(file, 'w') as f:
            f.write(str(self))


class SpiritScriptBuilder(PythonScriptBuilder):
    """Helper class to build pyton scripts for the spirit api"""

    _method_dict = {
        'llg': 'simulation.METHOD_LLG',
        'mc': 'simulation.METHOD_MC'
    }

    def method(self, key):
        """Set Spirit run method (i.e. LLG, MC)"""
        try:
            return self._method_dict[key.lower()]
        except KeyError as error:
            raise ValueError('Invalid method!') from error

    _solver_dict = {
        'depondt': 'simulation.SOLVER_DEPONDT',
        'heun': 'simulation.SOLVER_HEUN',
        'sib': 'simulation.SOLVER_SIB',
        'rk4': 'simulation.SOLVER_SIB',
        'vp': 'simulation.SOLVER_VP',
        'vp_oso': 'simulation.SOLVER_VP_OSO',
        'lbfgs_oso': 'simulation.SOLVER_LBFGS_OSO',
        'lbfgs_atlas': 'simulation.SOLVER_LBFGS_Atlas'
    }

    def solver(self, key):
        """Set spirit solver (Depodt, VP, ...)"""
        try:
            return self._solver_dict[key.lower()]
        except KeyError as error:
            raise ValueError('Invalid solver!') from error

    _module_dict = {
        'configuration': 'configuration',
        'simulation': 'simulation',
        'geometry': 'geometry',
        'state': 'state',
        'io': 'io'
    }

    # Modules
    def module(self, key):
        """Import the spirit modules"""
        try:
            return self._module_dict[key.lower()]
        except KeyError as error:
            raise ValueError('Invalid module!') from error

    @staticmethod
    def _dict_to_arg_string(dict):  # pylint: disable=redefined-builtin
        """Format a dict as a string of keyword arguments"""
        return ''.join(
            [', {} = {}'.format(key, val) for key, val in dict.items()])

    @staticmethod
    def list_to_arg_string(list):  # pylint: disable=redefined-builtin
        """Format a list as a string of positional arguments"""
        return ''.join([', {}'.format(l) for l in list])

    def _spirit_call(self, module, function_name, *args, **kwargs):
        """A generic call to any of the spirit api functions."""
        self += '{}.{}(p_state{}{})'.format(module, function_name,
                                            self.list_to_arg_string(args),
                                            self._dict_to_arg_string(kwargs))

    def import_modules(self, *args):
        """Imports the modules given in `*args`. If no `*args` are given, imports all modules in the `module` dict"""
        if len(args) > 0:
            for a in args:
                self += 'from spirit import {}'.format(a)
        else:
            for val in self._module_dict.values():
                self += 'from spirit import {}'.format(val)

    def state_block(self, input_file='input_created.cfg'):
        """Creates the state_block and thereby creates the p_state"""
        return self.block(
            "with state.State(\"{}\") as p_state:".format(input_file))

    def configuration(self, fname, *args, **kwargs):
        """Sets one of the configuration api functions on of p_state"""
        self._spirit_call(self.module('configuration'), fname, *args, **kwargs)

    def start_simulation(self, method, solver, *args, **kwargs):
        """Start a simulation with a method and a solver."""
        self._spirit_call(self.module('simulation'), 'start',
                          self.method(method), self.solver(solver), *args,
                          **kwargs)
