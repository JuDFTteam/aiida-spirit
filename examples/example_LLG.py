#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a test calculation on localhost.

Usage: ./example_01.py
"""
from os import path
import click
import numpy as np
from aiida import cmdline, engine
from aiida.orm import Dict, StructureData, ArrayData
from aiida.plugins import CalculationFactory
from aiida_spirit import helpers

INPUT_DIR = path.join(path.dirname(path.realpath(__file__)), 'input_files')


def test_run(spirit_code):
    """Run a calculation on the localhost computer.

    Uses test helpers to create AiiDA Code on the fly.
    """
    if not spirit_code:
        # get code
        computer = helpers.get_computer()
        spirit_code = helpers.get_code(entry_point='spirit', computer=computer)

    # Prepare input parameters
    parameters = Dict(dict={})
    # example structure: bcc Fe
    structure = StructureData(cell=[[1.42002584, 1.42002584, 1.42002584],
                                    [1.42002584, -1.42002584, -1.42002584],
                                    [-1.42002584, 1.42002584, -1.42002584]])
    structure.append_atom(position=[0, 0, 0], symbols='Fe')
    # create jij couplings input from csv export
    jijs_expanded = np.load(path.join(INPUT_DIR, 'Jij_expanded.npy'))
    jij_data = ArrayData()
    jij_data.set_array('Jij_expanded', jijs_expanded)

    # set up calculation
    inputs = {
        'code': spirit_code,
        'parameters': parameters,
        'jij_data': jij_data,
        'metadata': {
            'description': 'Test job submission with the aiida_spirit plugin',
        },
    }

    # Note: in order to submit your calculation to the aiida daemon, do:
    # from aiida.engine import submit
    # future = submit(CalculationFactory('spirit'), **inputs)
    result = engine.run(CalculationFactory('spirit'), **inputs)

    #computed_diff = result['spirit'].get_content()
    print(f'Computed result: {result}')


@click.command()
@cmdline.utils.decorators.with_dbenv()
@cmdline.params.options.CODE()
def cli(code):
    """Run example.

    Example usage: $ ./example_01.py --code diff@localhost

    Alternative (creates diff@localhost-test code): $ ./example_01.py

    Help: $ ./example_01.py --help
    """
    test_run(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
