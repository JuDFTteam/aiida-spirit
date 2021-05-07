# -*- coding: utf-8 -*-
""" Tests for calculations

"""
import os
import numpy as np
from aiida.plugins import CalculationFactory
from aiida.engine import run
from aiida.orm import Dict, StructureData, ArrayData

from . import TEST_DIR


def test_process(spirit_code):
    """Test running a calculation
    note this does not test that the expected outputs are created of output parsing"""

    # Prepare input parameters
    parameters = Dict(dict={})
    # example structure: bcc Fe
    structure = StructureData(cell=[[1.42002584, 1.42002584, 1.42002584],
                                    [1.42002584, -1.42002584, -1.42002584],
                                    [-1.42002584, 1.42002584, -1.42002584]])
    structure.append_atom(position=[0, 0, 0], symbols='Fe')
    # create jij couplings input from csv export
    jijs_expanded = np.load(
        os.path.join(TEST_DIR, 'input_files', 'Jij_expanded.npy'))
    jij_data = ArrayData()
    jij_data.set_array('Jij_expanded', jijs_expanded)

    # set up calculation
    inputs = {
        'code': spirit_code,
        'parameters': parameters,
        'jij_data': jij_data,
        'metadata': {
            'description': 'Test job submission with the aiida_spirit plugin',
            'options': {
                'max_wallclock_seconds': 300  # 5 mins max runtime
            },
        },
    }

    result = run(CalculationFactory('spirit'), **inputs)

    assert result is not None
