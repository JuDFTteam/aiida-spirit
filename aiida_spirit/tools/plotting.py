# -*- coding: utf-8 -*-
"""
Plotting tools for aiida-spirit.
"""

import numpy as np
from ._vfr import setup, update
from .get_from_remote import list_remote_files, get_file_content_from_remote


def init_spinview(vfr_frame_id='', height_px=600, width_percent=100):
    """
    Initialize the vfrendering HTML object.

    Needs to be called before the show_spins function can set the spins
    :param vfr_frame_id: a string that controls if multiple windows
    should be openend. Use the same string in show_spins to update this.
    :param height_px: height of the window in pixels
    :param width_percent: window width in percent of the current width size
    """

    # initialize vfrendering HTML object
    view = setup(vfr_frame_id, height_px, width_percent)

    return view


def _plot_spins_vfr(  # pylint: disable=too-many-arguments
        pos_cell,
        n_basis_cells,
        cell,
        spin_directions,
        scale_spins=1.0,
        vfr_frame_id=''):
    """
    Construct positions and directions array and update the vfrendering spin view
    """

    # set positions and direciton of the spins
    positions = []
    for iz in range(n_basis_cells[2]):
        for iy in range(n_basis_cells[1]):
            for ix in range(n_basis_cells[0]):
                for p in pos_cell:
                    # set position
                    positions.append(p + ix * cell[0] + iy * cell[1] +
                                     iz * cell[2])
    # make flattened arrays
    positions = np.array(positions).reshape(-1, 3)
    directions = np.array(spin_directions).reshape(-1, 3)

    # normalize directions
    norm = np.linalg.norm(directions, axis=1)
    norm[norm == 0] = 1  # prevent divide by zero
    for ixyz in range(3):
        directions[:, ixyz] /= norm

    # scaling factor for the directions
    directions *= scale_spins

    # put mid-point in the center to have origin for rotation in the center
    positions -= np.sum(positions, axis=0) / len(positions)

    # update the vfrendering view with the new positions and directions
    # we use rectilinear=False here to be able to work with any structure
    try:
        update(positions,
               directions,
               rectilinear=False,
               vfr_frame_id=vfr_frame_id)
    except KeyError:
        print(
            f'\nERROR: Did not find the vfr_frame_id "{vfr_frame_id}". Did you specify the same as in init_spinview?'
        )


def show_spins(  # pylint: disable=inconsistent-return-statements,too-many-arguments,too-many-locals, too-many-branches
        spirit_calc,
        show_final_structure=True,
        scale_spins=1.0,
        scale_lattice=1.0,
        list_spin_files_on_remote=False,
        use_remote_spins_id=None,
        mask=None,
        vfr_frame_id=''):
    """
    Update the vfrendering spin view plot with the final or initial spin structure.

    Needs to have the init_spinview() function called to initialize a window where the plot is shown.

    :param spirit_calc: the SpiritCalculation which is supposed to be visualized
    :param show_final_structure: boolean that tells us if the initial or final structure of the spins should be displayed
    :param scale_spins: a scaling factor that can be used to scale the size of the arrows
    :param scale_lattice: a scaling factor that can be used to scale the spacing of the atoms
    :param list_spin_files_on_remote: print a list of the available spin image files on the remote folder.
    :param use_remote_spins_id: show neither final nor initial spin structure but show the structure of
        a certain checkpoint (see list_spin_files_on_remote=True output for available checkpoints).
    :param mask: mask which can be used to hide or rescale spins (mask is multiplied to the spins,
                 i.e. mask==0 hides a spin, mask>1 enhaces its size).
    :param vfr_frame_id: if given this allows to control into which spinview frame the spins are shown.
        Should be the same as in the init_spinview. This is not fully implemented yet and does not work in this version.
    """

    # get number of unit cells used in spirit calculation
    # we use the default value from the template file if nothing is given
    n_basis_cells = spirit_calc.inputs.parameters.get_dict().get(
        'n_basis_cells', [5, 5, 5])

    # get structure information from spirit input structure
    struc = spirit_calc.inputs.structure
    cell = np.array(struc.cell)
    pos_cell = np.array([i.position for i in struc.sites])
    # rescale lattice
    cell *= scale_lattice
    pos_cell *= scale_lattice

    # get initial or final spin directions
    if 'magnetization' not in spirit_calc.outputs:
        if not spirit_calc.is_finished_ok and spirit_calc.is_terminated:
            raise ValueError('SpiritCalculation did not finish ok.')
        print(
            'SpiritCalculation does not have magnetization output node. Cannot plot anything'
        )
        return

    m = spirit_calc.outputs.magnetization
    minit = m.get_array('initial')
    mfinal = m.get_array('final')
    if show_final_structure:
        m = mfinal
    else:
        m = minit

    # apply a scaling mask
    if mask is not None:
        if m[:, 0].shape != mask.shape:
            raise ValueError(
                f'mask array is not of the right shape. Got {mask.shape} but expected {m[:,0].shape}.'
            )
        for ixyz in range(3):
            m[:, ixyz] *= mask

    if 'defects' in spirit_calc.inputs:
        if 'atom_types' in spirit_calc.outputs:
            # hide defects
            atom_types = spirit_calc.outputs.atom_types.get_array('atom_types')
            m[atom_types < 0] = 0
        else:
            # fallback if atom_types are not there
            # these are the positions where the initial and final spins are the same (hide those if we have defects)
            m[(minit == mfinal).all(axis=1)] = 0

    # print a list of files that are still on the remote and which can be plotted
    if list_spin_files_on_remote or use_remote_spins_id is not None:
        print('getting list of spirit images on remote')
        remote_files = list_remote_files(spirit_calc)
        spin_images = [
            i for i in remote_files if 'spirit_Image-00_Spins_' in i
        ]
        #all_image_ids = np.sort([int(i.split('_')[-1].split('.')[0]) for i in spin_images])
        if list_spin_files_on_remote:
            print(
                f'Found {len(spin_images)} spin checkpoints in the remote folder.'
            )
            return spin_images

    # istead of using the initial or final spins we show a certain checkpoint
    if use_remote_spins_id is not None:
        print(
            'download spin configuration from remote (this may take some time)'
        )
        #image_id = all_image_ids[use_remote_spins_id]
        fname = spin_images[
            use_remote_spins_id]  #'spirit_Image-00_Spins_'+str(image_id)+'.ovf'
        txt = get_file_content_from_remote(spirit_calc, fname)
        m = np.loadtxt(txt)
        print(f'loaded spin configuration from {fname}')

    # consistency check for magnetization and positions
    if np.prod(m.shape) != np.prod(n_basis_cells) * np.prod(pos_cell.shape):
        raise ValueError(
            'Shape of the magnetization directions and the (expanded) positions does not match.'
        )

    # now update the vfrendering plot
    # this assumes that the init_spinview() has been called before
    _plot_spins_vfr(pos_cell,
                    n_basis_cells,
                    cell,
                    m,
                    scale_spins,
                    vfr_frame_id=vfr_frame_id)
