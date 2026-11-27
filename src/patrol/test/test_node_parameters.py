import pytest
import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.context import Context
from rclpy.parameter import Parameter

from patrol.parameters import MotionSettings
from patrol.patrol import Patrol


@pytest.fixture
def context():
    context = Context()
    rclpy.init(context=context)
    yield context
    context.try_shutdown()


@pytest.fixture
def node(context):
    patrol = Patrol(context=context)
    yield patrol
    patrol.destroy_node()


def set_motion(node, **values):
    return node.set_parameters_atomically([
        Parameter(name, value=value) for name, value in values.items()
    ])


def test_rate_change_replaces_the_timer(node, monkeypatch):
    original = node.command_timer
    original_cancel = original.cancel
    cancellations = []

    def cancel():
        cancellations.append(original)
        original_cancel()

    monkeypatch.setattr(original, 'cancel', cancel)
    assert original.timer_period_ns == 100_000_000
    assert set_motion(node, publish_hz=5.0).successful
    assert cancellations == [original]
    assert node.get_parameter('publish_hz').value == node.settings.publish_hz == 5.0
    assert node.command_timer is not original
    assert node.command_timer.timer_period_ns == 200_000_000
    assert list(node.timers) == [node.command_timer]
    assert not node.command_timer.is_canceled()


@pytest.mark.parametrize('value', [0.0, -1.0, float('nan'), float('inf'), 31.0])
def test_rejected_frequency_preserves_timer(node, value):
    assert set_motion(node, publish_hz=5.0).successful
    timer = node.command_timer
    result = set_motion(node, publish_hz=value)

    assert not result.successful
    assert result.reason.startswith('publish_hz')
    assert node.get_parameter('publish_hz').value == node.settings.publish_hz == 5.0
    assert list(node.timers) == [timer]
    assert timer.timer_period_ns == 200_000_000
    assert not timer.is_canceled()


def test_speed_update_keeps_existing_timer(node):
    timer = node.command_timer

    assert set_motion(node, linear_speed=0.8, turn_rate=-0.5).successful
    assert node.settings == MotionSettings(0.8, -0.5, 10.0)
    assert list(node.timers) == [timer]


def test_invalid_batch_has_no_partial_update(node):
    timer = node.command_timer

    assert not set_motion(node, linear_speed=0.8, publish_hz=0.0).successful
    assert node.settings == MotionSettings()
    assert node.get_parameter('linear_speed').value == 0.5
    assert node.get_parameter('publish_hz').value == 10.0
    assert list(node.timers) == [timer]
    assert not timer.is_canceled()


def test_another_validator_can_veto_without_replacing_timer(node):
    def reject(_):
        return SetParametersResult(successful=False, reason='veto')

    node.remove_on_set_parameters_callback(node.validate_update)
    node.add_on_set_parameters_callback(reject)
    node.add_on_set_parameters_callback(node.validate_update)
    timer = node.command_timer

    assert set_motion(node, publish_hz=5.0).reason == 'veto'
    assert node.settings == MotionSettings()
    assert node.get_parameter('publish_hz').value == 10.0
    assert list(node.timers) == [timer]
    assert not timer.is_canceled()


@pytest.mark.parametrize(('name', 'value'), [
    ('linear_speed', -0.1), ('turn_rate', 1.1), ('publish_hz', 0.0),
])
def test_invalid_startup_override_is_rejected(context, name, value):
    with pytest.raises(ValueError, match=name):
        Patrol(context=context, parameter_overrides=[Parameter(name, value=value)])


def test_valid_startup_override_sets_initial_timer(context):
    overrides = [Parameter('linear_speed', value=0.8), Parameter('publish_hz', value=5.0)]
    patrol = Patrol(context=context, parameter_overrides=overrides)
    try:
        assert patrol.settings == MotionSettings(0.8, 0.3, 5.0)
        assert patrol.command_timer.timer_period_ns == 200_000_000
        assert list(patrol.timers) == [patrol.command_timer]
    finally:
        patrol.destroy_node()
