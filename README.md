# ПР04. Настройка скорости и частоты patrol

Пакет `patrol` из ПР03 теперь принимает параметры ROS 2 во время работы. Подписка по-прежнему хранит последнюю позу, а до её получения таймер отправляет нулевой `Twist`.

| Параметр | По умолчанию | Допустимый диапазон |
| --- | ---: | ---: |
| `linear_speed` | 0.5 м/с | 0–1 м/с |
| `turn_rate` | 0.3 рад/с | −1–1 рад/с |
| `publish_hz` | 10.0 Гц | 1–30 Гц |

Нода сначала проверяет предложенные значения. Для принятой частоты она готовит новый таймер, останавливает старый и запускает новый. Отклонённое предложение оставляет прежние значения и поток команд.

## Сборка и тесты

Из корня проекта в ROS 2 Lyrical:

```bash
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
python3 -m pytest src/patrol/test
```

## Демонстрация в трёх терминалах

В каждом терминале перейдите в корень проекта и подключите окружение. Выберите свободный домен и используйте его во всех терминалах.

```bash
source /opt/ros/lyrical/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=184
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
```

В первом запустите `ros2 launch turtle_bringup sim.launch.py`. Во втором запустите контроллер с переназначением команды на топик симулятора:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

В третьем терминале проверьте исходную частоту. Прервите каждый запуск `ros2 topic hz` после нескольких секунд измерения.

```bash
ros2 param get /patrol publish_hz
ros2 topic hz /turtle1/cmd_vel
ros2 param set /patrol publish_hz 5.0
ros2 topic hz /turtle1/cmd_vel
ros2 param set /patrol publish_hz 0.0
ros2 param get /patrol publish_hz
ros2 topic hz /turtle1/cmd_vel
```

После успешной смены частоты ожидается около 5 Гц. Запрос с `0.0` возвращает отказ, а следующий замер снова показывает около 5 Гц.

```bash
ros2 param set /patrol linear_speed 0.8
ros2 param set /patrol turn_rate -0.5
ros2 topic echo /turtle1/cmd_vel geometry_msgs/msg/Twist --once
ros2 service call /clear std_srvs/srv/Empty '{}'
ros2 action list -t
```

## Повторение проверок

Для автоматического опыта остановите ручные запуски. Сценарий сам поднимет симулятор без окна и сохранит команды и вывод. Checker запускается из корня проекта после распаковки course kit в `.course-kit/`.

```bash
ROS_DOMAIN_ID=184 python3 tools/record_pr04.py --output /tmp/pr04-demo/commands.md
python3 .course-kit/v1/tools/check_practice.py PR04 --submission .
```

Сравнение исправной и временно изменённой версий, результаты измерений и команды собраны в [parameters.md](evidence/pr04/parameters.md).
