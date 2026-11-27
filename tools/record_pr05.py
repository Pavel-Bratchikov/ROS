import argparse
from contextlib import ExitStack, contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import time

import yaml


TOPIC = '/robot_a/sensor_pose'
POSE_TYPE = 'turtlesim_msgs/msg/Pose'
SYSTEM = {'/turtlesim', '/robot_a/patrol', '/robot_a/pose_relay', '/robot_a/pose_subscriber'}
RECORDER = '/rosbag2_recorder'
PLAYBACK = {'/rosbag2_player', '/robot_a/replay_reliable', '/robot_a/replay_best_effort'}


class Experiment:
    def __init__(self, output, overrides):
        self.output = output.resolve()
        self.output.mkdir(parents=True)
        self.before = self.output / 'qos-before.txt'
        self.after = self.output / 'qos-after.txt'
        self.bag = self.output / 'bag'
        self.overrides = overrides.resolve(strict=True)
        self.env = os.environ | {
            'ROS_DOMAIN_ID': os.environ.get('ROS_DOMAIN_ID', '196'),
            'ROS_AUTOMATIC_DISCOVERY_RANGE': 'LOCALHOST',
            'QT_QPA_PLATFORM': 'offscreen',
            'ROS_LOG_DIR': str(self.output / 'ros-logs'),
            'RCUTILS_COLORIZED_OUTPUT': '0',
            'PYTHONUNBUFFERED': '1',
        }

    def record(self, destination, command, message, status):
        label = shlex.join(command)
        with destination.open('a', encoding='utf-8') as transcript:
            transcript.write(f'$ {label}\n{message.rstrip()}\n[{status}]\n\n')
        print(f'{label} -> {status}', flush=True)

    def cli(self, destination, command, timeout=20):
        result = subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=timeout)
        self.record(destination, command, result.stdout + result.stderr, f'exit {result.returncode}')
        return result

    def query(self, destination, arguments, ready):
        command = ('ros2', *arguments, '--no-daemon', '--spin-time', '2')
        for attempt in range(6):
            result = self.cli(destination, command, timeout=9)
            if result.returncode == 0 and ready(result.stdout):
                return result.stdout
            time.sleep(0.3)
        raise RuntimeError(f'Graph did not converge for {shlex.join(command)}')

    def nodes(self, destination, expected):
        self.query(destination, ('node', 'list'), lambda text: set(text.splitlines()) == expected)

    def endpoints(self, destination, publisher, observers):
        def ready(text):
            lines = text.splitlines()
            expected = [publisher, *observers]
            return 'Publisher count: 1' in lines and all(f'Node name: {name}' in lines for name in expected)

        return self.query(destination, ('topic', 'info', TOPIC, '--verbose'), ready)

    @contextmanager
    def process(self, destination, label, command):
        log = self.output / f'{label}.log'
        with log.open('w', encoding='utf-8') as stream:
            child = subprocess.Popen(
                command, env=self.env, stdout=stream, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        self.record(destination, command, f'Лог процесса: {log.name}', 'started')
        try:
            yield log
            if child.poll() is not None:
                raise RuntimeError(f'{label} exited unexpectedly: {log.read_text()}')
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGINT)
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=8)
                    raise RuntimeError(f'{label} did not stop on SIGINT')
            self.record(destination, command, f'Процесс завершён, лог: {log.name}', f'exit {child.returncode}')

    def launch(self, destination, reliability, record):
        return self.process(destination, f'live-{reliability}', (
            'ros2', 'launch', 'course_bringup', 'patrol.launch.py', 'namespace:=robot_a',
            f'subscriber_reliability:={reliability}', f'record:={str(record).lower()}',
            f'bag_dir:={self.bag}',
        ))

    def echo(self, destination, reliability):
        command = (
            'timeout', '3s', 'ros2', 'topic', 'echo', TOPIC, POSE_TYPE, '--once',
            '--qos-reliability', reliability, '--qos-history', 'keep_last',
            '--qos-depth', '10', '--qos-durability', 'volatile',
            '--no-daemon', '--spin-time', '0.1',
        )
        for attempt in range(3):
            result = self.cli(destination, command, timeout=8)
            if reliability == 'reliable':
                assert result.returncode == 124 and not re.search(r'^x:', result.stdout, re.MULTILINE)
                return
            if result.returncode == 0:
                pose = next(yaml.safe_load_all(result.stdout))
                assert {'x', 'y', 'theta', 'linear_velocity', 'angular_velocity'} <= pose.keys()
                return
            assert result.returncode == 124
        raise RuntimeError('The best_effort echo did not receive a pose')

    def count(self, destination, path, reliability):
        content = path.read_text(encoding='utf-8')
        counts = re.findall(rf'reliability={reliability} received=(\d+)', content)
        assert counts, f'No counters in {path.name}'
        total = max(map(int, counts))
        assert (total > 0) == (reliability == 'best_effort'), content
        with destination.open('a', encoding='utf-8') as transcript:
            transcript.write(f'{path.name}: {reliability}, максимум счётчика received={total}\n\n')

    def live(self):
        self.nodes(self.before, set())
        args = self.cli(self.before, ('ros2', 'launch', 'course_bringup', 'patrol.launch.py', '--show-args'))
        assert args.returncode == 0
        with self.launch(self.before, 'reliable', False) as log:
            self.nodes(self.before, SYSTEM)
            assert not self.bag.exists()
            info = self.endpoints(self.before, 'pose_relay', ('pose_subscriber',))
            assert 'Reliability: BEST_EFFORT' in info and 'Reliability: RELIABLE' in info
            topics = self.query(self.before, ('topic', 'list'), lambda text: TOPIC in text.splitlines())
            assert '/sensor_pose' not in topics.splitlines()
            self.query(
                self.before, ('node', 'info', '/robot_a/patrol'),
                lambda text: '/turtle1/pose' in text and '/turtle1/cmd_vel' in text,
            )
            self.echo(self.before, 'reliable')
        self.count(self.before, log, 'reliable')
        self.nodes(self.before, set())

        with self.launch(self.after, 'best_effort', True) as log:
            self.nodes(self.after, SYSTEM | {RECORDER})
            self.endpoints(self.after, 'pose_relay', ('pose_subscriber', 'rosbag2_recorder'))
            self.echo(self.after, 'best_effort')
            time.sleep(3.0)
        self.count(self.after, log, 'best_effort')
        self.nodes(self.after, set())

    def recording(self):
        result = self.cli(self.after, ('ros2', 'bag', 'info', str(self.bag)))
        assert result.returncode == 0
        metadata_path = self.bag / 'metadata.yaml'
        metadata = yaml.safe_load(metadata_path.read_text())['rosbag2_bagfile_information']
        topic, = metadata['topics_with_message_count']
        file_name, = metadata['relative_file_paths']
        assert metadata['storage_identifier'] == 'mcap'
        assert topic['message_count'] == metadata['message_count'] > 0
        assert topic['topic_metadata']['name'] == TOPIC
        assert topic['topic_metadata']['type'] == POSE_TYPE
        assert file_name.endswith('.mcap') and len(list(self.bag.glob('*.mcap'))) == 1
        shutil.copyfile(metadata_path, self.output / 'bag-metadata.yaml')
        return self.bag / file_name

    def replay(self, mcap):
        checksum = sha256(mcap.read_bytes()).hexdigest()
        with ExitStack() as stack:
            observers = {}
            for profile, destination in (('reliable', self.before), ('best_effort', self.after)):
                command = (
                    'ros2', 'run', 'course_bringup', 'pose_subscriber', '--ros-args',
                    '-r', '__ns:=/robot_a', '-r', f'__node:=replay_{profile}',
                    '-p', f'reliability:={profile}',
                )
                observers[profile] = stack.enter_context(self.process(destination, f'replay-{profile}', command))
            self.nodes(self.after, PLAYBACK - {'/rosbag2_player'})
            stack.enter_context(self.process(self.after, 'replay-player', (
                'ros2', 'bag', 'play', str(self.bag), '--loop',
                '--qos-profile-overrides-path', str(self.overrides), '--disable-keyboard-controls',
            )))
            self.nodes(self.after, PLAYBACK)
            info = self.endpoints(self.before, 'rosbag2_player', ('replay_reliable', 'replay_best_effort'))
            assert 'Reliability: BEST_EFFORT' in info and 'Reliability: RELIABLE' in info
            self.echo(self.before, 'reliable')
            self.echo(self.after, 'best_effort')
        self.count(self.before, observers['reliable'], 'reliable')
        self.count(self.after, observers['best_effort'], 'best_effort')
        self.nodes(self.after, set())
        assert sha256(mcap.read_bytes()).hexdigest() == checksum
        hashes = json.dumps({mcap.name: checksum}, indent=2)
        (self.output / 'bag-sha256.json').write_text(hashes + '\n', encoding='utf-8')
        with self.after.open('a', encoding='utf-8') as transcript:
            transcript.write(f'SHA-256 одного MCAP до и после replay совпадает:\n{hashes}\n')

    def run(self):
        for file in (self.before, self.after):
            file.write_text(f"ROS_DOMAIN_ID={self.env['ROS_DOMAIN_ID']}, QT_QPA_PLATFORM=offscreen\n\n", encoding='utf-8')
        self.live()
        self.replay(self.recording())
        print('Verified live QoS and replay from the same MCAP.', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--overrides', type=Path, default=Path('config/qos-overrides.yaml'))
    args = parser.parse_args()
    Experiment(args.output, args.overrides).run()


if __name__ == '__main__':
    main()
