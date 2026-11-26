from geometry_msgs.msg import Twist
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim_msgs.msg import Pose


def command_for_pose(last_pose: Pose | None) -> Twist:
    command = Twist()
    if last_pose is not None:
        command.linear.x = 0.5
        command.angular.z = 0.3
    return command


class Patrol(Node):
    def __init__(self) -> None:
        super().__init__('patrol')
        self.last_pose: Pose | None = None
        self.command_publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.pose_subscription = self.create_subscription(
            Pose, '/turtle1/pose', self.pose_callback, 10,
        )
        self.command_timer = self.create_timer(0.1, self.timer_callback)

    def pose_callback(self, message: Pose) -> None:
        self.last_pose = message

    def timer_callback(self) -> None:
        self.command_publisher.publish(command_for_pose(self.last_pose))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Patrol()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
