import time

import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.serialization import serialize_message
from turtlesim_msgs.msg import Pose

from course_bringup.pose_relay import PoseRelay
from course_bringup.pose_subscriber import PoseSubscriber


@pytest.fixture
def context():
    context = Context()
    rclpy.init(context=context)
    yield context
    context.try_shutdown()


def test_remapped_relay_matches_only_best_effort(context):
    producer = Node('source', context=context)
    relay = PoseRelay(
        context=context, namespace='/test_robot', cli_args=['--ros-args', '-r', 'pose:=/test_pose'],
    )
    observers = {
        name: PoseSubscriber(
            context=context, namespace='/test_robot',
            cli_args=['--ros-args', '-r', f'__node:={name}_observer'],
            parameter_overrides=[Parameter('reliability', value=name)],
        )
        for name in ('best_effort', 'reliable')
    }
    nodes = [producer, relay, *observers.values()]
    executor = SingleThreadedExecutor(context=context)
    try:
        for node in nodes:
            executor.add_node(node)
        assert relay.inbound.topic_name == '/test_pose'
        assert relay.outbound.topic_name == '/test_robot/sensor_pose'
        assert {node.subscription.topic_name for node in observers.values()} == {'/test_robot/sensor_pose'}
        publisher = producer.create_publisher(Pose, '/test_pose', 10)
        pose = Pose(x=3.5, y=2.25, theta=-0.25, linear_velocity=0.5, angular_velocity=0.125)
        producer.create_timer(0.02, lambda: publisher.publish(pose))
        compatible = observers['best_effort']
        end = time.monotonic() + 7
        while compatible.received_count < 10 and time.monotonic() < end:
            executor.spin_once(timeout_sec=0.1)
        assert compatible.received_count >= 10
        assert serialize_message(compatible.last_pose) == serialize_message(pose)
        assert observers['reliable'].received_count == 0
        assert observers['reliable'].last_pose is None
    finally:
        executor.shutdown()
        for node in reversed(nodes):
            node.destroy_node()


def test_runtime_reliability_cannot_change(context):
    node = PoseSubscriber(context=context)
    try:
        change = node.set_parameters_atomically([Parameter('reliability', value='reliable')])
        assert not change.successful
        assert node.get_parameter('reliability').value == 'best_effort'
    finally:
        node.destroy_node()


def test_startup_rejects_invalid_reliability(context):
    with pytest.raises(ValueError, match='reliability'):
        PoseSubscriber(context=context, parameter_overrides=[Parameter('reliability', value='invalid')])
