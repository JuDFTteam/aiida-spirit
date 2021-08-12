# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_spirit.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""
from os import path  #modification to run test
import numpy as np
from pandas import DataFrame
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import Dict, StructureData, ArrayData
from .data._formatting_info import _forbidden_keys
from .data._type_check import verify_input_para  #, validate_input_dict

# this is the template input config file which is read in and changed according to the inputs
TEMPLATE_PATH = path.join(path.dirname(path.realpath(__file__)),
                          'data/input_original.cfg')

# define file names
_RUN_SPIRIT = 'run_spirit.py'  # python file that runs the spirit job through the spirit python API
_SPIRIT_STDOUT = 'spirit.stdout'  # filename where the stdout of the spirit run is put
_INPUT_CFG = 'input_created.cfg'  # spirit input file

# Default retrieve list
_RETLIST = [
    _SPIRIT_STDOUT, _INPUT_CFG, _RUN_SPIRIT,
    'spirit_Image-00_Energy-archive.txt', 'spirit_Image-00_Spins-final.ovf',
    'spirit_Image-00_Spins-initial.ovf'
]


# validators for input ports
def validate_params(params, _):  # pylint: disable=inconsistent-return-statements
    """Validate the input parameters."""
    for key, val in params.get_dict().items():
        if key not in _forbidden_keys:
            try:
                _ = verify_input_para(key, val)
            except ValueError as err:
                return f'Parameters validator returned ValueError: {err}'
            except TypeError as err:
                return f'Parameters validator returned TypeError: {err}'
        else:
            return f'Parameters tries to overwrite an forbidden key: {key}'


class SpiritCalculation(CalcJob):
    """Run Spirit calculation from user defined inputs."""
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
                   help="""Dict node that allows to control the input parameters for spirit
                        (see https://spirit-docs.readthedocs.io/en/latest/core/docs/Input.html).
                        """)
        spec.input('run_options', valid_type=Dict, required=False,
                   default=lambda: Dict(dict={'simulation_method': 'LLG',
                                              'solver': 'Depondt',
                                              'configuration': {},
                                             }),
                   help="""Dict node that allows to control the spirit run
                        (e.g. simulation_method=LLG, solver=Depondt).
                        The configuration input specifies the input configuration
                        (the default is to start from a random configuration,
                        plus_z is also possible to start from all spins pointing in +z).
                        """)
        spec.input('structure', valid_type=StructureData, required=True,
                   help='Use a node that specifies the input crystal structure')
        spec.input('jij_data', valid_type=ArrayData, required=True,
                   help='Use a node that specifies the full list of pairwise interactions')
        spec.input('pinning', valid_type=ArrayData, required=False,
                   help="""Use a node that specifies the full pinning information for all spins
                        in the spirit supercell that should be pinned (i.e. take into account
                        the n_basis_cells input from the parameters input node. This is an
                        ArrayData object which should have the array called pinning which has
                        the columns (i, da, db, dc, Sx, Sy, Sz).
                        See https://spirit-docs.readthedocs.io/en/latest/core/docs/Input.html#pinning-a-name-pinning-a
                        for more information on pinning in spirit.
                        """)
        spec.input('defects', valid_type=ArrayData, required=False,
                   help="""Use a node that specifies the defects information for all spins
                        in the spirit supercell. This is an ArrayData object that should
                        define the defects in the defects array (column should be i, da, db, dc, itype
                        where itype<0 means vacancy). The atom type information can be given with the
                        atom_type array in the defects ArrayData that has the columns
                        (iatom  atom_type  mu_s  concentration).
                        See https://spirit-docs.readthedocs.io/en/latest/core/docs/Input.html
                        for more information on defects in spirit.
                        """)

        # define output nodes
        spec.output('output_parameters', valid_type=Dict, required=True,
                    help='Parsed values from the spirit stdout, stored as Dict for quick access.')
        spec.output('magnetization', valid_type=ArrayData, required=True,
                    help='initial and final magnetization')
        spec.output('energies', valid_type=ArrayData, required=True,
                    help='energy convergence')

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
        # CREATE .cfg FILE FROM DICTIONARY OF SETTINGS/PARAMETERS
        # from the dictionary given by the AiiDA node, the input.cfg file is created
        self.write_input_cfg(folder)

        ##############################################
        # CREATE "pinning.txt" file if needed
        if 'pinning' in self.inputs:
            self.write_pinning_file(folder)

        ##############################################
        # CREATE "defects.txt" file if needed
        if 'defects' in self.inputs:
            self.write_defects_file(folder)

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
        codeinfo.withmpi = self.inputs.metadata.options.withmpi
        codeinfo.stdin_name = _RUN_SPIRIT
        codeinfo.stdout_name = _SPIRIT_STDOUT

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]

        # this should be a list of the filenames we expect when spirit ran
        # i.e. the files we specify here will be copied back to the file repository
        retlist = _RETLIST
        if 'pinning' in self.inputs:
            # also retreive the pinning file
            retlist += ['pinning.txt']
        if 'defects' in self.inputs:
            # also retreive the defects file
            retlist += ['defects.txt']
        calcinfo.retrieve_list = retlist

        return calcinfo


    def write_input_cfg(self, folder):
        """Write the input.cfg file from the parameters input"""

        parameters = self.inputs.parameters
        input_dict = parameters.get_dict() #(would it be better to use "try, except" ?)

        # take out special keywords
        # this is used in the write_couplings_file to cut the couplings beyond a given radius
        # works only if the jij_data has positions_extended
        self.couplings_rcut = None # pylint: disable=attribute-defined-outside-init
        if 'couplings_cutoff_radius' in input_dict:
            self.couplings_rcut = input_dict.pop('couplings_cutoff_radius') # pylint: disable=attribute-defined-outside-init

        # extract structure information
        structure = self.inputs.structure
        if 'boundary_conditions' not in input_dict:
            # overwrite boundary conditions from pbc of structure
            # do this only if nothing is given in the input parameters
            input_dict['boundary_conditions'] = structure.pbc

        # go through the template input config and overwrite values from inputs
        input_file = []
        with open(TEMPLATE_PATH, 'r') as f_orig:
            for line in f_orig:
                input_file.append(line)

                if line[0] != '#' or '\n':
                    # if line is not a comment or line is not empty
                    # check if the parameter has to be modified and use function to modify line if needed
                    l_param_value = line.split(' ', 1)
                    key = l_param_value[0]

                    if key in input_dict:
                        if key not in _forbidden_keys:
                            val_str = verify_input_para(key, input_dict[key])
                            input_file[-1] = _modify_line(line, val_str)

                    ##############################################
                    # MODIFY "GEOMETRY" SECTION FROM .cfg FILE
                    # from the StructureData node given as an input, the "GEOMETRY" section is created
                    if key == 'bravais_lattice':
                        geometry_string = _get_geometry(structure)
                        input_file[-1] = geometry_string

        if 'pinning' in self.inputs:
            # put `pinned_from_file pinning.txt` into the input config to read the pinning info in the spirit run
            pinning_info = '\n\n# read pinning of spins from file\n'
            pinning_info += 'pinned_from_file pinning.txt\n'
            input_file.append(pinning_info)

        if 'defects' in self.inputs:
            # put the information for defects into the config file
            defects_info = self.get_defects_info()
            input_file.append(defects_info)

        # write new contents to a new file, which will be used for the calculations
        with folder.open(_INPUT_CFG, 'w') as f_created:
            f_created.writelines(input_file)


    def get_defects_info(self):
        """Get the defects info that is added to the config file"""
        # add line that specifies the defects file and add the atom_type info to the config file
        defects_info = '\n\n# read defects from file\n'
        defects_info += 'defects_from_file defects.txt\n'

        # add atom_types info if given
        if 'atom_types' in self.inputs.defects.get_arraynames():
            atom_types = self.inputs.defects.get_array('atom_types')
        else:
            atom_types = []

        if len(atom_types) > 0:
            defects_info += '\n\n# Disorder type: iatom  atom_type  mu_s  concentration\n'
            defects_info += f'atom_types {len(set(atom_types[:,0]))}\n'
            for itype in atom_types:
                defects_info += f'{itype[0]:i} {itype[1]:i} {itype[2]:f} {itype[3]:f}\n'

        return defects_info


    def write_defects_file(self, folder): # pylint: disable=unused-argument
        """Create the defects.txt file from the defects input array

        We write the `defects.txt` in this format:
          ### Atom types: type index 0..n or or vacancy (type < 0)
          ### Specify the number of defects and then the defects in terms of translations and type
          ### i  da db dc  itype
          n_defects 3 # this is skipped and all defects that are found in the file are used
          0  0 0 0  -1
          0  1 0 0  -1
          0  0 1 0  -1
        """
        # get defects array from the input node
        defects = self.inputs.defects.get_array('defects')

        # convert to dataframe for easier writeout
        defects_df = DataFrame(defects, columns=['i', 'da', 'db', 'dc', 'itype'])
        defects_df = defects_df.astype({'i':'int64', 'da':'int64', 'db':'int64', 'dc':'int64', 'itype':'int64'})

        # Write the defects file in csv format that spirit can understand
        with folder.open('defects.txt', 'w') as f:
            defects_df.to_csv(f, sep='\t', index=False, header=False)


    def write_pinning_file(self, folder): # pylint: disable=unused-argument
        """Create the pinning.txt file from the pinning input array

        We write the `pinning.txt` in this format (i, da, db, dc, Sx, Sy, Sz):
          0  0 0 0  1.0 0.0 0.0
          0  1 0 0  0.0 1.0 0.0
          0  0 1 0  0.0 0.0 1.0
        """
        # get pinning array from the input node
        pinning = self.inputs.pinning.get_array('pinning')

        # convert to dataframe for easier writeout
        pinning_df = DataFrame(pinning, columns=['i', 'da', 'db', 'dc', 'Sx', 'Sy', 'Sz'])
        pinning_df = pinning_df.astype({'i':'int64', 'da':'int64', 'db':'int64', 'dc':'int64',
                                        'Sx':'float64', 'Sy':'float64', 'Sz':'float64'})

        # make sure the pinning direction is normalized
        norm = np.sqrt(pinning_df['Sx']**2 + pinning_df['Sy']**2 + pinning_df['Sz']**2)
        pinning_df['Sx'] /= norm
        pinning_df['Sy'] /= norm
        pinning_df['Sz'] /= norm

        # Write the pinning file in csv format that spirit can understand
        with folder.open('pinning.txt', 'w') as f:
            pinning_df.to_csv(f, sep='\t', index=False, header=False)


    def write_couplings_file(self, folder): # pylint: disable=unused-argument
        """Write the couplings.txt file that contains the Jij's"""

        jij_data = self.inputs.jij_data # Collection of numpy arrays
        jij_expanded = jij_data.get_array('Jij_expanded') # Extracts the Jij_expanded array

        # create Dataframe and use either Jijs and DMI vectors or only Jijs if no Dijs are given
        # maybe we need an option to not use the DMI vector even if they are found?
        # Convert the data to Pandas Dataframe
        has_dmi = False
        if len(jij_expanded[0]) >= 8:
            # has Dij's
            # compute magnitude of DMI vector and add after Jij column
            # Dx, Dy, Dz are only used to get direction
            jd = np.zeros((len(jij_expanded), 10))
            jd[:, :6] = jij_expanded[:, :6]
            jd[:, 6] = np.linalg.norm(jij_expanded[:, 6:9], axis=1)
            jd[:, 7:10] = jij_expanded[:, 6:9]
            jijs_df = DataFrame(jd, columns=['i', 'j', 'da', 'db', 'dc', 'Jij', 'Dij', 'Dijx', 'Dijy', 'Dijz'])
            jijs_df['Dijx'] /= jijs_df['Dij']
            jijs_df['Dijy'] /= jijs_df['Dij']
            jijs_df['Dijz'] /= jijs_df['Dij']
            has_dmi = True
        elif len(jij_expanded[0]) >= 6:
            # has Jijs
            jijs_df = DataFrame(jij_expanded[:, :6], columns=['i', 'j', 'da', 'db', 'dc', 'Jij'])
        else:
            # no Jijs found, stop here
            raise ValueError('jij_data invalid')

        if not has_dmi:
            jijs_df = jijs_df.astype({'i':'int64', 'j':'int64', 'da':'int64', 'db':'int64', 'dc':'int64', 'Jij':'float64'})
        else:
            jijs_df = jijs_df.astype({'i':'int64', 'j':'int64', 'da':'int64', 'db':'int64', 'dc':'int64', 'Jij':'float64',
                                      'Dij':'float64', 'Dijx':'float64', 'Dijy':'float64', 'Dijz':'float64'})

        # cut all couplings that are futher away that the cutoff radius
        if self.couplings_rcut is not None:
            r = np.sqrt(np.sum(jij_data.get_array('positions_expanded')**2, axis=1))
            jijs_df = jijs_df[r <= self.couplings_rcut]

        # Write the couplings file in csv format that spirit can understand
        with folder.open('couplings.txt', 'w') as f:
            # spirit wants to have the data separated in tabs
            jijs_df.to_csv(f, sep='\t', index=False)


    def write_run_spirit(self, folder):
        """write the run_spirit.py script that controls the spirit python API."""

        # extract run options from input node
        run_opts = self.inputs.run_options.get_dict()

        # header for run_spirit.py
        header = """import os
### Import Spirit modules
from spirit import state
from spirit import configuration
from spirit import simulation

cfgfile = "input_created.cfg"
quiet = False

with state.State(cfgfile, quiet) as p_state:"""

        # now extract information from run_opts
        method = run_opts.get('simulation_method')
        solver = run_opts.get('solver')
        config = run_opts.get('configuration', {})

        # collect body of run_spirit.py script
        body = '\n'

        # set simulation (LLG, MC, ...)
        # - use method.upper to have case-insensitive input
        # - remember to end each line with '\n'
        if method.upper() == 'LLG':
            body += '    method = simulation.METHOD_LLG\n'
        # here we need to also allow other methods (HTST,GNEB,...)

        # set solver (DEPONDT, ...)
        if solver.upper() == 'DEPONDT':
            body += '    solver = simulation.SOLVER_DEPONDT # Velocity projection minimiser\n'
        # here we also need to be able to set the other solvers

        # set configuration (initialize spins in (plus z, ...)
        if 'plus_z' in config and config.get('plus_z', False):
            body += '    configuration.plus_z(p_state) # start from all spins pointing in +z\n'
        # here we should add additional configurations

        # finalize body with starting the spirit simulation
        body += '    # now run the simulation\n    simulation.start(p_state, method, solver)\n'

        # write run_spirit.py to the folder
        with folder.open(_RUN_SPIRIT, 'w') as f:
            txt = header + body
            f.write(txt)


def _modify_line(my_string, new_value):
    """Gets a line and the new parameter value as inputs
    and returns the line with the new parameter"""

    splitted = my_string.split(' ', 1)
    cnt = 0
    for element in splitted[1]:
        if element == ' ':
            cnt += 1
        else:
            break
    whitespace_count = cnt + 1
    splitted[1] = new_value
    ret_str = splitted[0] + whitespace_count*' ' + splitted[1] + '\n'
    return ret_str


def _get_geometry(structure):
    """Get the geometry string from the structure"""

    # bravais lattice using bravais vectors
    cell = np.array(structure.cell)

    # transformation matrix to relative coordinates
    U2rel = np.linalg.inv(cell.transpose())

    # bravais vectors as strings
    sv = ''
    for element in cell:
        string_v = ' '.join(map(str, element))
        sv += string_v + '\n'

    # sites in unit cell
    num_sites = len(structure.sites)
    sites_pos = ''
    for site in structure.sites:
        pos = site.position
        # transform positions to relative coordinates
        pos_rel = np.dot(U2rel, pos)
        pos_rel = pos_rel%1 # fold back to unit cell
        string_pos = ' '.join(map(str, pos_rel))
        sites_pos += string_pos + '\n'

    # collect string that defines the geometry
    geometry_string = 'bravais_vectors\n' + sv + '\n' + 'basis\n' + str(num_sites) + '\n' + sites_pos

    return geometry_string
