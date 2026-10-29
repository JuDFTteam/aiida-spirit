# -*- coding: utf-8 -*-
"""Tests for the parsing of the spirit stdout"""
from aiida_spirit.parsers import parse_outfile

# excerpt of a spirit develop (b3b94c2a) stdout; the 'Simulated time' line is garbled by a print
# of the run script that landed in the middle of spirit's (block buffered) log line
STDOUT = """\
==========     Version:  2.2.0
    Defects are not enabled
    Pinning is not enabled
------------ Terminated LLG Calculation ------------
    Total duration:    0:0:5.246
    Iterations / sec:  909.94
    Solver: Depondt
    Simulated time:       0.01100E_CHECK -1.201734330353473
    Number of  Errors:  0
    Number of Warnings: 0
""".splitlines(keepends=True)


def test_parse_outfile():
    """Entries are parsed, a garbled line is skipped and reported instead of failing"""
    out = parse_outfile(STDOUT)
    assert out['runtime_sec'] == 5.246
    assert out['it_per_s'] == 909.94
    assert out['solver'] == 'Depondt'
    assert out['simulation_mode'] == 'LLG'
    assert out['num_errors'] == 0 and out['num_warnings'] == 0
    assert 'simulation_time' not in out
    assert out['unparsed_lines'] == [
        'Simulated time:       0.01100E_CHECK -1.201734330353473'
    ]
    assert out['spirit_version_info']['Pinning'] == 'Pinning is not enabled'
    assert out['spirit_version_info'][
        'Version'] == 'Version:2.2.0'  # double spaces are removed
