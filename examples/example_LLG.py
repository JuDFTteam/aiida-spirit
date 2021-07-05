#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a test calculation on localhost.

Usage: ./example_01.py
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
OUTPUT_DIR = path.join(path.dirname(path.realpath(__file__)),
                       'output_files/temperature_spins.txt')


def test_run(spirit_code):
    """Run a calculation on the localhost computer.

    Uses test helpers to create AiiDA Code on the fly.
    """
    if not spirit_code:
        # get code
        computer = helpers.get_computer()
        spirit_code = helpers.get_code(entry_point='spirit', computer=computer)

    inputs = prepare_test_inputs(INPUT_DIR)
    # add the spirit code to the inputs
    inputs['code'] = spirit_code
    # prepare parameters
    output_contents = ''
    for i in range(0, 1051, 50):
        parameters = Dict(
            dict={
                'llg_temperature': str(i),  # temperature noise (in K)
                'external_field_magnitude':
                '0.005',  # external field of 0.005 T
                'external_field_normal':
                '0.0 0.0 1.0',  # external field points in z direction
                'mu_s':
                '2.2',  # change spin moment to have the right size for Fe
                'llg_n_iterations': '200000'  # limit the number of iterations
            })
        inputs['parameters'] = parameters

        # Note: in order to submit your calculation to the aiida daemon, do:
        # from aiida.engine import submit
        # future = submit(CalculationFactory('spirit'), **inputs)
        result = engine.run(CalculationFactory('spirit'), **inputs)

        #computed_diff = result['spirit'].get_content()
        print(f'Computed result: {result}')

        ret = result['retrieved']
        with ret.open('spirit_Image-00_Spins-final.ovf') as _file:
            spins_final = np.loadtxt(_file)
        mag_mean = np.mean(spins_final, axis=0)
        output_contents += str(i) + '\t' + str(mag_mean[2]) + '\n'

    with open(OUTPUT_DIR, 'w') as output_file:
        output_file.write(output_contents)


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
