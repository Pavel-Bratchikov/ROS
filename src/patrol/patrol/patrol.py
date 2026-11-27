from dataclasses import replace

from geometry_msgs.msg import Twist
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim_msgs.msg import Pose

from patrol.parameters import DEFAULTS, PARAMETER_NAMES, MotionSettings, parameter_error


def command_for_pose(
    last_pose: Pose | None,
    linear_speed: float = DEFAULTS.linear_speed,
    turn_rate: float = DEFAULTS.turn_rate,
) -> Twist:
    command = Twist()
    if last_pose is not None:
        command.linear.x = linear_speed
        command.angular.z = turn_rate
    return command


class Patrol(Node):
    def __init__(self, **kwargs) -> None:
        super().__init__('patrol', **kwargs)
        try:
            values = {
                name: self.declare_parameter(name, getattr(DEFAULTS, name)).value
                for name in PARAMETER_NAMES
            }
            self.settings = MotionSettings(**values)
            error = parameter_error(self.settings)
            if error:
                raise ValueError(error)
        except Exception:
            self.destroy_node()
            raise
        self.last_pose: Pose | None = None
        self.command_publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.pose_subscription = self.create_subscription(
            Pose, 'turtle1/pose', self.pose_callback, 10,
        )
        self.command_timer = self.create_timer(1.0 / self.settings.publish_hz, self.timer_callback)
        self.add_on_set_parameters_callback(self.validate_update)
        self.add_post_set_parameters_callback(self.commit_update)

    def proposed_settings(self, parameters) -> MotionSettings:
        changes = {
            item.name: item.value
            for item in parameters
            if item.name in PARAMETER_NAMES
        }
        return replace(self.settings, **changes)

    def validate_update(self, parameters) -> SetParametersResult:
        error = parameter_error(self.proposed_settings(parameters))
        return SetParametersResult(successful=not error, reason=error)

    def commit_update(self, parameters) -> None:
        proposed = self.proposed_settings(parameters)
        if proposed.publish_hz == self.settings.publish_hz:
            self.settings = proposed
            return

        next_timer = self.create_timer(1.0 / proposed.publish_hz, self.timer_callback, autostart=False)
        self.command_timer.cancel()
        self.destroy_timer(self.command_timer)
        self.command_timer = next_timer
        self.settings = proposed
        next_timer.reset()

    def pose_callback(self, message: Pose) -> None:
        self.last_pose = message

    def timer_callback(self) -> None:
        command = command_for_pose(self.last_pose, self.settings.linear_speed, self.settings.turn_rate)
        self.command_publisher.publish(command)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = Patrol()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
