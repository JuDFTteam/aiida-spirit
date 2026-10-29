# -*- coding: utf-8 -*-
"""pytest fixtures for simplified testing."""
import shutil
import pytest
pytest_plugins = ['aiida.tools.pytest_fixtures']


@pytest.fixture(scope='function', autouse=True)
def clear_database_auto(aiida_profile_clean):  # pylint: disable=unused-argument
    """Automatically clear database in between tests."""


@pytest.fixture(scope='function')
def spirit_code(aiida_code_installed):
    """Get a spirit code (the python interpreter, which runs the generated run_spirit.py)."""
    return aiida_code_installed(filepath_executable=shutil.which('python'),
                                default_calc_job_plugin='spirit')
