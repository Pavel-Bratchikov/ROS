from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, GroupAction, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():
    namespace, record, bag_dir, reliability = (
        LaunchConfiguration(argument)
        for argument in ('namespace', 'record', 'bag_dir', 'subscriber_reliability')
    )
    sensor_topic = PathJoinSubstitution(['/', namespace, 'sensor_pose'])
    system = GroupAction([
        PushRosNamespace(namespace),
        Node(
            package='patrol', executable='patrol', output='screen',
            remappings=[('turtle1/pose', '/turtle1/pose'), ('cmd_vel', '/turtle1/cmd_vel')],
        ),
        Node(
            package='course_bringup', executable='pose_relay', output='screen',
            remappings=[('pose', '/turtle1/pose')],
        ),
        Node(
            package='course_bringup', executable='pose_subscriber', output='screen',
            parameters=[{'reliability': reliability}],
        ),
    ])
    recorder = ExecuteProcess(
        cmd=[
            'ros2', 'bag', 'record', '-s', 'mcap', '-o', bag_dir,
            '--topics', sensor_topic, '--disable-keyboard-controls',
        ],
        condition=IfCondition(record),
        output='screen',
    )
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='robot_a'),
        DeclareLaunchArgument('record', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('bag_dir', default_value='pr05-bag'),
        DeclareLaunchArgument(
            'subscriber_reliability', default_value='best_effort',
            choices=['reliable', 'best_effort'],
        ),
        LogInfo(msg=['Namespace: ', namespace, ', subscriber: ', reliability, ', record: ', record]),
        Node(package='turtlesim', executable='turtlesim_node', namespace='/', output='screen'),
        system,
        recorder,
    ])
