========
Tutorial
========

This page contains a simple tutorial example for your code. The source code can be found under ``example_LLG.py`` in the examples folder.

What we want to achieve
+++++++++++++++++++++++

We want to compute a LLG simulation for the Fe bcc structure.

Step 1 - prepare parameters
---------------------------

The parameters for the simulation have to be given as *key*, *value* pairs inside an `AiiDA Dict <https://aiida.readthedocs.io/projects/aiida-core/en/latest/topics/data_types.html#core-data-types>`_.

::

	# prepare parameters
	parameters = Dict(
	    dict={
	        # temperature noise (in K)
	        'llg_temperature': '50',
	        # external field of 5 mT
	        'external_field_magnitude': '0.005',
	        # external field points in z direction
	        'external_field_normal': '0.0 0.0 1.0',
	        # change spin moment to have the right size for Fe
	        'mu_s': '2.2',
	        # limit the number of iterations
	        'llg_n_iterations': '2000'
	    })
	inputs['parameters'] = parameters

The **keys** of the parameters need to be written exactly as in the `Spirit input file <https://spirit-docs.readthedocs.io/en/latest/core/docs/Input.html>`_ and the **values** need to be of type ``string`` and also formatted as in the input file (check spacing in vectors).

The **keys** ``bravais lattice`` and ``interaction_pairs_file`` don't have to be given in the parameters *dictionary* as the structure and interaction pairs data will be passed using separate inputs.

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
For other cases, we will need to pass a valid `AiiDA ArrayData <https://aiida.readthedocs.io/projects/aiida-core/en/latest/topics/data_types.html#arraydata>`_ containing the interaction pairs. In the example below we use a ``numpy`` array with the data to create the **AiiDA ArrayData** input.
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

we may want to ouput some results. In order to do that, we need to access the folder where the calculation outputs are created. In this example we want to get the mean magnetization for each direction. For that, we access the output file containing the final configuration and using ``numpy.mean`` we calculate the mean magnetization.
::

	# output results
	ret = result['retrieved']
	with ret.open('spirit_Image-00_Spins-final.ovf') as _file:
	    spins_final = np.loadtxt(_file)
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
	    inputs = prepare_test_inputs(INPUT_DIR)

	    # add the spirit code to the inputs
	    inputs['code'] = spirit_code


	    # This is where you prepare the parameters

	    # This is where you set the structure

	    # This is where you create the jij inputs


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
