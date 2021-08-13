# -*- coding: utf-8 -*-
""" Helper functions for automatically setting up computer & code.
Helper functions for setting up

 1. An AiiDA localhost computer
 2. A "spirit" code on localhost

"""
import tempfile
import shutil
import os
import numpy as np
from aiida.orm import Dict, StructureData, ArrayData, Computer, Code
from aiida.common.exceptions import NotExistent

LOCALHOST_NAME = 'localhost-test'

executables = {
    # the spirit executable is simply a python environment with the spirit package installed
    'spirit': 'python',
}


def prepare_test_inputs(input_dir):
    """Prepare the input parameters, structure and load the Jij's
    for a simple SpiritCalculation for bcc Fe,
    """
    # Prepare input parameters
    parameters = Dict(dict={})
    # example structure: bcc Fe
    structure = StructureData(cell=[[1.42002584, 1.42002584, 1.42002584],
                                    [1.42002584, -1.42002584, -1.42002584],
                                    [-1.42002584, 1.42002584, -1.42002584]])
    structure.append_atom(position=[0, 0, 0], symbols='Fe')
    # create jij couplings input from csv export
    jijs_expanded = np.load(os.path.join(input_dir, 'Jij_expanded.npy'))
    jij_data = ArrayData()
    jij_data.set_array('Jij_expanded', jijs_expanded)

    # set up calculation
    inputs = {
        'parameters': parameters,
        'jij_data': jij_data,
        'structure': structure,
        'metadata': {
            'description': 'Test job submission with the aiida_spirit plugin',
        },
    }

    return inputs


def get_path_to_executable(executable):
    """ Get path to local executable.
    :param executable: Name of executable in the $PATH variable
    :type executable: str
    :return: path to executable
    :rtype: str
    """
    path = shutil.which(executable)
    if path is None:
        raise ValueError(
            "'{}' executable not found in PATH.".format(executable))
    return path


def get_computer(name=LOCALHOST_NAME, workdir=None):
    """Get AiiDA computer.
    Loads computer 'name' from the database, if exists.
    Sets up local computer 'name', if it isn't found in the DB.

    :param name: Name of computer to load or set up.
    :param workdir: path to work directory
        Used only when creating a new computer.
    :return: The computer node
    :rtype: :py:class:`aiida.orm.Computer`
    """

    try:
        computer = Computer.objects.get(name=name)
    except NotExistent:
        if workdir is None:
            workdir = tempfile.mkdtemp()

        computer = Computer(
            name=name,
            description='localhost computer set up by aiida_diff tests',
            hostname=name,
            workdir=workdir,
            transport_type='local',
            scheduler_type='direct')
        computer.store()
        computer.set_minimum_job_poll_interval(0.)
        computer.configure()

    return computer


def get_code(entry_point, computer):
    """Get local code.
    Sets up code for given entry point on given computer.

    :param entry_point: Entry point of calculation plugin
    :param computer: (local) AiiDA computer
    :return: The code node
    :rtype: :py:class:`aiida.orm.Code`
    """

    try:
        executable = executables[entry_point]
    except KeyError:
        raise KeyError(
            "Entry point '{}' not recognized. Allowed values: {}".format(
                entry_point, list(executables.keys())))

    codes = Code.objects.find(filters={'label': executable})  # pylint: disable=no-member
    if codes:
        return codes[0]

    path = get_path_to_executable(executable)
    code = Code(
        input_plugin_name=entry_point,
        remote_computer_exec=[computer, path],
    )
    code.label = executable
    return code.store()
