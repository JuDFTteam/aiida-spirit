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
from aiida.orm import SinglefileData, ArrayData
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

        # Check that folder content is as expected
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
        output_node, mag = self.parse_retrieved()
        self.out('output_parameters', output_node)
        self.out('magnetization', mag)

        return ExitCode(0)

    def parse_retrieved(self):
        """Parse the output from the retrieved and create aiida nodes"""

        retrieved = self.retrieved

        # parse info from stdout
        output_filename = _SPIRIT_STDOUT
        self.logger.info("Parsing '{}'".format(output_filename))
        with retrieved.open(output_filename, 'rb') as _f:
            output_node = SinglefileData(file=_f)
            # put some parsing here instead of returning the file ...

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
        mag.set_array('initial', m_init)
        mag.set_array('final', m_final)
        mag.set_array('energ', energ)
        mag.extras['description'] = {
            'initial': 'initial directions of the magnetization vectors',
            'final': 'final directions of the magnetization vectors',
            'energ': 'energy convergence',
        }

        return output_node, mag
