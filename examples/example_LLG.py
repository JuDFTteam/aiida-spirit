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
from aiida_spirit.tools import helpers
from aiida_spirit.tools.helpers import prepare_test_inputs

INPUT_DIR = path.join(path.dirname(path.realpath(__file__)), 'input_files')


def LLG_run(spirit_code):
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
    # (nested keys of the spirit TOML input, merged over aiida_spirit/data/input_defaults.toml)
    parameters = Dict({
        # change spin moment to have the right size for Fe
        'geometry': {'mu_s': 2.2},
        # external field of 5 mT in z direction
        'hamiltonian': {'external_field': {'magnitude': 0.005, 'direction': [0.0, 0.0, 1.0]}},
        'method': {
            'llg': {
                # temperature noise (in K)
                'temperature': 50,
                # limit the number of iterations
                'n_iterations': 200000,
            }
        },
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
    LLG_run(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
