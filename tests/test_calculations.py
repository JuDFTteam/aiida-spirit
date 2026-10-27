# -*- coding: utf-8 -*-
""" Tests for calculations

"""
import os
import pathlib
import tomllib
import numpy as np
import pytest
from aiida.plugins import CalculationFactory
from aiida.orm import StructureData, Dict, ArrayData
from aiida.engine import run, run_get_node
from aiida_spirit.tools.helpers import prepare_test_inputs

from . import TEST_DIR


def test_input_para_validator():
    """Check that the parameters validator rejects invalid input and accepts nested TOML keys"""

    for params in [
            {'llg_n_iterations': 17},  # legacy flat key
            {'hamiltonian': {'pairs': 'file://x.txt'}},  # set by the plugin
            {'geometry': {'bravais_lattice': 'sc'}},  # set by the plugin
            {'method': {'mc': {'output': {'folder': 'x'}}}},  # set by the plugin
            {'method': {'llg': {'n_iterations': None}}},  # not TOML
    ]:
        builder = CalculationFactory('spirit').get_builder()
        with pytest.raises(ValueError):
            builder.parameters = Dict(params)

    builder = CalculationFactory('spirit').get_builder()
    builder.parameters = Dict({'method': {'llg': {'n_iterations': 17}}, 'couplings_cutoff_radius': 2.5})


def _dry_run_folder(node):
    """Folder with the input files written by a dry run"""
    return pathlib.Path(node.dry_run_info['folder'])


def _read_table(path):
    """Read a tab separated spirit table (with header line) into a dict of columns"""
    lines = path.read_text().splitlines()
    header = lines[0].split()
    data = np.array([line.split() for line in lines[1:]], dtype=float).reshape(-1, len(header))
    return {key: data[:, i] for i, key in enumerate(header)}


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

    result, node = run_get_node(CalculationFactory('spirit'), **inputs)
    print(result)

    assert result is not None
    folder = _dry_run_folder(node)
    with (folder / 'input.toml').open('rb') as _f:
        config = tomllib.load(_f)
    assert config['hamiltonian']['pairs'] == 'file://couplings.txt'
    assert 'two_site_anisotropy' not in config['hamiltonian']
    assert config['geometry']['basis'] == [[0.0, 0.0, 0.0]]
    assert config['defaults']['output'] == {'file_tag': 'spirit', 'folder': '.'}
    couplings = _read_table(folder / 'couplings.txt')
    assert list(couplings) == ['i', 'j', 'da', 'db', 'dc', 'Jij']
    assert len(couplings['Jij']) == 700


def test_spirit_dmi_pinning_defects_dry_run(spirit_code):
    """Test running a calculation
    note this does only a dry run to check if the calculation plugin works"""

    inputs = {'metadata': {}}
    # test structure
    structure = StructureData(
        cell=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    structure.append_atom(position=[0., 0., 0.], symbols='Fe')
    inputs['structure'] = structure
    # test jijs with DMI vectors
    jijs = np.array([
        [0, 0, 1, 0, 0, 10.0, 6.0, 0.0, 0.0],
        [0, 0, 0, 1, 0, 10.0, 0.0, 6.0, 0.0],
        [0, 0, 0, 0, 1, 10.0, 0.0, 0.0, 6.0],
    ])
    jij_data = ArrayData()
    jij_data.set_array('Jij_expanded', jijs)
    inputs['jij_data'] = jij_data
    # input parameters
    inputs['parameters'] = Dict({
        'geometry': {
            'mu_s': 2.2,  # spin moment in mu_Bohr
            'n_basis_cells': [10, 10, 10],  # Spirit supercell
        },
        'hamiltonian': {
            # external magnetic field in T (point in +z direction)
            'external_field': {'magnitude': 0.5, 'direction': [0.0, 0.0, 1.0]},
            # single-ion anisotropy in meV
            'anisotropy': {'magnitude': 1., 'normal': [0.0, 0.0, 1.0]},
        },
        'method': {
            'llg': {
                'n_iterations': 50000,
                'n_iterations_log': 1000,
                'temperature': 4,  # temperature noise (K)
                'dt': 1.0E-3,  # LLG time step (ps)
                'force_convergence': 1e-7,
            }
        },
    })
    # run options
    inputs['run_options'] = Dict(
        dict={
            'simulation_method': 'llg',
            'solver': 'depondt',
            'configuration': {
                'plus_z': True
            },
        })
    # pinning input
    pinning = ArrayData()
    pinning.set_array(
        'pinning', np.array([
            [0, 8, 0, 0, 0, 0, 1],
            [0, 9, 0, 0, 0, 0, 1],
        ]))
    inputs['pinning'] = pinning
    # defects input
    defects = ArrayData()
    defects.set_array(
        'defects',
        np.array([
            # i, da, db, dc, itype
            [0, 0, 0, 0, -1],
            [0, 1, 0, 0, 1],
        ]))
    defects.set_array(
        'atom_types',
        np.array([
            # i, itype, mu_s, concentration,
            [0, 0, 2.2, 0.8],
            [0, 1, 1.1, 0.2],
        ]))
    inputs['defects'] = defects
    # code and computer options
    inputs['code'] = spirit_code
    inputs['metadata']['options'] = {
        # 5 mins max runtime
        'max_wallclock_seconds': 300
    }
    inputs['metadata']['dry_run'] = True

    result, node = run_get_node(CalculationFactory('spirit'), **inputs)
    print(result, node)

    assert result is not None
    assert 'pinning.txt' in node.get_retrieve_list()
    assert 'defects.txt' in node.get_retrieve_list()

    folder = _dry_run_folder(node)
    with (folder / 'input.toml').open('rb') as _f:
        config = tomllib.load(_f)
    geometry = config['geometry']
    assert geometry['pinning']['pinned'] == 'file://pinning.txt'
    assert geometry['defects'] == 'file://defects.txt'
    assert geometry['atom_types'].splitlines() == ['i type mu_s c', '0 0 2.200000 0.800000', '0 1 1.100000 0.200000']
    assert geometry['mu_s'] == 2.2
    assert config['method']['llg']['n_iterations'] == 50000
    assert config['method']['llg']['damping'] == 0.3  # from the plugin defaults
    assert list(_read_table(folder / 'pinning.txt')) == ['i', 'da', 'db', 'dc', 'x', 'y', 'z']
    assert list(_read_table(folder / 'defects.txt')) == ['i', 'da', 'db', 'dc', 'type']
    couplings = _read_table(folder / 'couplings.txt')
    assert list(couplings) == ['i', 'j', 'da', 'db', 'dc', 'Jij', 'Dijx', 'Dijy', 'Dijz']
    assert np.allclose(couplings['Dijz'], [0, 0, 6.0])  # DMI vector as given, not normalized


def test_spirit_tensor_dry_run(spirit_code):
    """Dry run with a full exchange tensor: check the couplings and two-site anisotropy tables"""
    inputs = prepare_test_inputs(os.path.join(TEST_DIR, 'input_files'))
    inputs['code'] = spirit_code
    inputs['metadata']['dry_run'] = True

    # J = 1.7, D = (0.3, -0.5, 0.8), K symmetric traceless (meV); Jtensor = J 1 + K + [D]_x^T
    jij, dmi = 1.7, np.array([0.3, -0.5, 0.8])
    kij = np.array([[-0.4, 0.05, -0.15], [0.05, 0.1, 0.25], [-0.15, 0.25, 0.3]])
    d_cross = np.array([[0, -dmi[2], dmi[1]], [dmi[2], 0, -dmi[0]], [-dmi[1], dmi[0], 0]])
    tensor = jij * np.eye(3) + kij + d_cross.T
    jij_data = ArrayData()
    jij_data.set_array('Jij_expanded', np.array([[0, 0, 1, 0, 0], [0, 0, 0, 1, 0]], dtype=float))
    jij_data.set_array('Jij_tensor', np.stack([tensor, 2 * tensor]))
    inputs['jij_data'] = jij_data

    _, node = run_get_node(CalculationFactory('spirit'), **inputs)
    folder = _dry_run_folder(node)
    with (folder / 'input.toml').open('rb') as _f:
        config = tomllib.load(_f)
    assert config['hamiltonian']['two_site_anisotropy'] == 'file://two_site_anisotropy.txt'

    couplings = _read_table(folder / 'couplings.txt')
    assert np.allclose(couplings['Jij'], [jij, 2 * jij])
    assert np.allclose(np.stack([couplings['Dijx'], couplings['Dijy'], couplings['Dijz']], axis=1),
                       [dmi, 2 * dmi])
    two_site = _read_table(folder / 'two_site_anisotropy.txt')
    assert list(two_site) == ['i', 'j', 'da', 'db', 'dc', 'Kijxx', 'Kijyy', 'Kijyz', 'Kijxz', 'Kijxy']
    for key, (i, j) in {'Kijxx': (0, 0), 'Kijyy': (1, 1), 'Kijyz': (1, 2), 'Kijxz': (0, 2), 'Kijxy': (0, 1)}.items():
        assert np.allclose(two_site[key], [kij[i, j], 2 * kij[i, j]])

    # a tensor array that does not match Jij_expanded is rejected
    bad = ArrayData()
    bad.set_array('Jij_expanded', np.zeros((2, 5)))
    bad.set_array('Jij_tensor', np.zeros((3, 3, 3)))
    with pytest.raises(ValueError):
        CalculationFactory('spirit').get_builder().jij_data = bad


def test_spirit_calc(spirit_code):
    """Test running a calculation
    this actually runs spirit and therefore needs
    to have spirit (develop, TOML input) installed in the python environment."""
    pytest.importorskip('spirit')

    # Prepare input parameters
    inputs = prepare_test_inputs(os.path.join(TEST_DIR, 'input_files'))
    inputs['code'] = spirit_code
    inputs['metadata']['options'] = {
        # 5 mins max runtime
        'max_wallclock_seconds': 300
    }

    result, node = run_get_node(CalculationFactory('spirit'), **inputs)
    print(result, node)
    print(node.exit_status, node.process_state)
    print(node.attributes)
    print(node.outputs.retrieved.list_object_names())
    print(inputs)
    assert node.is_finished_ok

    # check consistency of the output files
    check_outcome(result)


def test_spirit_calc_with_param(spirit_code):
    """Test running a calculation
    this actually runs spirit and therefore needs
    to have spirit installed in the python environment.

    This test runs a spirit calculation with an external field and a small temperature
    """
    pytest.importorskip('spirit')

    # Prepare input parameters
    inputs = prepare_test_inputs(os.path.join(TEST_DIR, 'input_files'))
    inputs['code'] = spirit_code
    inputs['metadata']['options'] = {
        # 5 mins max runtime
        'max_wallclock_seconds': 300
    }
    # prepare parameters
    parameters = Dict({
        'geometry': {'mu_s': 2.2},  # change spin moment to have the right size for Fe
        'hamiltonian': {
            # external field of 2 T in z direction
            'external_field': {'magnitude': 2.0, 'direction': [0.0, 0.0, 1.0]},
        },
        'method': {
            'llg': {
                'temperature': 10.0,  # 10 K temperature noise
                'n_iterations': 20000,  # limit the number of iterations
            }
        },
    })
    inputs['parameters'] = parameters

    # run options input dict
    inputs['run_options'] = Dict(dict={
        'simulation_method': 'LLG',
        'solver': 'Depondt',
    })

    # first a dry run
    inputs['metadata']['dry_run'] = True
    result = run(CalculationFactory('spirit'), **inputs)

    # then run the calculation
    inputs['metadata']['dry_run'] = False
    result, node = run_get_node(CalculationFactory('spirit'), **inputs)
    print(result)
    assert node.is_finished_ok

    # check consistency of the output files
    spins_final = check_outcome(result, threshold=0.10)
    mag_mean = np.mean(spins_final, axis=0)
    print(mag_mean)
    assert mag_mean[0] < 0.25
    assert mag_mean[1] < 0.25
    assert mag_mean[2] > 0.80


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
        #from pprint import pprint
        #pprint(txt)
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
    spins_initial = result['magnetization'].get_array('initial')
    var_initial = np.std(spins_initial, axis=0).max()
    print('std initial', var_initial)
    assert var_initial > 0.4

    spins_final = result['magnetization'].get_array('final')
    var_final = np.std(spins_final, axis=0).max()
    print('std final', var_final)
    assert var_final < threshold

    return spins_final
