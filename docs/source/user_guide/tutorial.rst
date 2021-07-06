========
Tutorial
========

This page contains a simple tutorial example for your code. The source code can be found under ``example_LLG.py`` in the examples folder.

Find the magnetic groud state with and LLG calculation
++++++++++++++++++++++++++++++++++++++++++++++++++++++

We want to compute the ground state magnetic structure of bcc Fe using an LLG calculation.

Step 1 - prepare parameters
---------------------------

The parameters for the simulation have to be given as *key*, *value* pairs inside an `AiiDA Dict <https://aiida.readthedocs.io/projects/aiida-core/en/latest/topics/data_types.html#core-data-types>`_. These set up the spirit calculation, define the Hamiltonian and allow to include external parameters like applying an external magnetic field. Information on what paramters can be set are listed on the `spirit documentation <https://spirit-docs.readthedocs.io/en/latest/core/docs/Input.html>`_. Note that the aiida-spirit plugin uses python booleans (`True/False`) for logical inputs and includes some type checking. Some parameters are set automatically by the plugin (e.g. the structure and coupling constants) and cannot be set in the input parameters.

::

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
	        'mu_s': 2.2,
	        # limit the number of iterations
	        'llg_n_iterations': 2000
	    })
	inputs['parameters'] = parameters


Step 2 - set structure
----------------------

For the case of the Fe bcc we don't need to input a structure as that's the structure set by default in ``helpers.py``.
If we wanted to use a different structure, we would have to give a valid `AiiDA StructureData <https://aiida.readthedocs.io/projects/aiida-core/en/latest/topics/data_types.html#structuredata>`_ as in the example below.
::

	# set structure
	structure = StructureData(cell=[[3.0, 0.0, 0.0],
	                                [0.0, 3.0, 0.0],
	                                [0.0, 0.0, 3.0]])
	structure.append_atom(position=[1.5, 1.5, 1.5], symbols='Li')

	inputs['structure'] = structure



Step 3 - create jij inputs
--------------------------

The interaction pairs are given to the spirit input file using a separate file. The jij inputs by default are also the ones corresponding to the Fe bcc, so in this example we don't need to pass them.
For other cases, we will need to pass a valid `AiiDA ArrayData <https://aiida.readthedocs.io/projects/aiida-core/en/latest/topics/data_types.html#arraydata>`_ containing the interaction pairs. In the example below we use a ``numpy`` array with the data to create the **AiiDA ArrayData** input. **The `jij_data` ArrayData needs to set the `Jij_expanded` array which is used in the spirit calculation! No other name is allowed.**
::

	# create jij inputs
	jijs_expanded = np.load(os.path.join(input_dir, 'Jij_expanded.npy'))
	jij_data = ArrayData()
	jij_data.set_array('Jij_expanded', jijs_expanded)

	inputs['jij_data'] = jij_data

Step 4 - output results
-----------------------

After running the calculation
::

	result = engine.run(CalculationFactory('spirit'), **inputs)

we may want to ouput some results. Spirit provides the output of the calculation in the output nodes `output_parameters` and `magentization` where the initial and final magnetization is stored for each spin in the simulation. We can use this information for the final configuration and using ``numpy.mean`` calculate the mean magnetization.
::

	# output results
        spins_final = result['magnetization'].get_array('final')
	mag_mean = np.mean(spins_final, axis=0)

	print(f'mean magnetization direction: {mag_mean}')

The final result
+++++++++++++++++++++++

The execution of the code generates the following messages in the terminal, which are the result of the two ``print`` commands.
::

	Computed result: {'remote_folder': <RemoteData: uuid: c0768576-733d-48ee-a247-f8d7da5a2a30 (pk: 450)>, 'retrieved': <FolderData: uuid: c62a7b97-903c-4e00-aaf1-e5f3db05f678 (pk: 451)>}
	mean magnetization direction: [ 0.74734316  0.63311166 -0.0463055 ]

This example can be used as a starting point to calculate LLG simulations for different structures and using different parameters. All is needed is to modify the inputs according to the system we want to simulate.

Code structure for running a LLG simulation
+++++++++++++++++++++++++++++++++++++++++++
A sample code structure for running a simulation could be the one presented below:
::

	#!/usr/bin/env python
	# -*- coding: utf-8 -*-
	# pylint: disable=duplicate-code

	from os import path
	import click
	import numpy as np
	from aiida import cmdline, engine
	from aiida.orm import Dict
	from aiida.plugins import CalculationFactory
	from aiida_spirit import helpers
	from aiida_spirit.helpers import prepare_test_inputs

	def test_run(spirit_code):
	    """Run a calculation on the localhost computer.

	    Uses test helpers to create AiiDA Code on the fly.
	    """
	    if not spirit_code:
	        # get code
	        computer = helpers.get_computer()
	        spirit_code = helpers.get_code(entry_point='spirit', computer=computer)

	    # use template input, prepared for a simple bcc Fe example
	    # this is where the structure and the jij's are set already
	    inputs = prepare_test_inputs(INPUT_DIR)

	    # add the spirit code to the inputs
	    inputs['code'] = spirit_code

	    # This is where you prepare the parameters
            parameters = Dict(
                dict={
                    'llg_temperature': 10.0,  # 10 K temperature noise
                    'external_field_magnitude': 2.0,  # external field of 2 T
                    'external_field_normal': [0.0, 0.0, 1.0],  # external field points in z direction
                    'mu_s': 2.2,  # change spin moment to have the right size for Fe
                    'llg_n_iterations': 20000  # limit the number of iterations
                })
            inputs['parameters'] = parameters

	    # This is where you prepare control the run modes of spirit (here LLG)
            inputs['run_options'] = Dict(dict={
                'simulation_method': 'LLG',
                'solver': 'Depondt',
            })

	    # Note: in order to submit your calculation to the aiida daemon, do:
	    # from aiida.engine import submit
	    # future = submit(CalculationFactory('spirit'), **inputs)
	    result = engine.run(CalculationFactory('spirit'), **inputs)

	    print(f'Computed result: {result}')

	    # This is where you can output your desired results


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

This code uses the default input values given by the module ``aiida\_spirit.helpers``.

To use other input values it is needed to define them and add them in the ``inputs`` dictionary using the keys: ``parameters``, ``jij_data``, ``structure``.
