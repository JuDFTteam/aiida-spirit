# -*- coding: utf-8 -*-
"""
Parsers provided by aiida_spirit.

Register parsers via the "aiida.parsers" entry point in setup.json.
"""
import numpy as np
from aiida.engine import ExitCode
from aiida.parsers.parser import Parser
from aiida.plugins import CalculationFactory
from aiida.common import exceptions
from aiida.orm import Dict, ArrayData
from masci_tools.io.common_functions import search_string
from .calculations import _RETLIST, _SPIRIT_STDOUT

SpiritCalculation = CalculationFactory('spirit')


class SpiritParser(Parser):
    """
    Parser class for parsing output of calculation.
    """
    def __init__(self, node):
        """
        Initialize Parser instance

        Checks that the ProcessNode being passed was produced by a SpiritCalculation.

        :param node: ProcessNode of calculation
        :param type node: :class:`aiida.orm.ProcessNode`
        """
        super(SpiritParser, self).__init__(node)
        if not issubclass(node.process_class, SpiritCalculation):
            raise exceptions.ParsingError('Can only parse SpiritCalculation')

    def parse(self, **kwargs):
        """
        Parse outputs, store results in database.

        :returns: an exit code, if parsing fails (or nothing if parsing succeeds)
        """

        # Check that folder content is as expected and needed for parsing
        files_retrieved = self.retrieved.list_object_names()
        files_expected = _RETLIST + [
            '_scheduler-stdout.txt', '_scheduler-stderr.txt'
        ]
        # Note: set(A) <= set(B) checks whether A is a subset of B
        if not set(files_expected) <= set(files_retrieved):
            self.logger.error("Found files '{}', expected to find '{}'".format(
                files_retrieved, files_expected))
            return self.exit_codes.ERROR_MISSING_OUTPUT_FILES

        # parse information from output file (number of iterations, convergence info, ...)
        output_node, mag, energ = self.parse_retrieved()
        self.out('output_parameters', output_node)
        self.out('magnetization', mag)
        self.out('energies', energ)

        # check consistency of spirit_version_info with the inputs
        if 'pinning' in self.node.inputs:
            version_info = output_node['spirit_version_info']
            if not 'enabled' in version_info['Pinning']:
                return self.exit_codes.ERROR_SPIRIT_CODE_INCOMPATIBLE
        if 'defects' in self.node.inputs:
            version_info = output_node['spirit_version_info']
            if not 'enabled' in version_info['Defects']:
                return self.exit_codes.ERROR_SPIRIT_CODE_INCOMPATIBLE

        return ExitCode(0)

    def parse_retrieved(self):
        """Parse the output from the retrieved and create aiida nodes"""

        retrieved = self.retrieved

        # parse info from stdout
        output_filename = _SPIRIT_STDOUT
        self.logger.info("Parsing '{}'".format(output_filename))
        with retrieved.open(output_filename, 'r') as _f:
            txt = _f.readlines()
        out_dict = parse_outfile(txt)
        output_node = Dict(dict=out_dict)

        # parse output files
        self.logger.info('Parsing energy archive')
        with retrieved.open('spirit_Image-00_Energy-archive.txt') as _f:
            energ = np.loadtxt(_f, skiprows=1)
        self.logger.info('Parsing initial magnetization')
        with retrieved.open('spirit_Image-00_Spins-initial.ovf') as _f:
            m_init = np.loadtxt(_f)
        self.logger.info('Parsing final magnetization')
        with retrieved.open('spirit_Image-00_Spins-final.ovf') as _f:
            m_final = np.loadtxt(_f)

        # collect arrays in ArrayData
        mag = ArrayData()
        mag.set_array(
            'initial',
            np.nan_to_num(m_init))  # nan_to_num is needed with defects
        mag.set_array('final', np.nan_to_num(m_final))
        mag.extras['description'] = {
            'initial': 'initial directions of the magnetization vectors',
            'final': 'final directions of the magnetization vectors',
        }
        energies = ArrayData()
        energies.set_array('energies', energ)
        energies.extras['description'] = {
            'energies': 'energy convergence',
        }

        return output_node, mag, energies


def parse_outfile(txt):
    """parse the spirit output file"""

    out_dict = {}

    itmp = search_string('Total duration', txt)
    if itmp >= 0:
        t_str = txt[itmp].split()[2]
        tmp = [float(i) for i in t_str.split(':')]
        t_sec = tmp[0] * 3600 + tmp[1] * 60 + tmp[2]
        out_dict['runtime'] = t_str
        out_dict['runtime_sec'] = t_sec

    itmp = search_string('Iterations / sec', txt)
    if itmp >= 0:
        tmp = txt[itmp].split()[-1]
        it_per_s = float(tmp)
        out_dict['it_per_s'] = it_per_s

    itmp = search_string('Simulated time', txt)
    if itmp >= 0:
        tmp = txt[itmp].split()
        sim_time = float(tmp[-2])
        sim_time_unit = tmp[-1]
        out_dict['simulation_time'] = sim_time
        out_dict['simulation_time_unit'] = sim_time_unit

    itmp = search_string('Number of  Errors', txt)
    if itmp >= 0:
        tmp = txt[itmp].split()
        num_errors = int(tmp[-1])
        out_dict['num_errors'] = num_errors

    itmp = search_string('Number of Warnings', txt)
    if itmp >= 0:
        tmp = txt[itmp].split()
        num_warn = int(tmp[-1])
        out_dict['num_warnings'] = num_warn

    itmp = search_string('Terminated', txt)
    if itmp >= 0:
        tmp = txt[itmp].split()
        out_dict['simulation_mode'] = tmp[-3]

    itmp = search_string('Solver:', txt)
    if itmp >= 0:
        tmp = txt[itmp].split()
        out_dict['solver'] = tmp[-1]

    # parse information on the spirit executable (i.e. check parallelization and enabled features)
    spirit_version_info = {}
    for key in [
            'Version', 'Revision', 'OpenMP', 'CUDA', 'std::thread', 'Defects',
            'Pinning', 'scalar type'
    ]:
        itmp = search_string(key, txt)
        if itmp >= 0:
            found_str = txt[itmp].replace('==========', '').replace('  ', '')
            if found_str[0] == ' ':
                found_str = found_str[1:-1]
            spirit_version_info[key] = found_str
    out_dict['spirit_version_info'] = spirit_version_info

    return out_dict
