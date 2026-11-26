# Проверка ноды patrol

Опыт выполнен на ROS 2 Lyrical в домене `16` с областью обнаружения `LOCALHOST`. Пакет `turtle_bringup` из предыдущей работы запускает один симулятор. При замере Qt работал в режиме `offscreen`, поэтому движение проверялось по сообщениям позы.

## Минимальный запуск и тесты

В отдельном временном workspace был собран пакет с нодой, которая только вызывала `rclpy.init`, создавала `/patrol` и входила в `spin`. После запуска установленной команды в графе появилась нода:

```console
$ ros2 run patrol patrol
$ ros2 node list --no-daemon --spin-time 2
/patrol
```

После SIGINT команда завершилась с кодом `0`, и список нод снова стал пуст. Полная версия собрана командой `colcon build --symlink-install --packages-select turtle_bringup patrol`. Два теста выбора скорости прошли как через `pytest`, так и через `colcon test`. Вывод сохранён в [tests.txt](tests.txt).

## Таймер до и после первой позы

Полная нода `patrol` была запущена до симулятора. В этот момент в графе была только `/patrol`. Таймер уже работал, а команда была нулевой:

```console
$ timeout 6s ros2 topic echo /cmd_vel geometry_msgs/msg/Twist --once
linear:
  x: 0.0
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.0
---
```

После `ros2 launch turtle_bringup sim.launch.py` ноды `/turtlesim` и `/patrol` обнаружили друг друга. Команда `ros2 topic type /turtle1/pose --no-daemon --spin-time 2` вернула `turtlesim_msgs/msg/Pose`.

```console
$ ros2 topic info /turtle1/pose --verbose --no-daemon --spin-time 2
Type: turtlesim_msgs/msg/Pose
Publisher count: 1
Node name: turtlesim
Node namespace: /
Endpoint type: PUBLISHER
Subscription count: 1
Node name: patrol
Node namespace: /
Endpoint type: SUBSCRIPTION
```

Тот же процесс `patrol` начал публиковать `linear.x = 0.5` и `angular.z = 0.3` после первого сообщения позы:

```console
$ timeout 6s ros2 topic echo /cmd_vel geometry_msgs/msg/Twist --once
linear:
  x: 0.5
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.3
---
```

## Разрыв связи по имени

В корневом пространстве имён относительный `cmd_vel` раскрывается в `/cmd_vel`. Вывод графа показал, что издатель и подписчик стоят на разных топиках:

```console
$ ros2 topic info /cmd_vel --verbose --no-daemon --spin-time 2
Type: geometry_msgs/msg/Twist
Publisher count: 1
Node name: patrol
Node namespace: /
Endpoint type: PUBLISHER
Subscription count: 0
$ ros2 topic info /turtle1/cmd_vel --verbose --no-daemon --spin-time 2
Type: geometry_msgs/msg/Twist
Publisher count: 0
Subscription count: 1
Node name: turtlesim
Node namespace: /
Endpoint type: SUBSCRIPTION
```

Поза сохранялась одинаковой в двух замерах с паузой 1,5 с. Публикация ненулевого `Twist` в `/cmd_vel` сама по себе движения не вызвала.

## Remap и частота команды

Симулятор остался запущенным. Нода `patrol` была остановлена и запущена снова с одним изменением — переназначением выходного имени:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

```console
$ ros2 topic info /turtle1/cmd_vel --verbose --no-daemon --spin-time 2
Type: geometry_msgs/msg/Twist
Publisher count: 1
Node name: patrol
Node namespace: /
Endpoint type: PUBLISHER
Subscription count: 1
Node name: turtlesim
Node namespace: /
Endpoint type: SUBSCRIPTION
```

После переназначения `turtlesim` начал получать команды и менять позу. `timeout --signal=INT 13s ros2 topic hz /turtle1/cmd_vel` зафиксировала последнее среднее **10.000 Гц** по окну из 109 интервалов:

```text
average rate: 10.000
    min: 0.099s max: 0.101s std dev: 0.00039s window: 109
```

Для каждого замера позы использовалась команда `timeout 6s ros2 topic echo /turtle1/pose turtlesim_msgs/msg/Pose --once`.

| Замер | x | y | theta | linear_velocity | angular_velocity |
| --- | ---: | ---: | ---: | ---: | ---: |
| Сразу после запуска симулятора | `5.544445` | `5.544445` | `0.000000` | `0.000000` | `0.000000` |
| Позже, при публикации в `/cmd_vel` | `5.544445` | `5.544445` | `0.000000` | `0.000000` | `0.000000` |
| При публикации после remap | `6.943631` | `6.311746` | `0.998415` | `0.500000` | `0.300000` |
| Через 2 с после остановки patrol | `7.163534` | `6.832473` | `1.339215` | `0.000000` | `0.000000` |

После остановки `patrol` в графе остался `/turtlesim`. Черепашка перестала двигаться после истечения срока действия последней команды. Это подтверждают нулевые скорости и неизменная поза при повторном замере.

## Как работает нода

- `rclpy.init` создаёт контекст ROS 2 для процесса.
- `rclpy.spin` передаёт управление исполнителю, который вызывает обработчики подписки и таймера.
- Callback подписки только сохраняет последнее сообщение. Таймер каждые 0,1 с передаёт его в чистую функцию выбора скорости и публикует результат.
- `Ctrl+C` останавливает обработку, уничтожает ноду и её издателя. Симулятор перестаёт использовать старый `Twist` по своему таймауту.
