# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_spirit.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""
from os import path  #modification to run test
import tomllib
import tomli_w
import numpy as np
from pandas import DataFrame
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import Dict, StructureData, ArrayData, List
from .tools.spirit_script_builder import SpiritScriptBuilder

# default spirit input (TOML) which is updated with the parameters input node
DEFAULTS_PATH = path.join(path.dirname(path.realpath(__file__)),
                          'data/input_defaults.toml')

# define file names
_RUN_SPIRIT = 'run_spirit.py'  # python file that runs the spirit job through the spirit python API
_SPIRIT_STDOUT = 'spirit.stdout'  # filename where the stdout of the spirit run is put
_INPUT_TOML = 'input.toml'  # spirit input file
_ATOM_TYPES = 'atom_types.txt'

# Default retrieve list
_RETLIST = [_SPIRIT_STDOUT, _INPUT_TOML, _RUN_SPIRIT, _ATOM_TYPES]

# top level sections of the spirit input; plugin-only keys are listed separately
_TOML_SECTIONS = ('defaults', 'logging', 'geometry', 'hamiltonian', 'method')
_PLUGIN_KEYS = ('couplings_cutoff_radius', )

# paths of the spirit input that only the plugin sets ('*' matches any method name)
_FORBIDDEN_PATHS = [
    ('defaults', 'output'),
    ('logging', 'output'),
    ('geometry', 'bravais_lattice'),
    ('geometry', 'bravais_vectors'),
    ('geometry', 'bravais_matrix'),
    ('geometry', 'basis'),
    ('geometry', 'lattice_constant'),
    ('geometry', 'pinning', 'pinned'),
    ('geometry', 'defects'),
    ('geometry', 'atom_types'),
    ('hamiltonian', 'pairs'),
    ('hamiltonian', 'two_site_anisotropy'),
    ('method', '*', 'output', 'folder'),
    ('method', '*', 'output', 'file_tag'),
    ('method', '*', 'max_walltime'),
]


def _flat_paths(dct, prefix=()):
    """Yield the paths (tuples of keys) to all leaves of a nested dict."""
    for key, val in dct.items():
        if isinstance(val, dict) and val:
            yield from _flat_paths(val, prefix + (key, ))
        else:
            yield prefix + (key, )


def _is_forbidden(key_path):
    """Check if a key path starts with one of the forbidden paths."""
    for forbidden in _FORBIDDEN_PATHS:
        if len(key_path) >= len(forbidden) and all(
                f in ('*', k) for f, k in zip(forbidden, key_path)):
            return True
    return False


def _deep_update(base, update):
    """Recursively update the nested dict `base` with `update` (in place)."""
    for key, val in update.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], val)
        else:
            base[key] = val
    return base


# validators for input ports
def validate_params(params, _):  # pylint: disable=inconsistent-return-statements
    """Validate the input parameters (nested dict in the structure of the spirit TOML input)."""
    input_dict = params.get_dict()
    for key in input_dict:
        if key not in _TOML_SECTIONS + _PLUGIN_KEYS:
            return (
                f'Unknown top level key `{key}` in parameters; expected one of '
                f'{_TOML_SECTIONS + _PLUGIN_KEYS} (nested keys of the spirit TOML input).'
            )
    toml_dict = {k: v for k, v in input_dict.items() if k in _TOML_SECTIONS}
    for key_path in _flat_paths(toml_dict):
        if _is_forbidden(key_path):
            dotted = '.'.join(key_path)
            return f'Parameters tries to overwrite a key set by the plugin: {dotted}'
    try:
        tomli_w.dumps(toml_dict)
    except TypeError as err:
        return f'Parameters cannot be written as TOML: {err}'


def validate_jij_data(jij_data, _):  # pylint: disable=inconsistent-return-statements
    """Validate the shapes of the arrays in the jij_data input."""
    names = jij_data.get_arraynames()
    if 'Jij_expanded' not in names:
        return 'jij_data needs the array `Jij_expanded`.'
    n_bonds, n_cols = jij_data.get_shape('Jij_expanded')
    if 'Jij_tensor' in names:
        tensor_shape = jij_data.get_shape('Jij_tensor')
        if tensor_shape != (n_bonds, 3, 3):
            return (f'`Jij_tensor` has shape {tensor_shape}, '
                    f'expected ({n_bonds}, 3, 3) to match `Jij_expanded`.')
        if n_cols < 5:
            return '`Jij_expanded` needs at least the columns i, j, da, db, dc.'
    elif n_cols < 6:
        return '`Jij_expanded` needs at least the columns i, j, da, db, dc, J.'


class SpiritCalculation(CalcJob):
    """Run Spirit calculation from user defined inputs."""

    # Default input and output files, will be shows with inputcat/outputcat
    _DEFAULT_INPUT_FILE = _INPUT_TOML
    _DEFAULT_OUTPUT_FILE = _SPIRIT_STDOUT

    @classmethod
    def define(cls, spec):
        """Define inputs and outputs of the calculation."""
        # yapf: disable
        super(SpiritCalculation, cls).define(spec)

        # set default values for AiiDA options
        spec.inputs['metadata']['options']['resources'].default = {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        }
        spec.inputs['metadata']['options']['parser_name'].default = 'spirit'

        # put here the input ports (parameters, structure, jij_data, ...)
        spec.input('parameters', valid_type=Dict, required=False,
                   validator=validate_params,
                   help="""Dict node that allows to control the input parameters for spirit.
                        The keys are nested in the structure of the spirit TOML input, e.g.
                        {'method': {'llg': {'n_iterations': 1000}}, 'geometry': {'n_basis_cells': [10, 10, 1]}}
                        (see https://spirit-docs.readthedocs.io/en/latest/core/docs/Input.html).
                        They are merged over the plugin defaults in `aiida_spirit/data/input_defaults.toml`.
                        Geometry, coupling tables and output locations are set by the plugin.
                        The extra key `couplings_cutoff_radius` drops couplings beyond that radius.
                        """)
        spec.input('run_options', valid_type=Dict, required=False,
                   default=lambda: Dict(dict={'simulation_method': 'LLG',
                                              'solver': 'Depondt',
                                              'configuration': {},
                                              'post_processing': '',
                                             }),
                   help="""Dict node that allows to control the spirit run
                        (e.g. simulation_method=LLG, solver=Depondt).
                        The configuration input specifies the input configuration
                        (the default is to start from a random configuration,
                        plus_z is also possible to start from all spins pointing in +z).
                        The post_processing string is added to the run script and allows
                        to add e.g. quantities.get_topological_charge(p_state) for the
                        calculation of the topological charge of a 2D system.
                        """)
        spec.input('structure', valid_type=StructureData, required=True,
                   help='Use a node that specifies the input crystal structure')
        spec.input('jij_data', valid_type=ArrayData, required=True,
                   validator=validate_jij_data,
                   help="""ArrayData with the full list of pairwise interactions, one row per listed
                        bond i -> j (spirit counts each listed bond once, energy in meV per bond:
                        -n_i^T Jtensor n_j; a bond listed in both directions counts twice).
                        Array 'Jij_expanded' has the columns (i, j, da, db, dc, J, Dx, Dy, Dz); J and
                        the DMI vector D are optional if 'Jij_tensor' is given. D is in spirit's
                        convention, D_x = (Jtensor_yz - Jtensor_zy) / 2, i.e. half the vector of
                        aiida-kkr's JijData. The optional array 'Jij_tensor' (shape (n, 3, 3), rows
                        aligned with 'Jij_expanded') gives the full tensor instead; it is split into
                        J, D and the two-site anisotropy K and overrides the J and D columns.
                        The optional array 'positions_expanded' (bond vectors) is used by the
                        couplings_cutoff_radius parameter.
                        """)
        spec.input('pinning', valid_type=ArrayData, required=False,
                   help="""Use a node that specifies the full pinning information for all spins
                        in the spirit supercell that should be pinned (i.e. take into account
                        the n_basis_cells input from the parameters input node. This is an
                        ArrayData object which should have the array called 'pinning' which has
                        the columns (i, da, db, dc, Sx, Sy, Sz).
                        See https://spirit-docs.readthedocs.io/en/latest/core/docs/Input.html#pinning-a-name-pinning-a
                        for more information on pinning in spirit.
                        """)
        spec.input('defects', valid_type=ArrayData, required=False,
                   help="""Use a node that specifies the defects information for all spins
                        in the spirit supercell. This is an ArrayData object that should
                        define the defects in the 'defects' array (column should be i, da, db, dc, itype
                        where itype<0 means vacancy). The atom type information can be given with the
                        atom_type array in the defects ArrayData that has the columns
                        (iatom  atom_type  mu_s  concentration).
                        See https://spirit-docs.readthedocs.io/en/latest/core/docs/Input.html
                        for more information on defects in spirit.
                        """)
        spec.input('initial_state', valid_type=ArrayData, required=False,
                   help="""Use a node that specifies the initial directions of all spins
                        in the spirit supercell. This is an ArrayData object that should
                        define the 'initial_state' array (columns should be x, y, z).
                        This overwrites the configuration input!
                        """)
        spec.input('add_to_retrieved', valid_type=List, required=False,
                   help='List of strings specifying additional files that should be retrieved.')

        # define output nodes
        spec.output('output_parameters', valid_type=Dict, required=True,
                    help='Parsed values from the spirit stdout, stored as Dict for quick access.')
        spec.output('magnetization', valid_type=ArrayData, required=False,
                    help='initial and final magnetization')
        spec.output('energies', valid_type=ArrayData, required=False,
                    help='energy convergence')
        spec.output('atom_types', valid_type=ArrayData, required=False,
                    help='list of atom types used in the simulation (-1 indicates vacancies).')
        spec.output('monte_carlo', valid_type=ArrayData, required=False,
                    help='sampled quantities from a monte carlo run')

        # define exit codes that are used to terminate the SpiritCalculation
        spec.exit_code(100, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')
        spec.exit_code(101, 'ERROR_SPIRIT_CODE_INCOMPATIBLE',
                       message='The Spirit Code does not support a feature that is needed (e.g. pinning).')


    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files
            needed by the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """
        ##############################################
        # CREATE input.toml FILE FROM DICTIONARY OF SETTINGS/PARAMETERS
        # from the dictionary given by the AiiDA node, the input.toml file is created
        self.write_input_toml(folder)

        ##############################################
        # CREATE "pinning.txt" file if needed
        if 'pinning' in self.inputs:
            self.write_pinning_file(folder)

        ##############################################
        # CREATE "defects.txt" file if needed
        if 'defects' in self.inputs:
            self.write_defects_file(folder)

        ##############################################
        # CREATE "initial_state.txt" file if needed
        if 'initial_state' in self.inputs:
            self.write_initial_configuration(folder)

        ##############################################
        # CREATE "couplings.txt" FILE FROM Jij
        self.write_couplings_file(folder)

        ##############################################
        # CREATE "run_spirit.py"
        self.write_run_spirit(folder)

        ##############################################
        # FINALLY GIVE THE INFORMATION TO AIIDA
        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.withmpi = self.inputs.metadata.options.get('withmpi', False)  # unset by default in aiida-core 2
        codeinfo.stdin_name = _RUN_SPIRIT
        codeinfo.stdout_name = _SPIRIT_STDOUT

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]

        # this should be a list of the filenames we expect when spirit ran
        # i.e. the files we specify here will be copied back to the file repository
        # note that the retlist_tmp contains only files which are only needed in parsing
        # but are then not kept in the file repository (e.g. magnetization arrays which are
        # stored as numy arrays instead of also keeping the raw text files)
        retlist = _RETLIST.copy()
        retlist_tmp = []
        if 'pinning' in self.inputs:
            # also retreive the pinning file
            retlist += ['pinning.txt']
        if 'defects' in self.inputs:
            # also retreive the defects file
            retlist += ['defects.txt']

        run_opts = self.inputs.run_options.get_dict()
        if run_opts['simulation_method'].upper() == 'LLG':
            retlist_tmp += ['spirit_Image-00_Energy-archive.txt',
                            'spirit_Image-00_Spins-final.ovf',
                            'spirit_Image-00_Spins-initial.ovf']
        elif run_opts['simulation_method'].upper() == 'MC':
            retlist_tmp += ['output_mc.txt']

        # from the input we can specify additional files that should be retrieved
        if 'add_to_retrieved' in self.inputs:
            retlist += self.inputs.add_to_retrieved.get_list()

        calcinfo.retrieve_list = retlist
        calcinfo.retrieve_temporary_list = retlist_tmp

        return calcinfo


    def write_input_toml(self, folder):
        """Write the input.toml file: plugin defaults, updated with the parameters input,
        plus the geometry, coupling tables and output locations set by the plugin."""

        input_dict = self.inputs.parameters.get_dict() if 'parameters' in self.inputs else {}

        # take out special keywords
        # this is used in the write_couplings_file to cut the couplings beyond a given radius
        # works only if the jij_data has positions_extended
        self.couplings_rcut = input_dict.pop('couplings_cutoff_radius', None) # pylint: disable=attribute-defined-outside-init

        with open(DEFAULTS_PATH, 'rb') as _f:
            config = tomllib.load(_f)
        _deep_update(config, input_dict)

        # geometry from the StructureData input
        structure = self.inputs.structure
        geometry = config['geometry']
        if 'boundary_conditions' not in input_dict.get('geometry', {}):
            # boundary conditions from pbc of structure, only if nothing is given in the input parameters
            geometry['boundary_conditions'] = [int(pbc) for pbc in structure.pbc]
        geometry.update(_get_geometry(structure))

        # output locations
        config['defaults'] = {'output': {'file_tag': 'spirit', 'folder': '.'}}
        config['logging']['output'] = {'folder': '.'}

        # tables are written to separate files and linked here
        config['hamiltonian']['pairs'] = 'file://couplings.txt'
        if 'Jij_tensor' in self.inputs.jij_data.get_arraynames():
            config['hamiltonian']['two_site_anisotropy'] = 'file://two_site_anisotropy.txt'
        if 'pinning' in self.inputs:
            geometry.setdefault('pinning', {})['pinned'] = 'file://pinning.txt'
        if 'defects' in self.inputs:
            geometry['defects'] = 'file://defects.txt'
            atom_types = self.get_atom_types_table()
            if atom_types is not None:
                geometry['atom_types'] = atom_types

        with folder.open(_INPUT_TOML, 'w') as _f:
            _f.write(tomli_w.dumps(config, multiline_strings=True))


    def get_atom_types_table(self):
        """Get the atom_types table (i type mu_s c) from the defects input, or None if not given"""
        if 'atom_types' not in self.inputs.defects.get_arraynames():
            return None
        atom_types = self.inputs.defects.get_array('atom_types')
        if len(atom_types) == 0:
            return None
        # input columns: iatom  atom_type  mu_s  concentration
        rows = [f'{int(t[0])} {int(t[1])} {t[2]:f} {t[3]:f}' for t in atom_types]
        return '\n'.join(['i type mu_s c'] + rows) + '\n'


    def write_defects_file(self, folder): # pylint: disable=unused-argument
        """Create the defects.txt file from the defects input array

        We write the `defects.txt` in this format (type: atom type index 0..n or vacancy if type < 0):
          i  da db dc  type
          0  0 0 0  -1
          0  1 0 0  -1
          0  0 1 0  -1
        """
        # check if defects list is given
        if 'defects' not in self.inputs.defects.get_arraynames():
            # no list of defects specified
            # instead write a table without rows
            with folder.open('defects.txt', 'w') as _f:
                _f.writelines(['i da db dc type\n'])
        else:
            # get defects array from the input node
            defects = self.inputs.defects.get_array('defects')

            # convert to dataframe for easier writeout
            defects_df = DataFrame(defects, columns=['i', 'da', 'db', 'dc', 'type'])
            defects_df = defects_df.astype({'i':'int64', 'da':'int64', 'db':'int64', 'dc':'int64', 'type':'int64'})

            # Write the defects file in csv format that spirit can understand (with header line)
            with folder.open('defects.txt', 'w') as _f:
                defects_df.to_csv(_f, sep='\t', index=False)


    def write_pinning_file(self, folder): # pylint: disable=unused-argument
        """Create the pinning.txt file from the pinning input array

        We write the `pinning.txt` in this format:
          i  da db dc  x   y   z
          0  0 0 0  1.0 0.0 0.0
          0  1 0 0  0.0 1.0 0.0
          0  0 1 0  0.0 0.0 1.0
        """
        # get pinning array from the input node
        pinning = self.inputs.pinning.get_array('pinning')

        # convert to dataframe for easier writeout
        pinning_df = DataFrame(pinning, columns=['i', 'da', 'db', 'dc', 'x', 'y', 'z'])
        pinning_df = pinning_df.astype({'i':'int64', 'da':'int64', 'db':'int64', 'dc':'int64',
                                        'x':'float64', 'y':'float64', 'z':'float64'})

        # make sure the pinning direction is normalized
        norm = np.sqrt(pinning_df['x']**2 + pinning_df['y']**2 + pinning_df['z']**2)
        pinning_df['x'] /= norm
        pinning_df['y'] /= norm
        pinning_df['z'] /= norm

        # Write the pinning file in csv format that spirit can understand (with header line)
        with folder.open('pinning.txt', 'w') as _f:
            pinning_df.to_csv(_f, sep='\t', index=False)


    def write_initial_configuration(self, folder):
        """Write the 'initial_state.txt' file (OVF 2.0 text format) with the direction of each spin"""
        # get the initial state (i.e. directions array) from the input node
        initial_state = np.array(self.inputs.initial_state.get_array('initial_state'), dtype=float)

        # make sure the directions are normalized
        initial_state /= np.linalg.norm(initial_state, axis=1)[:, None]

        # header as in the OVF files written by spirit; spirit takes the number of spins from the nodes
        header = '\n'.join([
            '# OOMMF OVF 2.0', '# Segment count: 1', '# Begin: Segment', '# Begin: Header',
            '# Title: initial state written by aiida-spirit',
            '# valuedim: 3', '# valueunits: none none none', '# valuelabels: spin_x spin_y spin_z',
            '# meshunit: nm', '# meshtype: rectangular',
            '# xbase: 0', '# ybase: 0', '# zbase: 0',
            '# xstepsize: 1', '# ystepsize: 1', '# zstepsize: 1',
            '# xmin: 0', '# ymin: 0', '# zmin: 0',
            f'# xmax: {len(initial_state)}', '# ymax: 1', '# zmax: 1',
            f'# xnodes: {len(initial_state)}', '# ynodes: 1', '# znodes: 1',
            '# End: Header', '# Begin: Data Text',
        ])
        with folder.open('initial_state.txt', 'w') as _f:
            np.savetxt(_f, initial_state, fmt='%.15f', header=header, comments='',
                       footer='# End: Data Text\n# End: Segment', delimiter='  ')


    def write_couplings_file(self, folder): # pylint: disable=unused-argument,too-many-locals
        """Write the couplings.txt (exchange, DMI) and, from a full tensor, the
        two_site_anisotropy.txt file.

        Each row of `Jij_expanded` is one listed bond i -> j (+ da, db, dc). Spirit counts
        every listed bond once (energy per bond, meV)::

            E_ij = -J n_i.n_j - D.(n_i x n_j) - n_i^T K n_j = -n_i^T Jtensor n_j

        so a bond listed in both directions is counted twice. The rows are passed through
        unchanged; listing each bond once or twice is the user's convention.
        """

        jij_data = self.inputs.jij_data # Collection of numpy arrays
        jij_expanded = jij_data.get_array('Jij_expanded') # Extracts the Jij_expanded array
        index_columns = ['i', 'j', 'da', 'db', 'dc']

        two_site = None
        if 'Jij_tensor' in jij_data.get_arraynames():
            # split the full tensor into isotropic, antisymmetric (DMI) and symmetric traceless part
            jij, dij, kij = _split_exchange_tensor(jij_data.get_array('Jij_tensor'))
            jijs_df = DataFrame(jij_expanded[:, :5], columns=index_columns)
            jijs_df['Jij'] = jij
            jijs_df[['Dijx', 'Dijy', 'Dijz']] = dij
            # Kijzz is left out, spirit fills it in from the vanishing trace
            two_site = DataFrame(jij_expanded[:, :5], columns=index_columns)
            two_site[['Kijxx', 'Kijyy', 'Kijyz', 'Kijxz', 'Kijxy']] = np.stack(
                [kij[:, 0, 0], kij[:, 1, 1], kij[:, 1, 2], kij[:, 0, 2], kij[:, 0, 1]], axis=1)
        elif len(jij_expanded[0]) >= 9:
            # columns i j da db dc J Dx Dy Dz; the DMI vector goes to spirit as it is
            jijs_df = DataFrame(jij_expanded[:, :9], columns=index_columns + ['Jij', 'Dijx', 'Dijy', 'Dijz'])
        elif len(jij_expanded[0]) >= 6:
            # has Jijs
            jijs_df = DataFrame(jij_expanded[:, :6], columns=index_columns + ['Jij'])
        else:
            # no Jijs found, stop here
            raise ValueError('jij_data invalid')

        tables = {'couplings.txt': jijs_df}
        if two_site is not None:
            tables['two_site_anisotropy.txt'] = two_site

        # cut all couplings that are futher away that the cutoff radius
        keep = slice(None)
        if self.couplings_rcut is not None:
            r = np.sqrt(np.sum(jij_data.get_array('positions_expanded')**2, axis=1))
            keep = r <= self.couplings_rcut

        for filename, table in tables.items():
            table = table[keep].astype({col: 'int64' for col in index_columns})
            # Write the table in csv format that spirit can understand (tab separated, header line)
            with folder.open(filename, 'w') as _f:
                table.to_csv(_f, sep='\t', index=False)


    def write_run_spirit(self, folder):
        """write the run_spirit.py script that controls the spirit python API."""

        # extract run options from input node
        run_opts = self.inputs.run_options.get_dict()

        # now extract information from run_opts
        method = run_opts.get('simulation_method')
        solver = run_opts.get('solver')
        config = run_opts.get('configuration', {})
        post_proc = run_opts.get('post_processing', '')

        if method.upper() == 'MC':
            self.write_mc_script(folder) # A bit unclean but lets separate the code somewhat
            return

        # write the default spirit input file (e.g. for LLG)
        script = SpiritScriptBuilder()
        script.import_modules()
        with script.state_block():
            # write out the atom_types (needed for parsing defects)
            script += 'atom_types = geometry.get_atom_types(p_state)'
            with script.block("with open('"+_ATOM_TYPES+"', 'w') as _f:"):
                script += "_f.writelines([f'{i}\\n' for i in atom_types])"

            # deal with the input configuration
            if 'plus_z' in config and config.get('plus_z', False):
                script.configuration('plus_z')
            else:
                for _ in range(config.get('random', 1)):
                    script.configuration('random')

            # set an initial state defined for all spins
            # this overwites the previous configuration setting!
            if 'initial_state' in self.inputs:
                script += 'io.image_read(p_state, "initial_state.txt")'
            script.start_simulation(method, solver)

            # maybe add post_processing script
            if len(post_proc) > 0:
                script += post_proc

        # write run_spirit.py to the folder
        with folder.open(_RUN_SPIRIT, 'w') as f:
            txt = script.body
            f.write(txt)


    def write_mc_script(self, folder):
        """Write the MC script version of run_spirit.py"""
        script = SpiritScriptBuilder()
        script += """
        import numpy as np
        from spirit import state
        from spirit import system
        from spirit import simulation
        from spirit import configuration
        from spirit import parameters
        from spirit import hamiltonian
        from spirit import quantities
        from spirit import geometry
        from spirit import constants
        """

        run_opts = self.inputs.run_options.get_dict()
        mc_configuration = run_opts['mc_configuration']

        keys = ['n_thermalisation', 'n_decorrelation', 'n_samples', 'n_temperatures', 'T_start', 'T_end']

        for k in keys:
            script += '{:20} = {}'.format(k, mc_configuration[k])

        script += """
        sample_temperatures     = np.linspace(T_start, T_end, n_temperatures)
        energy_samples          = []
        magnetization_samples   = []
        susceptibility_samples  = []
        specific_heat_samples   = []
        binder_cumulant_samples = []
        """

        with script.state_block():
            # write out the atom_types (needed for parsing defects)
            script += 'atom_types = geometry.get_atom_types(p_state)'
            with script.block("with open('"+_ATOM_TYPES+"', 'w') as _f:"):
                script += "_f.writelines([f'{i}\\n' for i in atom_types])"

            # get number of spins
            script += 'NOS = system.get_nos(p_state)'

            # Loop over temperatures
            with script.block('for iT, T in enumerate(sample_temperatures):'):
                script += 'parameters.mc.set_temperature(p_state, T)'
                script.configuration('plus_z')
                script += """
                # Cumulative average variables
                E  = 0
                E2 = 0
                M  = 0
                M2 = 0
                M4 = 0

                # Thermalisation
                parameters.mc.set_iterations(p_state, n_thermalisation, n_thermalisation) # We want n_thermalisation iterations and only a single log message
                simulation.start(p_state, simulation.METHOD_MC, simulation.MC_ALGORITHM_METROPOLIS) # runs the n_thermalisation iterations

                # Sampling at given temperature
                parameters.mc.set_iterations(p_state, n_decorrelation*n_samples, n_decorrelation*n_samples) # We want n_decorrelation iterations and only a single log message
                simulation.start(p_state, simulation.METHOD_MC, simulation.MC_ALGORITHM_METROPOLIS, single_shot=True) # Start a single-shot MC simulation

                for n in range(n_samples):
                    # Run decorrelation
                    for i_decorr in range(n_decorrelation):
                        simulation.single_shot(p_state) # one MC iteration
                    # Get energy (update first, get_energy may return a stale value)
                    system.update_energy(p_state)
                    E_local = system.get_energy(p_state) / NOS
                    # Get magnetization
                    M_local = np.array(quantities.get_magnetization(p_state))
                    M_local_tot = np.linalg.norm(M_local)
                    # Add to cumulative averages
                    E   += E_local
                    E2  += E_local**2
                    M   += M_local_tot
                    M2  += M_local_tot**2
                    M4  += M_local_tot**4

                # Make sure the MC simulation is not running anymore
                simulation.stop(p_state)

                # Average over samples
                E  /= n_samples
                E2 /= n_samples
                M  /= n_samples
                M2 /= n_samples
                M4 /= n_samples

                # Calculate observables
                chi = (M2 - np.dot(M, M)) / (constants.k_B * T)
                c_v = (E2 - E**2) / (constants.k_B * T**2)
                cumulant = 1 - M4/(3 * M2**2)

                energy_samples.append(E)
                magnetization_samples.append(M)
                susceptibility_samples.append(chi)
                specific_heat_samples.append(c_v)
                binder_cumulant_samples.append(cumulant)
                """

        script += """
        output_mc      = np.zeros((len(sample_temperatures), 6))
        output_mc[:,0] = sample_temperatures
        output_mc[:,1] = energy_samples
        output_mc[:,2] = magnetization_samples
        output_mc[:,3] = susceptibility_samples
        output_mc[:,4] = specific_heat_samples
        output_mc[:,5] = binder_cumulant_samples

        np.savetxt("output_mc.txt", output_mc, header="sample_temperatures, energy_samples, magnetization_samples, susceptibility_samples, specific_heat_samples, binder_cumulant_samples")
        """

        # write run_spirit.py to the folder
        with folder.open(_RUN_SPIRIT, 'w') as f:
            f.write(script.body)

def _split_exchange_tensor(tensor):
    """Split exchange tensors (shape (n, 3, 3), meV) into J, D and K.

    Convention (energy per listed bond -n_i^T Jtensor n_j, as in spirit)::

        Jtensor = J * 1 + K + [D]_x^T,   [D]_x v = D x v

    so J = tr(Jtensor) / 3, D_x = (Jtensor_yz - Jtensor_zy) / 2 (and cyclic), and
    K = (Jtensor + Jtensor^T) / 2 - J * 1 (symmetric, traceless).
    Note: aiida-kkr's JijData stores twice this D vector.

    :returns: J (n,), D (n, 3), K (n, 3, 3)
    """
    tensor = np.asarray(tensor, dtype=float)
    jij = np.trace(tensor, axis1=1, axis2=2) / 3
    antisym = (tensor - tensor.transpose(0, 2, 1)) / 2
    dij = np.stack([antisym[:, 1, 2], antisym[:, 2, 0], antisym[:, 0, 1]], axis=1)
    kij = (tensor + tensor.transpose(0, 2, 1)) / 2 - jij[:, None, None] * np.eye(3)
    return jij, dij, kij


def _get_geometry(structure):
    """Get the geometry entries of the spirit input (bravais_vectors, basis) from the structure"""

    # bravais vectors in Angstrom; lattice_constant is fixed to 1 so that they are not rescaled
    cell = np.array(structure.cell)

    # transformation matrix to relative coordinates
    U2rel = np.linalg.inv(cell.transpose())

    # sites in unit cell, in relative coordinates, folded back to the unit cell
    basis = [(np.dot(U2rel, site.position) % 1).tolist() for site in structure.sites]

    return {'lattice_constant': 1.0, 'bravais_vectors': cell.tolist(), 'basis': basis}
