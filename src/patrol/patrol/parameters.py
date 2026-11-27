from dataclasses import dataclass, fields


@dataclass(frozen=True)
class MotionSettings:
    linear_speed: float = 0.5
    turn_rate: float = 0.3
    publish_hz: float = 10.0


DEFAULTS = MotionSettings()
PARAMETER_NAMES = tuple(field.name for field in fields(MotionSettings))
LIMITS = {
    'linear_speed': (0.0, 1.0),
    'turn_rate': (-1.0, 1.0),
    'publish_hz': (1.0, 30.0),
}


def parameter_error(settings: MotionSettings) -> str:
    for name, (minimum, maximum) in LIMITS.items():
        value = getattr(settings, name)
        if type(value) not in (int, float) or not minimum <= value <= maximum:
            return f'{name} needs a finite number in [{minimum}, {maximum}]'
    return ''
