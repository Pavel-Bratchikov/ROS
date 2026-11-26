# Граф turtlesim и изоляция доменов

Опыт выполнен в Ubuntu 26.04.1 LTS с ROS 2 Lyrical и `rmw_fastrtps_cpp`. Симулятор работал с платформой Qt `offscreen`. Ввод для `turtle_teleop_key` подавался в псевдотерминал как последовательность клавиши ↑, а движение проверялось по координате `x`. В каждом процессе было задано `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`.

## Граф до смены домена

Симулятор `ros2 run turtlesim turtlesim_node`, управление `ros2 run turtlesim turtle_teleop_key` и наблюдатель стартовали с `ROS_DOMAIN_ID=16`.

```console
$ ros2 node list --no-daemon --spin-time 2
/teleop_turtle
/turtlesim
$ ros2 topic list -t --no-daemon --spin-time 2
/parameter_events [rcl_interfaces/msg/ParameterEvent]
/rosout [rcl_interfaces/msg/Log]
/turtle1/cmd_vel [geometry_msgs/msg/Twist]
/turtle1/color_sensor [turtlesim_msgs/msg/Color]
/turtle1/pose [turtlesim_msgs/msg/Pose]
$ ros2 topic type /turtle1/pose --no-daemon --spin-time 2
turtlesim_msgs/msg/Pose
```

Узел `/teleop_turtle` переводит ввод с клавиатуры в команды скорости для `/turtle1/cmd_vel`. Узел `/turtlesim` читает этот топик, обновляет положение и публикует позу и цвет в точке, где находится черепаха. Из вывода `ros2 node info /turtlesim --no-daemon --spin-time 2`:

```text
/turtlesim
  Subscribers:
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /turtle1/cmd_vel: geometry_msgs/msg/Twist
  Publishers:
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /rosout: rcl_interfaces/msg/Log
    /turtle1/color_sensor: turtlesim_msgs/msg/Color
    /turtle1/pose: turtlesim_msgs/msg/Pose
```

Координата `x` до нажатий была `5.5444`. После нажатий получено сообщение:

```console
$ timeout 5s ros2 topic echo /turtle1/pose turtlesim_msgs/msg/Pose --once
x: 9.160444259643555
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
---
```

Команда `timeout --signal=INT 12s ros2 topic hz /turtle1/pose` работала 12 секунд. Последняя строка среднего и статистика интервалов:

```text
average rate: 62.500
    min: 0.015s max: 0.017s std dev: 0.00052s window: 624
```

Измеренная частота — **62.500 Гц**, средний интервал около 16 мс.

## Изоляция

Симулятор продолжал работать в домене 16. Управление остановлено и заново запущено в домене 17. В этом же домене запущены CLI-команды наблюдения:

```console
$ export ROS_DOMAIN_ID=17
$ ros2 node list --no-daemon --spin-time 2
/teleop_turtle
$ timeout 5s ros2 topic echo /turtle1/pose turtlesim_msgs/msg/Pose --once > evidence/pr01/pose-broken.txt 2>&1
$ printf 'exit=%s\n' "$?"
exit=124
```

За пять секунд поза не поступила. В файле осталась строка `!rclpy.ok()` от завершившегося CLI. После нажатий ↑ в домене 17 координата черепахи осталась `x=9.1604` по измерению из домена 16.

## Восстановление

Управление остановлено и запущено в домене 16. Наблюдатель вернулся туда же и повторил команду с тем же типом и таймаутом:

```console
$ export ROS_DOMAIN_ID=16
$ ros2 node list --no-daemon --spin-time 2
/teleop_turtle
/turtlesim
$ timeout 5s ros2 topic echo /turtle1/pose turtlesim_msgs/msg/Pose --once > evidence/pr01/pose-fixed.txt 2>&1
$ printf 'exit=%s\n' "$?"
exit=0
```

Поза сохранилась в `pose-fixed.txt`. После нажатий ↑ координата `x` изменилась с `9.1604` на `11.0889`.

| Этап | Симулятор | Управление | Наблюдатель | Получение позы |
| --- | ---: | ---: | ---: | --- |
| До смены | 16 | 16 | 16 | сообщение, код `0` |
| Изоляция | 16 | 17 | 17 | таймаут 5 с, код `124` |
| Восстановление | 16 | 16 | 16 | сообщение, код `0` |

Участники DDS обнаруживают друг друга внутри одного домена. `ROS_DOMAIN_ID` читается при создании участника, поэтому для переноса ноды управления пришлось завершить старый процесс и запустить новый. Симулятор оставался в домене 16 весь опыт и восстановил обмен после возвращения управления и наблюдателя.
