class PythonScriptBuilder(object):
    indentation = ""
    indentation_increment = 4*" "

    def __init__(self, indentation = ""):
        self.indentation = indentation
        self.body = ""

    def __enter__(self):
        """On entering a with clause we increase the indentation."""
        self.indentation += self.indentation_increment
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """On exiting a with clause we decrease the indentation."""
        self.indentation = self.indentation[0:-len(self.indentation_increment)]
        return False # return False so that exceptions inside the with block are re-raised

    def __str__(self):
        """String representation."""
        return self.body

    def __iadd__(self, contents):
        """Operator += appends to script body and respects indentation. Ignores leading empty lines.
           IMPORTANT: When appending multiline strings, make sure that the first non-empty line has a correct *relative* indentation to the rest of the lines.
           This is because the first non-empty line will be used to figure out how much leading whitespace to remove from the rest of the lines.
        """
        split_at_newline = contents.split("\n")

        # Ignore the leading empty lines
        i = 0
        while split_at_newline[i].strip() == "":
            i += 1
        split_at_newline = split_at_newline[i:]

        # Use the leading whitespace of the first non empty line
        l = split_at_newline[0]
        n_leading_whitespace = len(l) - len(l.lstrip())

        for l in split_at_newline:
            self.body += self.indentation + l[n_leading_whitespace:] + "\n"
        return self

    def empty_line(self):
        self.body += "\n"

    def block(self, header):
        """"
            Start a block with a header.
            e.g:    with s.block("for i in range(10):"):
                        print(i)
        """
        self += header
        return self

    def write(self, file):
        """Write script to file"""
        with open(file, 'w') as f:
            f.write(str(self))


class SpiritScriptBuilder(PythonScriptBuilder):
    # Methods
    LLG = "simulation.METHOD_LLG"
    MC  = "simulation.METHOD_MC"

    # Solvers
    DEPONDT     = "simulation.SOLVER_DEPONDT"
    HEUN        = "simulation.SOLVER_HEUN"
    SIB         = "simulation.SOLVER_SIB"
    RK4         = "simulation.SOLVER_RK4"
    VP          = "simulation.SOLVER_VP"
    VP_OSO      = "simulation.SOLVER_VP_OSO"
    LBFGS_OSO   = "simulation.SOLVER_LBFGS_OSO"
    LBFGS_ATLAS = "simulation.SOLVER_LBFGS_Atlas"

    # Modules
    module_configuration = "configuration"
    module_simulation    = "simulation"
    module_state         = "state"

    @staticmethod
    def _dict_to_arg_string(dict):
        return "".join( [", {} = {}".format(key, val) for key, val in dict.items()] )

    @staticmethod
    def list_to_arg_string(list):
        return "".join( [", {}".format(l) for l in list] )

    @staticmethod
    def _dict_merge(base_dict, update_dict):
        base_dict = update_dict.copy()   # start with keys and values of base_dict
        base_dict.update(update_dict)    # modifies base_dict with keys and values of update_dict
        return base_dict

    def _spirit_call(self, module, function_name, p_state="p_state", *args, **kwargs):
        self += "{}.{}({}{}{})".format(module, function_name, p_state, self.list_to_arg_string(args), self._dict_to_arg_string(kwargs))

    def import_modules(self, *args):
        for a in args:
            self += "from spirit import {}".format(a)

    def state_block(self, input_file="input_created.cfg"):
        return self.block("with state.State(\"{}\") as p_state:".format(input_file))

    def configuration(self, fname, *args, **kwargs):
        """Sets one of the configuration api functions on of p_state"""
        self._spirit_call(self.module_configuration, fname, *args, **kwargs)

    def start_simulation(self, method, solver, **kwargs):
        self._spirit_call(self.module_simulation, "start", method, solver, **kwargs)