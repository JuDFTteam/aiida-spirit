# -*- coding: utf-8 -*-
""" Tests for calculations

"""
import os
import numpy as np
from aiida.plugins import CalculationFactory
from aiida.orm import Dict
from aiida.engine import run
from aiida_spirit.helpers import prepare_test_inputs

from . import TEST_DIR


def test_spirit_calc_dry_run(spirit_code):
    """Test running a calculation
    note this does only a dry run to check if the calculation plugin works"""

    # Prepare input parameters
    inputs = prepare_test_inputs(os.path.join(TEST_DIR, 'input_files'))
    inputs['code'] = spirit_code
    inputs['metadata']['options'] = {
        # 5 mins max runtime
        'max_wallclock_seconds': 300
    }
    inputs['metadata']['dry_run'] = True

    result = run(CalculationFactory('spirit'), **inputs)
    print(result)

    assert result is not None


def test_spirit_calc(spirit_code):
    """Test running a calculation
    this actually runs spirit and therefore needs
    to have spirit installed in the python environment."""

    # Prepare input parameters
    inputs = prepare_test_inputs(os.path.join(TEST_DIR, 'input_files'))
    inputs['code'] = spirit_code
    inputs['metadata']['options'] = {
        # 5 mins max runtime
        'max_wallclock_seconds': 300
    }

    result = run(CalculationFactory('spirit'), **inputs)
    print(result)

    # check consistency of the output files
    check_outcome(result)


def test_spirit_calc_with_param(spirit_code):
    """Test running a calculation
    this actually runs spirit and therefore needs
    to have spirit installed in the python environment.

    This test runs a spirit calculation with an external field and a small temperature
    """

    # Prepare input parameters
    inputs = prepare_test_inputs(os.path.join(TEST_DIR, 'input_files'))
    inputs['code'] = spirit_code
    inputs['metadata']['options'] = {
        # 5 mins max runtime
        'max_wallclock_seconds': 300
    }
    # prepare parameters
    parameters = Dict(
        dict={
            'llg_temperature': '10',  # 10 K temperature noise
            'external_field_magnitude': '2.0',  # external field of 2 T
            'external_field_normal':
            '0.0 0.0 1.0',  # external field points in z direction
            'mu_s': '2.2',  # change spin moment to have the right size for Fe
            'llg_n_iterations': '20000'  # limit the number of iterations
        })
    inputs['parameters'] = parameters

    # first a dry run
    inputs['metadata']['dry_run'] = True
    result = run(CalculationFactory('spirit'), **inputs)

    # then run the calculation
    inputs['metadata']['dry_run'] = False
    result = run(CalculationFactory('spirit'), **inputs)
    print(result)

    # check consistency of the output files
    spins_final = check_outcome(result, threshold=0.10)
    mag_mean = np.mean(spins_final, axis=0)
    print(mag_mean)
    assert mag_mean[0] < 0.25
    assert mag_mean[1] < 0.25
    assert mag_mean[2] > 0.85


def check_outcome(result, threshold=1e-5):
    """check the result of a spirit calculation
    Checks if retrieved is there and if the output inside of the retreived makes sense"""

    # check output
    assert 'retrieved' in result
    ret = result['retrieved']
    out_file_list = ret.list_object_names()

    # check if spirit std out exists
    print(f'contents of retrieved: {out_file_list}')
    assert 'spirit.stdout' in out_file_list
    with ret.open('spirit.stdout') as _file:
        txt = _file.readlines()
    assert len(txt) > 100

    # check some lines in the spirit std output
    for line in txt:
        if 'Number of  Errors:' in line:
            errors = line.split()[-1]
        if 'Number of Warnings:' in line:
            warnings = line.split()[-1]
    assert int(errors) == 0
    assert int(warnings) == 0

    # check if initial and final spin image make sense
    assert 'spirit_Image-00_Spins-initial.ovf' in out_file_list
    with ret.open('spirit_Image-00_Spins-initial.ovf') as _file:
        spins_initial = np.loadtxt(_file)
    var_initial = np.std(spins_initial, axis=0).max()
    print(var_initial)
    assert var_initial > 0.4

    assert 'spirit_Image-00_Spins-final.ovf' in out_file_list
    with ret.open('spirit_Image-00_Spins-final.ovf') as _file:
        spins_final = np.loadtxt(_file)
    var_final = np.std(spins_final, axis=0).max()
    print(var_final)
    assert var_final < threshold

    return spins_final
