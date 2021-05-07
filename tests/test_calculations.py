# -*- coding: utf-8 -*-
""" Tests for calculations

"""
from aiida.plugins import CalculationFactory
from aiida.engine import run
from aiida_spirit.helpers import prepare_test_inputs

from . import TEST_DIR


def test_process(spirit_code):
    """Test running a calculation
    note this does not test that the expected outputs are created of output parsing"""

    # Prepare input parameters
    inputs = prepare_test_inputs(TEST_DIR)
    inputs['code'] = spirit_code
    inputs['metadata']['options'] = {
        # 5 mins max runtime
        'max_wallclock_seconds': 300
    }

    result = run(CalculationFactory('spirit'), **inputs)

    assert result is not None
