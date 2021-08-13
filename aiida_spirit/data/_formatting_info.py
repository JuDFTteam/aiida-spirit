# -*- coding: utf-8 -*-
"""
Things for type and consistency checking of spirit input parameters
"""

# list of keys which are only set by the plugin and are forbitted to be modified by the user
_forbidden_keys = [
    'output_file_tag',
    'log_output_folder',
    'llg_output_folder',
    'mc_output_folder',
    'gneb_output_folder',
    'mmf_output_folder',
    'ema_output_folder',
    'hamiltonian',
    'interaction_pairs_file',
    'lattice_constant',
    'bravais_lattice',
    'mc_max_walltime',
    'llg_max_walltime',
    'gneb_max_walltime',
    'mmf_max_walltime',
    'ema_max_walltime',
]

# hard coded list of keywords that expect a single boolean value
_single_bools = [
    'save_input_initial',
    'save_input_final',
    'save_positions_initial',
    'save_positions_final',
    'save_neighbours_initial',
    'save_neighbours_final',
    'ddi_pb_zero_padding',
    'log_to_console',
    'log_to_file',
    'mc_output_any',
    'mc_output_initial',
    'mc_output_final',
    'mc_output_energy_step',
    'mc_output_energy_archive',
    'mc_output_energy_spin_resolved',
    'mc_output_energy_divide_by_nspins',
    'mc_output_energy_add_readability_lines',
    'mc_output_configuration_step',
    'mc_output_configuration_archive',
    'llg_renorm',
    'llg_stt_use_gradient',
    'llg_output_any',
    'llg_output_initial',
    'llg_output_final',
    'llg_output_energy_step',
    'llg_output_energy_archive',
    'llg_output_energy_spin_resolved',
    'llg_output_energy_divide_by_nspins',
    'llg_output_energy_add_readability_lines',
    'llg_output_configuration_step',
    'llg_output_configuration_archive',
    'gneb_renorm',
    'gneb_output_any',
    'gneb_output_initial',
    'gneb_output_final',
    'gneb_output_energies_step',
    'gneb_output_energies_interpolated',
    'gneb_output_energies_divide_by_nspins',
    'gneb_output_energies_add_readability_lines',
    'gneb_output_chain_step',
    'mmf_output_any',
    'mmf_output_initial',
    'mmf_output_final',
    'mmf_output_energy_step',
    'mmf_output_energy_archive',
    'mmf_output_energy_divide_by_nspins',
    'mmf_output_energy_add_readability_lines',
    'mmf_output_configuration_step',
    'mmf_output_configuration_archive',
    'ema_output_any',
    'ema_output_initial',
    'ema_output_final',
    'ema_output_energy_step',
    'ema_output_energy_archive',
    'ema_output_energy_divide_by_nspins',
    'ema_output_energy_spin_resolved',
    'ema_output_energy_add_readability_lines',
    'ema_output_configuration_step',
    'ema_output_configuration_archive',
]

# keys for which values should be arrays/lists of booleans, together with the expected length
_array_bools = {'boundary_conditions': 3}

# keys for which values should be integers, together with the expected value range (None if not specified)
_single_ints = {
    'log_console_level': [0, 6],
    'log_file_level': [0, 6],
    'mc_seed': [None, None],
    'mc_n_iterations': [None, None],
    'mc_n_iterations_log': [None, None],
    'llg_seed': [None, None],
    'llg_n_iterations': [None, None],
    'llg_n_iterations_log': [None, None],
    'gneb_n_energy_interpolations': [None, None],
    'gneb_n_iterations': [None, None],
    'gneb_n_iterations_log': [None, None],
    'gneb_output_chain_filetype': [None, None],
    'mmf_n_iterations': [None, None],
    'mmf_n_iterations_log': [None, None],
    'mmf_n_modes': [None, None],
    'mmf_n_mode_follow': [None, None],
    'ema_n_iterations': [None, None],
    'ema_n_iterations_log': [None, None],
    'ema_n_modes': [None, None],
    'ema_n_mode_follow': [None, None],
    'mc_output_configuration_filetype': [None, None],
    'llg_output_configuration_filetype': [None, None],
    'mmf_output_configuration_filetype': [None, None],
    'ema_output_configuration_filetype': [None, None],
}

# keys for which values should be arrays/lists of integers, together with the expected value range (None if not specified)
_array_ints = {
    'ddi_n_periodic_images': [3, None, None],
    'n_basis_cells': [3, None, None],
}

# values which are floats
_single_floats = {
    'external_field_magnitude': [None, None],
    'anisotropy_magnitude': [None, None],
    'ddi_radius': [None, None],
    'mc_temperature': [None, None],
    'mc_acceptance_ratio': [None, None],
    'llg_temperature': [None, None],
    'llg_temperature_gradient_inclination': [None, None],
    'llg_damping': [None, None],
    'llg_beta': [None, None],
    'llg_dt': [None, None],
    'llg_stt_magnitude': [None, None],
    'llg_force_convergence': [None, None],
    'gneb_spring_constant': [None, None],
    'gneb_force_convergence': [None, None],
    'mmf_force_convergence': [None, None],
    'ema_frequency': [None, None],
    'ema_amplitude': [None, None],
}

# values which are arrays of floats
# last entry decides if all values are put in new lines
_array_floats = {
    'external_field_normal': [3, None, None],
    'anisotropy_normal': [3, None, None],
    'llg_temperature_gradient_direction': [3, None, None],
    'llg_stt_polarisation_normal': [3, None, None],
    'mu_s': [None, 0, None],
}

# values which are strings, together with a list of allowed values
_single_strings = {
    'ddi_method': ['fft', 'fmm', 'cutoff', 'none'],
}
