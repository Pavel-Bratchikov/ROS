# Команды опыта ПР04

Домен `184`, Qt `offscreen`.

```console
$ ros2 node list --no-daemon --spin-time 2

[exit 0]
```

```console
$ ros2 launch turtle_bringup sim.launch.py
Лог процесса: fixed-commands-turtlesim.txt
[запущен]
```

```console
$ ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
Лог процесса: fixed-commands-patrol.txt
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
average rate: 9.999
	min: 0.099s max: 0.101s std dev: 0.00048s window: 9
average rate: 9.996
	min: 0.099s max: 0.101s std dev: 0.00040s window: 19
average rate: 10.000
	min: 0.099s max: 0.101s std dev: 0.00039s window: 25
average rate: 9.999
	min: 0.099s max: 0.101s std dev: 0.00048s window: 25
average rate: 10.000
	min: 0.099s max: 0.101s std dev: 0.00054s window: 25
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
average rate: 5.000
	min: 0.200s max: 0.200s std dev: 0.00016s window: 4
average rate: 4.998
	min: 0.200s max: 0.200s std dev: 0.00018s window: 9
average rate: 4.999
	min: 0.199s max: 0.200s std dev: 0.00024s window: 14
average rate: 5.000
	min: 0.199s max: 0.200s std dev: 0.00023s window: 19
average rate: 5.000
	min: 0.199s max: 0.200s std dev: 0.00021s window: 24
[exit 124]
```

```console
$ ros2 param set /patrol publish_hz 0.0
Setting parameter failed: publish_hz needs a finite number in [1.0, 30.0]
[exit 0]
```

```console
$ ros2 param get /patrol publish_hz
Double value is: 5.0
[exit 0]
```

```console
$ ros2 param set /patrol publish_hz -1.0
Setting parameter failed: publish_hz needs a finite number in [1.0, 30.0]
[exit 0]
```

```console
$ ros2 param get /patrol publish_hz
Double value is: 5.0
[exit 0]
```

```console
$ ros2 param set /patrol publish_hz .nan
Setting parameter failed: publish_hz needs a finite number in [1.0, 30.0]
[exit 0]
```

```console
$ ros2 param get /patrol publish_hz
Double value is: 5.0
[exit 0]
```

```console
$ timeout --signal=INT 7s ros2 topic hz /turtle1/cmd_vel --window 25
average rate: 5.001
	min: 0.200s max: 0.200s std dev: 0.00005s window: 4
average rate: 5.000
	min: 0.200s max: 0.200s std dev: 0.00012s window: 9
average rate: 5.000
	min: 0.200s max: 0.200s std dev: 0.00010s window: 14
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00024s window: 19
average rate: 4.999
	min: 0.199s max: 0.201s std dev: 0.00026s window: 24
[exit 124]
```

```console
$ ros2 param set /patrol linear_speed 0.8
Set parameter successful
[exit 0]
```

```console
$ ros2 param set /patrol turn_rate -0.5
Set parameter successful
[exit 0]
```

```console
$ timeout 8s ros2 topic echo /turtle1/cmd_vel geometry_msgs/msg/Twist --once
linear:
  x: 0.8
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: -0.5
---
[exit 0]
```

```console
$ ros2 service call /clear std_srvs/srv/Empty '{}'
waiting for service to become available...
requester: making request: std_srvs.srv.Empty_Request()

response:
std_srvs.srv.Empty_Response()
[exit 0]
```

```console
$ ros2 action list -t
/turtle1/rotate_absolute [turtlesim_msgs/action/RotateAbsolute]
[exit 0]
```
