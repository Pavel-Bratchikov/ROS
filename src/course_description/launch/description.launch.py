from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from course_description.model import DEFAULT_DIMENSIONS, expand_model


def _publisher(context):
    dimensions = {key: LaunchConfiguration(key).perform(context) for key in DEFAULT_DIMENSIONS}
    model = LaunchConfiguration('model').perform(context)
    description = expand_model(model, **dimensions)
    return [Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': ParameterValue(description, value_type=str),
            'use_sim_time': False,
        }],
    )]


def generate_launch_description():
    share = Path(get_package_share_directory('course_description'))
    view = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', str(share / 'rviz/vehicle.rviz'), '--display-title-format', 'PR06-RViz'],
        output='screen',
        condition=IfCondition(LaunchConfiguration('rviz')),
    )
    return LaunchDescription([
        DeclareLaunchArgument('model', default_value=str(share / 'urdf/vehicle.urdf.xacro')),
        *(DeclareLaunchArgument(name, default_value=str(value)) for name, value in DEFAULT_DIMENSIONS.items()),
        DeclareLaunchArgument('rviz', default_value='true', choices=['true', 'false']),
        OpaqueFunction(function=_publisher),
        view,
    ])
