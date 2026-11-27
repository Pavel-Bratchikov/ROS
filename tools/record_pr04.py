import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time

import yaml


def stop(process):
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)


class Experiment:
    def __init__(self, output, env, stack):
        self.output = output
        self.env = env
        self.stack = stack

    def record(self, command, stdout, result):
        label = shlex.join(command)
        with self.output.open('a', encoding='utf-8') as log:
            log.write(f'```console\n$ {label}\n{stdout.rstrip()}\n[{result}]\n```\n\n')
        print(f'{label} -> {result}', flush=True)

    def cli(self, *args, codes=(0,)):
        result = subprocess.run(args, env=self.env, capture_output=True, text=True, timeout=22)
        self.record(args, result.stdout + result.stderr, f'exit {result.returncode}')
        if result.returncode not in codes:
            raise RuntimeError(result.stderr or result.stdout)
        return result

    def start(self, name, *command):
        path = self.output.with_name(f'{self.output.stem}-{name}.txt')
        with path.open('w', encoding='utf-8') as log:
            process = subprocess.Popen(
                command, env=self.env, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        self.stack.callback(stop, process)
        self.record(command, f'Лог процесса: {path.name}', 'запущен')
        return process, path

    def discovered_nodes(self):
        output = self.cli('ros2', 'node', 'list', '--no-daemon', '--spin-time', '2')
        return set(output.stdout.splitlines())

    def measure_rate(self, expected):
        for attempt in range(2):
            result = self.cli(
                'timeout', '--signal=INT', '7s', 'ros2', 'topic', 'hz',
                '/turtle1/cmd_vel', '--window', '25', codes=(124,),
            )
            output = result.stdout
            rates = re.findall(r'average rate:\s*([0-9.]+)', output)
            if rates and abs(float(rates[-1]) - expected) < expected * 0.12:
                return
        raise RuntimeError(f'Expected a stream near {expected} Hz, got {output!r}')

    def get_frequency(self):
        value = self.cli('ros2', 'param', 'get', '/patrol', 'publish_hz')
        return float(value.stdout.rsplit(':', 1)[1])

    def set_parameter(self, name, value):
        result = self.cli('ros2', 'param', 'set', '/patrol', name, value, codes=(0, 1))
        return result.stdout + result.stderr

    def verify_broken(self, patrol, patrol_log):
        command = ['ros2', 'param', 'set', '/patrol', 'publish_hz', '0.0']
        with subprocess.Popen(
            command, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, start_new_session=True,
        ) as client:
            try:
                assert patrol.wait(timeout=14) != 0
            finally:
                stop(client)
                response, _ = client.communicate(timeout=5)
        self.record(command, response, f'exit {client.returncode}; patrol exit {patrol.returncode}')
        assert 'ZeroDivisionError' in patrol_log.read_text(encoding='utf-8')
        print('Reproduced ZeroDivisionError in patrol.', flush=True)

    def verify_fixed(self, patrol):
        for value in ('0.0', '-1.0', '.nan'):
            rejection = self.set_parameter('publish_hz', value)
            assert 'failed' in rejection.lower() and 'publish_hz' in rejection
            assert self.get_frequency() == 5.0
        self.measure_rate(5.0)

        assert 'successful' in self.set_parameter('linear_speed', '0.8')
        assert 'successful' in self.set_parameter('turn_rate', '-0.5')
        twist = self.cli(
            'timeout', '8s', 'ros2', 'topic', 'echo', '/turtle1/cmd_vel',
            'geometry_msgs/msg/Twist', '--once',
        )
        command = next(yaml.safe_load_all(twist.stdout))
        assert command['linear']['x'] == 0.8 and command['angular']['z'] == -0.5
        reply = self.cli('ros2', 'service', 'call', '/clear', 'std_srvs/srv/Empty', '{}')
        assert 'Empty_Response' in reply.stdout
        actions = self.cli('ros2', 'action', 'list', '-t').stdout
        assert '/turtle1/rotate_absolute' in actions and 'RotateAbsolute' in actions
        assert patrol.poll() is None
        print('Verified parameter rejection, stream, Twist, service and action.', flush=True)

    def run(self, expect_broken):
        if self.discovered_nodes():
            raise RuntimeError('Choose a ROS_DOMAIN_ID with an empty graph')
        self.start('turtlesim', 'ros2', 'launch', 'turtle_bringup', 'sim.launch.py')
        patrol, patrol_log = self.start(
            'patrol', 'ros2', 'run', 'patrol', 'patrol', '--ros-args',
            '-r', 'cmd_vel:=/turtle1/cmd_vel',
        )
        for attempt in range(5):
            if self.discovered_nodes() == {'/patrol', '/turtlesim'}:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError('patrol and turtlesim were not discovered')
        for attempt in range(4):
            pose_type = self.cli(
                'ros2', 'topic', 'type', '/turtle1/pose', '--no-daemon', '--spin-time', '2', codes=(0, 1),
            )
            if '/msg/Pose' in pose_type.stdout:
                break
        else:
            raise RuntimeError('Pose topic was not discovered')

        assert self.get_frequency() == 10.0
        self.measure_rate(10.0)
        assert 'successful' in self.set_parameter('publish_hz', '5.0')
        assert self.get_frequency() == 5.0
        self.measure_rate(5.0)

        if expect_broken:
            self.verify_broken(patrol, patrol_log)
        else:
            self.verify_fixed(patrol)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expect-broken', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ | {
        'ROS_DOMAIN_ID': os.environ.get('ROS_DOMAIN_ID', '184'),
        'ROS_AUTOMATIC_DISCOVERY_RANGE': 'LOCALHOST',
        'QT_QPA_PLATFORM': 'offscreen',
        'ROS_LOG_DIR': str(output.parent / 'ros-logs'),
        'RCUTILS_COLORIZED_OUTPUT': '0',
        'PYTHONUNBUFFERED': '1',
    }
    output.write_text(
        f"# Команды опыта ПР04\n\nДомен `{env['ROS_DOMAIN_ID']}`, Qt `offscreen`.\n\n",
        encoding='utf-8',
    )
    with ExitStack() as stack:
        Experiment(output, env, stack).run(args.expect_broken)


if __name__ == '__main__':
    main()
