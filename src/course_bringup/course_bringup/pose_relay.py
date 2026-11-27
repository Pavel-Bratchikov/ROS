from rclpy.node import Node
from turtlesim_msgs.msg import Pose

from course_bringup.common import pose_qos, run_node


class PoseRelay(Node):
    def __init__(self, **kwargs) -> None:
        super().__init__('pose_relay', **kwargs)
        self.outbound = self.create_publisher(Pose, 'sensor_pose', pose_qos('best_effort'))
        self.inbound = self.create_subscription(Pose, 'pose', self.outbound.publish, 10)


def main(args=None) -> None:
    run_node(PoseRelay, args)
