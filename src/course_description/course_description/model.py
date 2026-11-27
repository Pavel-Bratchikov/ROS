from math import isfinite

import xacro


DEFAULT_DIMENSIONS = {'wheelbase': 0.8, 'track': 0.62, 'wheel_radius': 0.12}


def _dimension(name, value):
    try:
        meters = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f'{name} must be a finite positive dimension in metres') from None
    if isinstance(value, bool) or not isfinite(meters) or meters <= 0:
        raise ValueError(f'{name} must be a finite positive dimension in metres')
    return str(meters)


def expand_model(
    path, *, wheelbase=DEFAULT_DIMENSIONS['wheelbase'], track=DEFAULT_DIMENSIONS['track'],
    wheel_radius=DEFAULT_DIMENSIONS['wheel_radius'],
):
    values = {'wheelbase': wheelbase, 'track': track, 'wheel_radius': wheel_radius}
    dimensions = {name: _dimension(name, value) for name, value in values.items()}
    return xacro.process_file(str(path), mappings=dimensions).documentElement.toxml()
