#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=duplicate-code
"""Run a test calculation on localhost.

Usage: ./example_LLG.py
"""

from os import path
import numpy as np
import click
from aiida import cmdline, engine
from aiida.orm import Dict
from aiida.plugins import CalculationFactory
from aiida_spirit import helpers
from aiida_spirit.helpers import prepare_test_inputs

INPUT_DIR = path.join(path.dirname(path.realpath(__file__)), 'input_files')


def test_run(spirit_code):
    """Run a calculation on the localhost computer.

    Uses test helpers to create AiiDA Code on the fly.
    """
    if not spirit_code:
        # get code
        computer = helpers.get_computer()
        spirit_code = helpers.get_code(entry_point='spirit', computer=computer)

    # use template input, prepared for a simple bcc Fe example
    inputs = prepare_test_inputs(INPUT_DIR)

    # add the spirit code to the inputs
    inputs['code'] = spirit_code

    # prepare parameters
    parameters = Dict(
        dict={
            # temperature noise (in K)
            'llg_temperature': 50,
            # external field of 5 mT
            'external_field_magnitude': 0.005,
            # external field points in z direction
            'external_field_normal': [0.0, 0.0, 1.0],
            # change spin moment to have the right size for Fe
            'mu_s': [2.2],
            # limit the number of iterations
            'llg_n_iterations': 200000
        })
    inputs['parameters'] = parameters

    # Note: in order to submit your calculation to the aiida daemon, do:
    # from aiida.engine import submit
    # future = submit(CalculationFactory('spirit'), **inputs)
    result = engine.run(CalculationFactory('spirit'), **inputs)

    print(f'Computed result: {result}')
    spins_final = result['magnetization'].get_array('final')
    mag_mean = np.mean(spins_final, axis=0)

    print(f'mean magnetization direction: {mag_mean}')


@click.command()
@cmdline.utils.decorators.with_dbenv()
@cmdline.params.options.CODE()
def cli(code):
    """Run example.

    Example usage: $ ./example_LLG.py --code spirit@localhost

    Alternative (creates spirit@localhost-test code): $ ./example_LLG.py

    Help: $ ./example_LLG.py --help
    """
    test_run(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
