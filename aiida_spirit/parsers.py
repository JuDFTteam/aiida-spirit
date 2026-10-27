# -*- coding: utf-8 -*-
"""
Parsers provided by aiida_spirit.

Register parsers via the "aiida.parsers" entry point in setup.json.
"""
import pathlib
import numpy as np
from aiida.engine import ExitCode
from aiida.parsers.parser import Parser
from aiida.plugins import CalculationFactory
from aiida.common import exceptions
from aiida.orm import Dict, ArrayData
from masci_tools.io.common_functions import search_string
from .calculations import _RETLIST, _SPIRIT_STDOUT, _ATOM_TYPES

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
        super(SpiritParser, self).__init__(node)  # pylint: disable=super-with-arguments
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
        retrieved_dict = self.parse_retrieved()

        # parse files in temporary folder
        # these files are not kept in the file repository but become numy arrays and are stored as ArrayData output nodes
        retrieved_temporary_folder = kwargs.get('retrieved_temporary_folder',
                                                None)
        if retrieved_temporary_folder is not None:
            retrieved_dict = self.parse_temporary_retrieved(
                retrieved_dict, retrieved_temporary_folder)

        for key, value in retrieved_dict.items():
            self.out(key, value)

        # check consistency of spirit_version_info with the inputs
        output_node = retrieved_dict['output_parameters']
        if 'pinning' in self.node.inputs:
            version_info = output_node['spirit_version_info']
            if 'not enabled' in version_info['Pinning']:
                return self.exit_codes.ERROR_SPIRIT_CODE_INCOMPATIBLE
        if 'defects' in self.node.inputs:
            version_info = output_node['spirit_version_info']
            if 'not enabled' in version_info['Defects']:
                return self.exit_codes.ERROR_SPIRIT_CODE_INCOMPATIBLE

        return ExitCode(0)

    def _parse_if_found(self, filename, *args, folder=None, **kwargs):
        """Parses a file and loads it with `np.loadtxt`.
        The `*args` and `**kwargs` are passed to `np.loadtxt`.
        If the file is not found it returns None."""
        if folder is None:
            folder = self.retrieved
            if filename in folder.list_object_names():
                with folder.open(filename, 'r') as _f:
                    return np.loadtxt(_f, *args, **kwargs)
            else:
                return self._file_not_found(filename)
        else:
            filenames = [f.name for f in folder.glob('*')]
            if filename in filenames:
                with (folder / filename).open('r') as _f:
                    return np.loadtxt(_f, *args, **kwargs)
            else:
                return self._file_not_found(filename)

    def _parse_energy(self, filename, folder):
        """Parse a spirit energy file into an array (one row per saved iteration).
        Header lines and the separator lines (readability option) are skipped and
        the column separators `|` are ignored. Returns None if the file is not found."""
        path = folder / filename
        if not path.exists():
            return self._file_not_found(filename)
        rows = []
        for line in path.read_text().replace('|', ' ').splitlines():
            try:
                row = [float(val) for val in line.split()]
            except ValueError:
                continue
            if row:
                rows.append(row)
        return np.atleast_2d(np.array(rows))

    def _file_not_found(self, filename):
        self.logger.info('{} not found!'.format(filename))

    def parse_retrieved(self):  # pylint: disable=too-many-locals
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
        self.logger.info('Parsing atom types')
        atyp = self._parse_if_found(_ATOM_TYPES)

        # Write dictionary of retrieved quantities
        _retrieved_dict = {'output_parameters': output_node}

        # collect arrays in ArrayData
        if atyp is not None:
            atypes = ArrayData()
            atypes.set_array('atom_types', atyp)
            atypes.extras['description'] = {
                'atom_types': 'list of atom types for all positions',
            }
            _retrieved_dict.update({'atom_types': atypes})

        return _retrieved_dict

    def parse_temporary_retrieved(self, _retrieved_dict,
                                  retrieved_temporary_folder):
        """Parse files that are defined in the retrieve_temporary_list"""
        retrieved_temporary_folder = pathlib.Path(retrieved_temporary_folder)

        self.logger.info('Parsing energy archive')
        energ = self._parse_energy('spirit_Image-00_Energy-archive.txt',
                                   retrieved_temporary_folder)

        self.logger.info('Parsing initial magnetization')
        m_init = self._parse_if_found('spirit_Image-00_Spins-initial.ovf',
                                      folder=retrieved_temporary_folder)

        self.logger.info('Parsing final magnetization')
        m_final = self._parse_if_found('spirit_Image-00_Spins-final.ovf',
                                       folder=retrieved_temporary_folder)

        self.logger.info('Parsing MC output')
        out_mc = self._parse_if_found('output_mc.txt',
                                      folder=retrieved_temporary_folder)

        if m_init is not None and m_final is not None:
            mag = ArrayData()
            mag.set_array(
                'initial',
                np.nan_to_num(m_init))  # nan_to_num is needed with defects
            mag.set_array('final', np.nan_to_num(m_final))
            mag.extras['description'] = {
                'initial': 'initial directions of the magnetization vectors',
                'final': 'final directions of the magnetization vectors',
            }
            _retrieved_dict.update({'magnetization': mag})

        if energ is not None:
            energies = ArrayData()
            energies.set_array('energies', energ)
            energies.extras['description'] = {
                'energies': 'Energy convergence with iterations.',
            }
            _retrieved_dict.update({'energies': energies})

        # Only add mc if it is found
        if out_mc is not None:
            output_mc = ArrayData()

            # Associante the columns of out_mc with individual arrays
            array_names = [
                'temperature', 'energy', 'magnetization', 'susceptibility',
                'specific_heat', 'binder_cumulant'
            ]
            for i, name in enumerate(array_names):
                output_mc.set_array(name, out_mc[:, i])

            output_mc.extras['description'] = {
                'temperature':
                'The temperature at which the sampling was performed',
                'energy':
                'The average energy at the sampled temperature',
                'magnetization':
                'The average spin direction at the sample temperature',
                'susceptibility':
                'The susceptibility at the sampled temperature',
                'specific_heat':
                'The specific heat at the sampled temperature',
                'binder_cumulant':
                'The binder_cumulant at the sampled temperature',
            }
            _retrieved_dict.update({'monte_carlo': output_mc})

        return _retrieved_dict


def _runtime(line):
    """Runtime string and seconds from the 'Total duration' line"""
    t_str = line.split()[2]
    hours, minutes, seconds = (float(i) for i in t_str.split(':'))
    return {'runtime': t_str, 'runtime_sec': hours * 3600 + minutes * 60 + seconds}


# search string in the spirit stdout -> function that turns the found line into output entries
_OUTFILE_ENTRIES = {
    'Total duration': _runtime,
    'Iterations / sec': lambda line: {'it_per_s': float(line.split()[-1])},
    'Simulated time': lambda line: {'simulation_time': float(line.split()[-2]),
                                    'simulation_time_unit': line.split()[-1]},
    'Number of  Errors': lambda line: {'num_errors': int(line.split()[-1])},
    'Number of Warnings': lambda line: {'num_warnings': int(line.split()[-1])},
    'Terminated': lambda line: {'simulation_mode': line.split()[-3]},
    'Solver:': lambda line: {'solver': line.split()[-1]},
}


def parse_outfile(txt):
    """parse the spirit output file

    A line that cannot be parsed (e.g. garbled by output of a post-processing script
    interleaved with spirit's log) is skipped instead of failing the whole parsing."""

    out_dict = {}
    for search, get_entries in _OUTFILE_ENTRIES.items():
        itmp = search_string(search, txt)
        if itmp >= 0:
            try:
                out_dict.update(get_entries(txt[itmp]))
            except (ValueError, IndexError):
                out_dict.setdefault('unparsed_lines', []).append(txt[itmp].strip())

    # parse information on the spirit executable (i.e. check parallelization and enabled features)
    spirit_version_info = {}
    for key in [
            'Version', 'Revision', 'OpenMP', 'CUDA', 'std::thread', 'Defects',
            'Pinning', 'scalar type'
    ]:
        itmp = search_string(key, txt)
        if itmp >= 0:
            found_str = txt[itmp].replace('==========', '').replace('  ', '')
            spirit_version_info[key] = found_str.strip()
    out_dict['spirit_version_info'] = spirit_version_info

    return out_dict
