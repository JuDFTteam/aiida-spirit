# Changelog

## v0.3.0 (unreleased)

Needs a Spirit version that reads the TOML input (Spirit `develop`, tested with `b3b94c2a`),
aiida-core >= 2.6 and Python >= 3.11.

### Breaking
- The plugin writes Spirit's TOML input (`input.toml`) instead of the legacy `input_created.cfg`.
  The `parameters` input holds nested keys of the TOML input
  (e.g. `{'method': {'llg': {'n_iterations': 1000}}}`) and is merged over
  `aiida_spirit/data/input_defaults.toml`; the flat keys of the legacy input are rejected.

### Added
- Full exchange tensor input: the optional array `Jij_tensor` (shape `(n, 3, 3)`) of `jij_data` is
  split into the isotropic exchange, the DMI vector and the two-site anisotropy (written to
  `two_site_anisotropy.txt`). The energy convention (per listed bond) is in the `jij_data` help text.
- Validators for `parameters` (plugin-owned keys, non-TOML values) and `jij_data` (array shapes).

### Fixed
- Monte Carlo: the thermalisation iterations were set but never run, so every temperature was
  sampled straight from the ordered start.
- Monte Carlo: start with the Metropolis algorithm passed explicitly; update the energy before reading it.
- `solver='rk4'` selected the SIB solver.
- `ERROR_SPIRIT_CODE_INCOMPATIBLE` could never be returned ("Pinning is not enabled" contains "enabled").
- DMI rows with `D = 0` were written as NaN; the DMI vector is now passed as a vector.
- Energy files with readability lines, and stdout lines garbled by interleaved prints, no longer break the parser.
- aiida-core 2: `withmpi` may be unset; the `parameters` input is optional.
- The initial state is written in OVF format.
