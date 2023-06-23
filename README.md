[![Build Status](https://github.com/JuDFTteam/aiida-spirit/workflows/ci/badge.svg?branch=master)](https://github.com/JuDFTteam/aiida-spirit/actions)
[![Coverage Status](https://codecov.io/gh/JuDFTteam/aiida-spirit/branch/main/graph/badge.svg?token=F7ISM4558S)](https://codecov.io/gh/JuDFTteam/aiida-spirit)
[![Docs status](https://readthedocs.org/projects/aiida-spirit/badge)](http://aiida-spirit.readthedocs.io/)
[![PyPI version](https://badge.fury.io/py/aiida-spirit.svg)](https://badge.fury.io/py/aiida-spirit)
[![DOI](https://zenodo.org/badge/364820045.svg)](https://zenodo.org/badge/latestdoi/364820045)

# aiida-spirit

AiiDA plugin for the [spirit code](http://spirit-code.github.io/)


## Installation

```shell
pip install aiida-spirit # install aiida-spirit from pypi
verdi quicksetup  # better to set up a new profile
verdi plugin list aiida.calculations  # should now show your calclulation plugins
```


## Usage

Here goes a complete example of how to submit a test calculation using this plugin.

A quick demo of how to submit a calculation (the spirit python API needs to be installed for this to work: `pip install spirit`):
```shell
verdi daemon start     # make sure the daemon is running
cd examples
./example_LLG.py       # run test calculation
verdi process list -a  # check record of calculation
```

## Development

```shell
git clone https://github.com/JuDFTteam/aiida-spirit .
cd aiida-spirit
pip install -e .[pre-commit,testing]  # install extra dependencies
pre-commit install  # install pre-commit hooks
pytest -v  # discover and run all tests
```

Note that `pytest -v` will create a test database and profile which requires to find the `pg_ctl` command.
If `pg_ctl` is not found you need to nake sure that postgres is installed and then add the localtion of
`pg_ctl` to the `PATH`:
```
# add postgres path for pg_ctl to PATH
# this is an example for Postgres 9.6 installed on a mac
PATH="/Applications/Postgres.app/Contents/Versions/9.6/bin/:$PATH"
export PATH
```

## Citation

If you use AiiDA-Spirit please cite the method paper
 - P. Rüßmann, J. Ribas Sobreviela, M. Sallermann, M. Hoffmann, F. Rhiem, and S. Blügel, *The AiiDA-Spirit Plugin for Automated Spin-Dynamics Simulations and Multi-Scale Modeling Based on First-Principles Calculations*, Front. Mater. **9**, 825043 (2022). [doi: 10.3389/fmats.2022.825043](https://doi.org/10.3389/fmats.2022.825043),

 and the latest code release
 - P. Rüßmann, J. Ribas Sobreviela, M. Sallermann, M. Hoffmann, F. Rhiem, and S. Blügel. JuDFTteam/aiida-spirit. Zenodo. [doi: 10.5281/zenodo.8070770](https://doi.org/10.5281/zenodo.8070770).

## License

The AiiDA-Spirit code is under the [MIT license](LICENSE).

## Contact

p.ruessmann@fz-juelich.de
