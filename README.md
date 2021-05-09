[![Build Status](https://github.com/JuDFTteam/aiida-spirit/workflows/ci/badge.svg?branch=master)](https://github.com/JuDFTteam/aiida-spirit/actions)
[![Coverage Status](https://coveralls.io/repos/github/JuDFTteam/aiida-spirit/badge.svg?branch=master)](https://coveralls.io/github/JuDFTteam/aiida-spirit?branch=master)
[![Docs status](https://readthedocs.org/projects/aiida-spirit/badge)](http://aiida-spirit.readthedocs.io/)
[![PyPI version](https://badge.fury.io/py/aiida-spirit.svg)](https://badge.fury.io/py/aiida-spirit)

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

A quick demo of how to submit a calculation:
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

## License

MIT

## Contact

p.ruessmann@fz-juelich.de
