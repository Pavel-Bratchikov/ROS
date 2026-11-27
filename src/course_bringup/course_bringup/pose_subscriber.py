from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from turtlesim_msgs.msg import Pose

from course_bringup.common import pose_qos, run_node


class PoseSubscriber(Node):
    def __init__(self, **kwargs) -> None:
        super().__init__('pose_subscriber', **kwargs)
        try:
            self.reliability = self.declare_parameter(
                'reliability', 'best_effort', ParameterDescriptor(read_only=True),
            ).value
            profile = pose_qos(self.reliability)
        except Exception:
            self.destroy_node()
            raise
        self.last_pose: Pose | None = None
        self.received_count = 0
        self.subscription = self.create_subscription(Pose, 'sensor_pose', self.receive, profile)
        self.timer = self.create_timer(1.0, self.log_delivery)

    def receive(self, pose: Pose) -> None:
        self.last_pose = pose
        self.received_count += 1

    def log_delivery(self) -> None:
        self.get_logger().info(f'reliability={self.reliability} received={self.received_count}')


def main(args=None) -> None:
    run_node(PoseSubscriber, args)
