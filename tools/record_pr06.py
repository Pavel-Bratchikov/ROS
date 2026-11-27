import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import yaml


MOVABLE_JOINTS = (
    'front_left_steering_joint', 'front_right_steering_joint',
    'front_left_wheel_joint', 'front_right_wheel_joint',
    'rear_left_wheel_joint', 'rear_right_wheel_joint',
)
PUBLISHER = '/robot_state_publisher'
STATIC_TOPIC = '/tf_static'


class Trial:
    def __init__(self, output, model, expected_lidar):
        self.output = output.resolve()
        self.output.mkdir(parents=True)
        self.model = model.resolve(strict=True)
        self.expected_lidar = expected_lidar
        self.model_log = self.output / 'model-check.txt'
        self.qos_log = self.output / 'tf-qos.txt'
        self.env = os.environ | {
            'ROS_DOMAIN_ID': os.environ.get('ROS_DOMAIN_ID', '204'),
            'ROS_AUTOMATIC_DISCOVERY_RANGE': 'LOCALHOST',
            'ROS_LOG_DIR': str(self.output / 'ros-logs'),
            'RCUTILS_COLORIZED_OUTPUT': '0',
            'PYTHONUNBUFFERED': '1',
        }

    def record(self, path, command, output, status):
        name = shlex.join(command)
        with path.open('a', encoding='utf-8') as log:
            log.write(f'$ {name}\n{output.rstrip()}\n[exit {status}]\n\n')
        print(f'{name} -> {status}', flush=True)

    def cli(self, path, command, codes=(0,), timeout=22):
        result = subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=timeout)
        self.record(path, command, result.stdout + result.stderr, result.returncode)
        if result.returncode not in codes:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout

    def graph(self, path, arguments, ready):
        command = ('ros2', *arguments, '--no-daemon', '--spin-time', '2')
        for attempt in range(5):
            output = self.cli(path, command, codes=(0, 1))
            if ready(output):
                return output
            time.sleep(0.4)
        raise RuntimeError(f'Graph did not converge: {shlex.join(command)}')

    @contextmanager
    def process(self, name, command):
        path = self.output / f'{name}.log'
        with path.open('w', encoding='utf-8') as log:
            process = subprocess.Popen(
                command, env=self.env, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        with self.model_log.open('a', encoding='utf-8') as log:
            log.write(f'$ {shlex.join(command)}\nФоновый процесс, лог {path.name}\n\n')
        try:
            yield process
            if process.poll() is not None:
                raise RuntimeError(path.read_text())
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=6)
                    raise RuntimeError(f'{name} did not stop on SIGINT')
            with self.model_log.open('a', encoding='utf-8') as log:
                log.write(f'{name}: exit={process.returncode} после остановки\n\n')

    def expand(self):
        target = self.output / 'vehicle.urdf'
        self.cli(self.model_log, ('xacro', str(self.model), '-o', str(target)))
        tree = ET.parse(target)
        ET.indent(tree, space='  ')
        tree.write(target, encoding='utf-8', xml_declaration=True)
        self.cli(self.model_log, ('check_urdf', str(target)))
        return tree.getroot()

    def verify_lidar(self):
        output = self.cli(self.model_log, (
            'timeout', '--signal=INT', '6s', 'ros2', 'run', 'tf2_ros', 'tf2_echo',
            'base_link', 'lidar_link',
        ), codes=(124,))
        positions = re.findall(r'Translation: \[([^\]]+)\]', output)
        assert positions, output
        for position in positions:
            coordinates = [float(number) for number in position.split(',')]
            assert coordinates == self.expected_lidar, output

    def topic_profile(self, topic, durability):
        output = self.graph(
            self.qos_log, ('topic', 'info', topic, '--verbose'),
            lambda text: 'Publisher count: 1' in text and 'Node name: robot_state_publisher' in text,
        )
        assert 'Reliability: RELIABLE' in output
        assert f'Durability: {durability}' in output

    def echo(self, topic, durability, expected, seconds=4):
        command = (
            'timeout', f'{seconds}s', 'ros2', 'topic', 'echo', topic, 'tf2_msgs/msg/TFMessage',
            '--once', '--no-daemon', '--spin-time', '0.1',
            '--qos-reliability', 'reliable', '--qos-durability', durability,
        )
        for attempt in range(3):
            result = subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=seconds + 5)
            self.record(self.qos_log, command, result.stdout + result.stderr, result.returncode)
            if expected == 124:
                assert result.returncode == 124 and 'child_frame_id:' not in result.stdout
                return []
            if result.returncode == 0:
                message = next(yaml.safe_load_all(result.stdout))
                return message['transforms']
            assert result.returncode == 124
        raise RuntimeError(f'Transforms were not received on {topic}')

    def verify_static(self, static):
        self.topic_profile(STATIC_TOPIC, 'TRANSIENT_LOCAL')
        received = self.echo(STATIC_TOPIC, 'transient_local', 0)
        assert {(tf['header']['frame_id'], tf['child_frame_id']) for tf in received} == static
        self.echo(STATIC_TOPIC, 'volatile', 124)
        with self.qos_log.open('a', encoding='utf-8') as log:
            log.write(
                '/tf_static хранит последнее сообщение с жёсткими связями. '
                'Поздний подписчик с TRANSIENT_LOCAL получает его, а VOLATILE ждёт новых сообщений. '
                '/tf передаёт обновления подвижных связей с VOLATILE.\n\n'
            )

    def verify_dynamic(self, dynamic, all_edges):
        self.topic_profile('/tf', 'VOLATILE')
        recorded = self.echo('/tf', 'volatile', 0, seconds=7)
        assert {(tf['header']['frame_id'], tf['child_frame_id']) for tf in recorded} == dynamic
        self.cli(self.model_log, (
            'ros2', 'run', 'tf2_tools', 'view_frames', '--wait-time', '4',
            '--output', str(self.output / 'frames'),
        ))
        diagram = (self.output / 'frames.gv').read_text()
        for parent, child in all_edges:
            assert f'"{parent}" -> "{child}"' in diagram, diagram
        assert (self.output / 'frames.pdf').stat().st_size > 0

    def capture_rviz(self):
        from PyQt6.QtGui import QGuiApplication

        config = Path(get_package_share_directory('course_description')) / 'rviz/vehicle.rviz'
        with self.process('rviz', (
            'ros2', 'run', 'rviz2', 'rviz2', '-d', str(config), '--display-title-format', 'PR06-RViz',
        )) as process:
            for attempt in range(14):
                info = self.cli(self.model_log, ('xwininfo', '-name', 'PR06-RViz'), codes=(0, 1))
                identifier = re.search(r'Window id:\s*(0x[0-9a-fA-F]+)', info)
                if identifier:
                    break
                if process.poll() is not None:
                    raise RuntimeError((self.output / 'rviz.log').read_text())
                time.sleep(0.5)
            else:
                raise RuntimeError('RViz window was not found on the virtual display')
            time.sleep(3)
            app = QGuiApplication(['pr06-window-capture'])
            window = app.primaryScreen().grabWindow(int(identifier.group(1), 16))
            assert window.width() > 400 and window.height() > 300
            assert window.save(str(self.output / 'rviz.png'), 'PNG')

    def run(self, minimal, rviz):
        model = self.expand()
        self.graph(self.model_log, ('node', 'list'), lambda text: not text.strip())
        launch = (
            'ros2', 'launch', 'course_description', 'description.launch.py',
            'rviz:=false', f'model:={self.model}',
        )
        with self.process('state-publisher', launch):
            self.graph(self.model_log, ('node', 'list'), lambda text: PUBLISHER in text.splitlines())
            self.verify_lidar()
            if not minimal:
                static, dynamic = set(), set()
                for joint in model.findall('joint'):
                    edges = static if joint.get('type') == 'fixed' else dynamic
                    edges.add((joint.find('parent').get('link'), joint.find('child').get('link')))
                self.verify_static(static)
                message = yaml.safe_dump({
                    'header': 'auto', 'name': list(MOVABLE_JOINTS), 'position': [0.0] * len(MOVABLE_JOINTS),
                }, default_flow_style=True).strip()
                with self.process('joint-states', (
                    'ros2', 'topic', 'pub', '-r', '10', '/joint_states', 'sensor_msgs/msg/JointState', message,
                )):
                    self.verify_dynamic(dynamic, static | dynamic)
                    if rviz:
                        self.capture_rviz()
        self.graph(self.model_log, ('node', 'list'), lambda text: not text.strip())


def main():
    parser = argparse.ArgumentParser()
    share = Path(get_package_share_directory('course_description'))
    parser.add_argument('--model', type=Path, default=share / 'urdf/vehicle.urdf.xacro')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--minimal', action='store_true')
    parser.add_argument('--expect-broken', action='store_true')
    parser.add_argument('--rviz', action='store_true')
    args = parser.parse_args()
    expected = [0.56, 0.0, 0.76] if args.expect_broken else [0.28, 0.0, 0.38]
    Trial(args.output, args.model, expected).run(args.minimal, args.rviz)


if __name__ == '__main__':
    main()
