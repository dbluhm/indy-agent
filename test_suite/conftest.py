""" Pytest behavior customizations.
"""

import os
import pytest
from config import Config

def pytest_addoption(parser):
    """ Load in config path. """
    parser.addoption(
        "--sc",
        "--suite-config",
        dest='suite_config',
        action="store",
        metavar="SUITE_CONFIG",
        help="Load suite configuration from SUITE_CONFIG",
    )
    parser.addoption(
        "-S",
        "--select",
        dest='select',
        action='store',
        metavar='SELECT_REGEX',
        help='Run tests matching SELECT_REGEX. Overrides tests selected in configuration.'
    )

def pytest_configure(config):
    """ Load Test Suite Configuration. """
    dirname = os.path.dirname(__file__)
    config_path = config.getoption('suite_config')
    config_path = 'config.toml' if not config_path else config_path
    config_path = os.path.join(dirname, config_path)
    print('\nLoading Agent Test Suite configuration from file: {}\n'.format(config_path))

    config.suite_config = Config.from_file(config_path)

    #parser = Config.get_arg_parser()
    #(args, _) = parser.parse_known_args()
    #if args:
        #config.suite_config.update(vars(args))

    # register an additional marker
    config.addinivalue_line(
        "markers", "features(name[, name, ...]): Define what features the test belongs to."
    )

def pytest_runtest_setup(item):
    pass

def pytest_collection_modifyitems(session, config, items):
    def feature_filter(item):
        feature_names = [mark.args for mark in item.iter_markers(name="features")]
        feature_names = [item for sublist in feature_names for item in sublist]
        if feature_names:
            for selected_test in item.config.suite_config.tests:
                if selected_test in feature_names:
                    item.selected_feature = selected_test
                    return True

        return False

    items[:] = list(filter(feature_filter, items))
