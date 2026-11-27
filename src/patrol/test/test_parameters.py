from dataclasses import replace

import pytest

from patrol.parameters import DEFAULTS, parameter_error


@pytest.mark.parametrize(('name', 'value'), [
    ('publish_hz', 10.0),
    ('publish_hz', 5.0),
    ('publish_hz', 1.0),
    ('publish_hz', 30.0),
    ('linear_speed', 0.0),
    ('linear_speed', 1.0),
    ('turn_rate', -1.0),
    ('turn_rate', 1.0),
])
def test_motion_parameter_accepts_in_range_values(name, value):
    assert not parameter_error(replace(DEFAULTS, **{name: value}))


@pytest.mark.parametrize(('name', 'value'), [
    ('publish_hz', 0.0),
    ('publish_hz', -1.0),
    ('publish_hz', 30.1),
    ('publish_hz', float('nan')),
    ('publish_hz', float('inf')),
    ('publish_hz', True),
    ('publish_hz', '5.0'),
    ('linear_speed', -0.1),
    ('linear_speed', 1.01),
    ('linear_speed', float('nan')),
    ('turn_rate', -1.1),
    ('turn_rate', 1.1),
    ('turn_rate', float('-inf')),
])
def test_motion_parameter_rejects_invalid_values(name, value):
    assert parameter_error(replace(DEFAULTS, **{name: value})).startswith(name)
