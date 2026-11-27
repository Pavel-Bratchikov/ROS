from geometry_msgs.msg import Twist
from patrol.patrol import command_for_pose
from turtlesim_msgs.msg import Pose


def test_command_is_zero_before_first_pose():
    assert command_for_pose(None) == Twist()


def test_command_moves_after_receiving_pose():
    expected = Twist()
    expected.linear.x = 0.5
    expected.angular.z = 0.3

    pose = Pose(x=5.5, y=5.5, theta=0.2)

    assert command_for_pose(pose) == expected


def test_command_uses_custom_speed_and_turn_rate():
    expected = Twist()
    expected.linear.x = 0.8
    expected.angular.z = -0.5

    assert command_for_pose(Pose(), 0.8, -0.5) == expected


def test_custom_values_still_require_pose():
    assert command_for_pose(None, 0.8, -0.5) == Twist()
