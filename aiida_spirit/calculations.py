# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_spirit.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""
from os import path  #modification to run test
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import Dict, StructureData, ArrayData
from pandas import DataFrame

TEMPLATE_PATH = path.join(path.dirname(path.realpath(__file__)),
                          'data/input_original.cfg')


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

        # new ports
        # put here the input ports (parameters, structure, jij_data
        spec.input('parameters', valid_type=Dict, help='Use a node that specifies the input parameters')
        spec.input('structure', valid_type=StructureData, required=True,
                   help='Use a node that specifies the input crystal structure')
        spec.input('jij_data', valid_type=ArrayData, required=True,
                   help='Use a node that specifies the full list of pairwise interactions')
        # define exit codes that are used to terminate the SpiritCalculation
        spec.exit_code(100, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')

        # define file names
        cls._RUN_SPIRIT = 'run_spirit.py' # python file that runs the spirit job through the spirit python API
        cls._SPIRIT_STDOUT = 'spirit.stdout' # filename where the stdout of the spirit run is put


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

        parameters = self.inputs.parameters
        input_dict = parameters.get_dict() #(would it be better to use "try, except" ?)


        # gets a line and the new parameter value as inputs and returns the line with the new parameter
        def modify_line(my_string, new_value):
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

        new_dict = {}
        with open(TEMPLATE_PATH, 'r') as f_orig:
            for num, line in enumerate(f_orig, 1):
                new_dict[num] = line                 # create dictionary with keys=line_number and values=line_text

                if line[0] != '#' or '\n':             # if line is not a comment or line is not empty
                    # check if the parameter has to be modified and use function to modify line if needed
                    l_param_value = line.split(' ', 1)
                    param = l_param_value[0]

                    if param in input_dict.keys():
                        if param not in ['bravais lattice', 'interaction_pairs_file']:
                            modif_line = modify_line(line, input_dict[param])
                            new_dict[num] = modif_line


                    ##############################################
                    # MODIFY "GEOMETRY" SECTION FROM .cfg FILE
                    # from the StructureData node given as an input, the "GEOMETRY" section is created

                    if param == 'bravais_lattice':

                        structure = self.inputs.structure

                        # bravais lattice using bravais vectors
                        cell = structure.cell
                        sv = ''
                        for element in cell:
                            string_v = ' '.join(map(str, element))
                            sv += string_v + '\n'
                        # sites in unit cell
                        num_sites = len(structure.sites)
                        sites_pos = ''
                        for site in structure.sites:
                            string_pos = ' '.join(map(str, site.position))
                            sites_pos += string_pos + '\n'

                        # write geometry section to file
                        geometry_string = 'bravais_vector\n' + sv + '\n' + 'basis\n' + str(num_sites) + '\n' + sites_pos
                        new_dict[num] = geometry_string


        with folder.open('input_created.cfg', 'w') as f_created:
            # write new contents to a new file, which will be used for the calculations
            text = ''
            for element in new_dict:
                text += new_dict[element]
            f_created.write(text)



    ##############################################
    # CREATE "couplings.txt" FILE FROM Jij

        jij_data = self.inputs.jij_data # Collection of numpy arrays
        jij_expanded = jij_data.get_array('Jij_expanded') # Extracts the Jij_expanded array

        jijs_df = DataFrame(jij_expanded, columns=['i', 'j', 'da', 'db', 'dc', 'Jij']) # Convert the data to Pandas Dataframe
        jijs_df = jijs_df.astype({'i':'int64', 'j':'int64', 'da':'int64', 'db':'int64', 'dc':'int64', 'Jij':'float64'})
        # Write the couplings file in csv format that spirit can understand
        with folder.open('couplings.txt', 'w') as f:
            jijs_df.to_csv(f, sep='\t', index=False) # spirit wants to have the data separated in tabs

        ##############################################
        # CREATE "run_spirit.py"

        #TODO: put here he code that write the spirit.py file
        with folder.open('run_spirit.py', 'w') as f:
            f.write(
                """import os
import sys

### Import Spirit modules
from spirit import state
from spirit import configuration
from spirit import simulation
from spirit import io

cfgfile = "input_created.cfg"
quiet = False

with state.State(cfgfile, quiet) as p_state:
    ### LLG dynamics simulation
    LLG = simulation.METHOD_LLG
    DEPONDT = simulation.SOLVER_DEPONDT # Velocity projection minimiser
    simulation.start(p_state, LLG, DEPONDT)
                """)


        ##############################################
        # FINALLY GIVE THE INFORMATION TO AIIDA

        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.withmpi = self.inputs.metadata.options.withmpi
        codeinfo.stdin_name = self._RUN_SPIRIT
        codeinfo.stdout_name = self._SPIRIT_STDOUT

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        # this should be a list of the filenames we expect when spirit ran
        # i.e. the files we specify here will be copied back to the file repository
        calcinfo.retrieve_list = [self._SPIRIT_STDOUT]

        return calcinfo
