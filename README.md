# ПР05. Запуск patrol, QoS и повтор MCAP

`course_bringup` запускает один `/turtlesim` и ноды `patrol`, `pose_relay` и `pose_subscriber` в заданном пространстве имён. При стандартном `namespace:=robot_a` реле получает глобальную позу `/turtle1/pose` и публикует её в `/robot_a/sensor_pose` с `best_effort`. Команда движения от `patrol` переназначена на `/turtle1/cmd_vel`.

| Аргумент запуска | По умолчанию | Назначение |
| --- | --- | --- |
| `namespace` | `robot_a` | Пространство имён трёх нод работы |
| `record` | `false` | Запустить recorder только при `true` |
| `bag_dir` | `pr05-bag` | Новый каталог записи MCAP |
| `subscriber_reliability` | `best_effort` | Запрошенная надёжность подписчика |

## Сборка

Из корня проекта в ROS 2 Lyrical:

```bash
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test --packages-select patrol course_bringup --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose
```

В каждом терминале опыта подключите ту же базовую ROS и `install/setup.bash`, работайте из корня проекта и используйте один свободный домен, например `196`. Остановите старые запуски симулятора, контроллера и плеера.

```bash
export ROS_DOMAIN_ID=196
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
```

## Сравнение профилей на живом потоке

В первом терминале запустите несовместимый профиль:

```bash
ros2 launch course_bringup patrol.launch.py namespace:=robot_a record:=false subscriber_reliability:=reliable
```

Во втором подтвердите, что топик обнаружен. `reliable`-подписчик запрашивает гарантию, которую издатель `best_effort` не предлагает. Через три секунды `timeout` должен вернуть `124`.

```bash
ros2 topic info /robot_a/sensor_pose --verbose --no-daemon --spin-time 2
timeout 3s ros2 topic echo /robot_a/sensor_pose turtlesim_msgs/msg/Pose --once --qos-reliability reliable
printf 'exit=%s\n' "$?"
```

Остановите первый запуск и замените профиль подписчика. Укажите свободное имя каталога записи.

```bash
ros2 launch course_bringup patrol.launch.py namespace:=robot_a record:=true bag_dir:=pr05-bag subscriber_reliability:=best_effort
```

Второй терминал должен получить сообщение, а счётчик подписчика в первом начнёт расти.

```bash
timeout 3s ros2 topic echo /robot_a/sensor_pose turtlesim_msgs/msg/Pose --once --qos-reliability best_effort
```

Дайте recorder поработать несколько секунд и завершите launch через `Ctrl+C`, чтобы сохранить метаданные.

## Повтор записи

Проверьте состав и запустите повтор в первом терминале:

```bash
ros2 bag info pr05-bag
ros2 bag play pr05-bag --loop --qos-profile-overrides-path config/qos-overrides.yaml
```

Во втором терминале повторите обе команды `echo` с теми же профилями. На одном и том же MCAP `reliable` снова ждёт до таймаута, а `best_effort` получает позу.

## Проверки и результаты

Автоматический опыт повторяет обе проверки QoS и создаёт запись в новом каталоге. Живой симулятор в нём работает без окна.

```bash
ROS_DOMAIN_ID=196 python3 tools/record_pr05.py --output "$(mktemp -d)/run"
python3 .course-kit/v1/tools/check_practice.py PR05 --submission .
```

Для сдачи сохранены [вывод с таймаутами](evidence/pr05/qos-before.txt), [вывод с доставкой](evidence/pr05/qos-after.txt), [метаданные](evidence/pr05/bag-metadata.yaml) и [один MCAP](evidence/pr05/bag/).
