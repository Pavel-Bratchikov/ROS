# Команды опыта ПР04

Домен `185`, Qt `offscreen`.

```console
$ ros2 node list --no-daemon --spin-time 2

[exit 0]
```

```console
$ ros2 launch turtle_bringup sim.launch.py
Лог процесса: broken-commands-turtlesim.txt
[запущен]
```

```console
$ ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
Лог процесса: broken-commands-patrol.txt
[запущен]
```

```console
$ ros2 node list --no-daemon --spin-time 2
/patrol
/turtlesim
[exit 0]
```

```console
$ ros2 topic type /turtle1/pose --no-daemon --spin-time 2
turtlesim_msgs/msg/Pose
[exit 0]
```

```console
$ ros2 param get /patrol publish_hz
Double value is: 10.0
[exit 0]
```

```console
$ timeout --signal=INT 7s ros2 topic hz /turtle1/cmd_vel --window 25
average rate: 9.998
	min: 0.100s max: 0.101s std dev: 0.00040s window: 4
average rate: 9.998
	min: 0.099s max: 0.101s std dev: 0.00031s window: 14
average rate: 9.997
	min: 0.099s max: 0.101s std dev: 0.00034s window: 24
average rate: 9.997
	min: 0.099s max: 0.101s std dev: 0.00040s window: 25
[exit 124]
```

```console
$ ros2 param set /patrol publish_hz 5.0
Set parameter successful
[exit 0]
```

```console
$ ros2 param get /patrol publish_hz
Double value is: 5.0
[exit 0]
```

```console
$ timeout --signal=INT 7s ros2 topic hz /turtle1/cmd_vel --window 25
average rate: 4.995
	min: 0.200s max: 0.201s std dev: 0.00037s window: 4
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00039s window: 9
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00036s window: 14
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00034s window: 19
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00031s window: 24
[exit 124]
```

```console
$ ros2 param set /patrol publish_hz 0.0

[exit 2; patrol exit 1]
```
