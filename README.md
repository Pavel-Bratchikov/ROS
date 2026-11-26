# ПР01. Окружение и граф ROS 2

В этой работе `turtlesim` публикует состояние черепахи, а `turtle_teleop_key` передаёт команды с клавиатуры. Опыт показывает, как проверить обмен сообщениями и что происходит, если узлы запущены в разных доменах DDS.

## Запуск

Откройте три Bash-терминала в одной среде. Для Ubuntu 26.04 и ROS 2 Lyrical в каждом выполните:

```bash
source /opt/ros/lyrical/setup.bash
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_DOMAIN_ID=16
```

На Ubuntu 24.04 подключите `/opt/ros/jazzy/setup.bash`. Если на занятии выдана другая пара доменов, замените 16 и 17 во всех командах.

В первом терминале запустите симулятор:

```bash
ros2 run turtlesim turtlesim_node
```

Во втором запустите управление и нажмите стрелки при фокусе в этом терминале:

```bash
ros2 run turtlesim turtle_teleop_key
```

В третьем терминале из корня репозитория сохраните отчёт среды и проверьте граф:

```bash
mkdir -p evidence/pr01
ros2 doctor --report > evidence/pr01/doctor.txt 2>&1
ros2 node list --no-daemon --spin-time 2
ros2 topic list -t --no-daemon --spin-time 2
ros2 node info /turtlesim --no-daemon --spin-time 2
POSE_TYPE=$(ros2 topic type /turtle1/pose --no-daemon --spin-time 2)
printf '%s\n' "$POSE_TYPE"
ros2 topic echo /turtle1/pose "$POSE_TYPE" --once
ros2 topic hz /turtle1/pose
```

Оставьте замер частоты на 10 секунд или дольше и остановите его через `Ctrl+C`. Запишите длительность и измеренную частоту. Команды движения проходят через `/turtle1/cmd_vel`, а наблюдаемые координаты и скорости приходят в `/turtle1/pose`.

## Проверка изоляции и восстановления

Оставьте симулятор работать в домене 16. Остановите управление через `Ctrl+C` и запустите его в домене 17:

```bash
export ROS_DOMAIN_ID=17
ros2 run turtlesim turtle_teleop_key
```

В терминале наблюдения, где сохранён `POSE_TYPE`, выполните:

```bash
export ROS_DOMAIN_ID=17
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once > evidence/pr01/pose-broken.txt 2>&1
printf 'exit=%s\n' "$?"
```

За пять секунд поза поступить не должна. При истечении таймаута команда завершится с кодом `124`.

Остановите управление и перезапустите его после `export ROS_DOMAIN_ID=16`. В терминале наблюдения поменяйте домен и повторите проверку:

```bash
export ROS_DOMAIN_ID=16
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once > evidence/pr01/pose-fixed.txt 2>&1
printf 'exit=%s\n' "$?"
```

Ожидаемые результаты — обе ноды в списке, сообщение позы и код `0`. Проверьте стрелками, что управление вернулось.

## Проверка отчёта

Команды и результаты опыта находятся в [`evidence/pr01/graph.md`](evidence/pr01/graph.md). CI загружает course kit `v1-w12`, проверяет контрольную сумму архива и запускает checker с полной историей Git. С тем же комплектом, распакованным в `.course-kit/`, локальная проверка выполняется из корня репозитория:

```bash
python3 -m json.tool evidence/pr01/environment.json > /dev/null
python3 -m json.tool evidence/pr01/report.json > /dev/null
python3 .course-kit/v1/tools/check_practice.py PR01 --submission .
```
