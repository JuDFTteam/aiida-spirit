# -*- coding: utf-8 -*-
""" Tests for calculations

"""
import os
from aiida.plugins import CalculationFactory
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
