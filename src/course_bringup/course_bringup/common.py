import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.qos import DurabilityPolicy, HistoryPolicy, LivelinessPolicy, QoSProfile, ReliabilityPolicy


RELIABILITY = {
    policy.name.lower(): policy
    for policy in (ReliabilityPolicy.BEST_EFFORT, ReliabilityPolicy.RELIABLE)
}


def pose_qos(name: str) -> QoSProfile:
    policy = RELIABILITY.get(name)
    if policy is None:
        raise ValueError(f'Invalid reliability {name!r}; use reliable or best_effort')
    return QoSProfile(
        depth=10,
        history=HistoryPolicy.KEEP_LAST,
        durability=DurabilityPolicy.VOLATILE,
        liveliness=LivelinessPolicy.AUTOMATIC,
        reliability=policy,
    )


def run_node(node_type, args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = node_type()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
