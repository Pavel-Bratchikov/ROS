import pytest
from rclpy.qos import QoSCompatibility, qos_check_compatible

from course_bringup.common import pose_qos


@pytest.mark.parametrize(('offered', 'requested', 'compatible'), [
    ('reliable', 'reliable', True),
    ('reliable', 'best_effort', True),
    ('best_effort', 'best_effort', True),
    ('best_effort', 'reliable', False),
])
def test_reliability_matrix(offered, requested, compatible):
    result, _ = qos_check_compatible(pose_qos(offered), pose_qos(requested))
    expected = QoSCompatibility.OK if compatible else QoSCompatibility.ERROR
    assert result == expected


@pytest.mark.parametrize('value', ['unknown', '', 'BEST_EFFORT'])
def test_unknown_reliability_is_rejected(value):
    with pytest.raises(ValueError, match='reliability'):
        pose_qos(value)
