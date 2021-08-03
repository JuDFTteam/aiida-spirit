# -*- coding: utf-8 -*-
"""
Plotting tools for aiida-spirit.
"""

import numpy as np
from ._vfr import setup, update


def init_spinview():
    """
    Initialize the vfrendering HTML object.

    Needs to be called before the show_spins function can set the spins
    """

    # initialize vfrendering HTML object
    view = setup()

    return view


def _plot_spins_vfr(pos_cell,
                    n_basis_cells,
                    cell,
                    spin_directions,
                    scale_spins=1.0):
    """
    Construct positions and directions array and update the vfrendering spin view
    """

    # set positions and direciton of the spins
    positions = []
    for iz in range(n_basis_cells[0]):
        for iy in range(n_basis_cells[1]):
            for ix in range(n_basis_cells[2]):
                for p in pos_cell:
                    # set position
                    positions.append(p + ix * cell[0] + iy * cell[1] +
                                     iz * cell[2])
    # make flattened array
    positions = np.array(positions).reshape(-1, 3)

    # normalize directions
    directions = np.array(spin_directions).reshape(-1, 3)
    for ixyz in range(len(directions)):
        directions[ixyz, :] /= np.linalg.norm(directions[ixyz, :])

    # scaling factor for the directions
    directions *= scale_spins

    # put mid-point in the center to have origin for rotation in the center
    positions -= np.sum(positions, axis=0) / len(positions)

    # update the vfrendering view with the new positions and directions
    # we use rectilinear=False here to be able to work with any structure
    update(positions, directions, rectilinear=False)


def show_spins(spirit_calc, show_final_structure=True, scale_spins=1.0):
    """
    Update the vfrendering spin view plot with the final or initial spin structure.

    Needs to have the init_spinview() function called to initialize a window where the plot is shown.

    :param spirit_calc: the SpiritCalculation which is supposed to be visualized
    :param show_final_structure: boolean that tells us if the initial or final structure of the spins should be displayed
    :param scale_spins: a scaling factor that can be used to scale the size of the arrows
    """

    # get number of unit cells used in spirit calculation
    # we use the default value from the template file if nothing is given
    n_basis_cells = spirit_calc.inputs.parameters.get_dict().get(
        'n_basis_cells', [5, 5, 5])

    # get structure information from spirit input structure
    struc = spirit_calc.inputs.structure
    cell = np.array(struc.cell)
    pos_cell = np.array([i.position for i in struc.sites])

    # get initial or final spin directions
    m = spirit_calc.outputs.magnetization
    if show_final_structure:
        m = m.get_array('final')
    else:
        m = m.get_array('initial')

    # consistency check for magnetization and positions
    if np.prod(m.shape) != np.prod(n_basis_cells) * np.prod(pos_cell.shape):
        raise ValueError(
            'Shape of the magnetization directions and the (expanded) positions does not match.'
        )

    # now update the vfrendering plot
    # this assumes that the init_spinview() has been called before
    _plot_spins_vfr(pos_cell, n_basis_cells, cell, m, scale_spins)
