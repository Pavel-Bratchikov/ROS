# ПР06. Описание Ackermann-робота и дерево tf2

Пакет `course_description` разворачивает Xacro и передаёт URDF в `robot_state_publisher`. Размеры корпуса и колёс взяты из SDF курса. Оси корпуса следуют REP-103: вперёд по X, влево по Y, вверх по Z.

| Аргумент launch | Значение по умолчанию | Что меняется |
| --- | ---: | --- |
| `wheelbase` | 0.80 м | Расстояние между осями |
| `track` | 0.62 м | Расстояние между центрами левого и правого колёс |
| `wheel_radius` | 0.12 м | Радиус колеса и высота `base_link` над `base_footprint` |
| `rviz` | `true` | Запуск RViz с готовой конфигурацией |

## Сборка и запуск

Распакуйте course kit в `.course-kit/`. Из корня workspace в ROS 2 Lyrical выполните:

```bash
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
source install/setup.bash
xacro src/course_description/urdf/vehicle.urdf.xacro -o /tmp/vehicle.urdf
check_urdf /tmp/vehicle.urdf
colcon test --packages-select course_description --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose --test-result-base build/course_description
```

Подключите окружение ROS и `install/setup.bash` в каждом терминале. Задайте один свободный домен, остановите прежние экземпляры `robot_state_publisher` и запустите модель:

```bash
export ROS_DOMAIN_ID=201
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 launch course_description description.launch.py
```

В конфигурации RViz Fixed Frame задан как `base_link`. Для запуска только издателя преобразований добавьте `rviz:=false`. Фиксированные звенья появляются сразу. Чтобы в RViz также появились колёса и поворотные кулаки, во втором терминале подайте начальные углы:

```bash
ros2 topic pub -r 10 /joint_states sensor_msgs/msg/JointState \
  '{header: auto, name: [front_left_steering_joint, front_right_steering_joint, front_left_wheel_joint, front_right_wheel_joint, rear_left_wheel_joint, rear_right_wheel_joint], position: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}'
```

## Проверка связей и QoS

```bash
ros2 run tf2_ros tf2_echo base_link lidar_link
```

Смещение исправного лидара от корпуса равно `(0.28, 0, 0.38)` м. Завершите `tf2_echo` через `Ctrl+C`, проверьте дерево и подписки:

```bash
ros2 run tf2_tools view_frames --output /tmp/pr06-frames
ros2 topic info /tf_static --verbose --no-daemon --spin-time 2
timeout 4s ros2 topic echo /tf_static tf2_msgs/msg/TFMessage --once \
  --qos-reliability reliable --qos-durability transient_local
printf 'exit=%s\n' "$?"
timeout 4s ros2 topic echo /tf_static tf2_msgs/msg/TFMessage --once \
  --qos-reliability reliable --qos-durability volatile
printf 'exit=%s\n' "$?"
```

Поздняя подписка с `transient_local` читает сохранённые преобразования и завершает команду с кодом `0`. Для того же издателя `volatile` ждёт только новые сообщения, поэтому при неизменной модели ожидается код `124`.

## Материалы проверки

[Таблица фреймов](evidence/pr06/frames.md), [профили TF](evidence/pr06/tf-qos.txt) и [вывод проверок модели](evidence/pr06/model-check.txt) фиксируют результаты. В отдельной копии смена родителя `lidar_link` на `camera_link` оставляет дерево структурно корректным, но удваивает смещение по X и Z.

После остановки ручных запусков автоматический опыт можно повторить из нового каталога. Флаг `--rviz` дополнительно сохраняет PNG окна и требует дисплея X11 (например, `xvfb-run`).

```bash
ROS_DOMAIN_ID=204 python3 tools/record_pr06.py --output "$(mktemp -d)/run"
python3 .course-kit/v1/tools/check_practice.py PR06 --submission .
```
