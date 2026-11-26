# ПР03. Управление turtlesim из ноды patrol

`patrol` подписывается на `/turtle1/pose` и раз в 0,1 с отправляет `geometry_msgs/msg/Twist` в относительный `cmd_vel`. До первого сообщения позы скорость равна нулю. После него нода задаёт `linear.x = 0.5` и `angular.z = 0.3`.

## Сборка и тесты

Для ROS 2 Lyrical выполните из корня проекта:

```bash
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
python3 -m pytest src/patrol/test
```

В каждом терминале демонстрации подключите ROS 2 и установленный workspace. Используйте один домен во всех трёх терминалах и остановите старые экземпляры симулятора, `teleop` и `patrol`.

```bash
source /opt/ros/lyrical/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
```

## Запуск и проверка связи

В первом терминале запустите симулятор:

```bash
ros2 launch turtle_bringup sim.launch.py
```

Во втором запустите `patrol` со стандартным именем выходного топика:

```bash
ros2 run patrol patrol
```

В третьем терминале сравните конечные точки:

```bash
ros2 node list --no-daemon --spin-time 2
ros2 topic type /turtle1/pose --no-daemon --spin-time 2
ros2 topic info /turtle1/pose --verbose --no-daemon --spin-time 2
ros2 topic info /cmd_vel --verbose --no-daemon --spin-time 2
ros2 topic info /turtle1/cmd_vel --verbose --no-daemon --spin-time 2
```

В корневом namespace относительное имя `cmd_vel` становится `/cmd_vel`, тогда как симулятор слушает `/turtle1/cmd_vel`. Остановите `patrol` через `Ctrl+C` и запустите его снова с переназначением:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

В терминале наблюдения проверьте появление издателя и измерьте частоту:

```bash
ros2 topic info /turtle1/cmd_vel --verbose --no-daemon --spin-time 2
timeout --signal=INT 13s ros2 topic hz /turtle1/cmd_vel
```

Если конечные точки пока не видны, дайте DDS несколько секунд на обнаружение и повторите запрос. После остановки `patrol` дождитесь, пока симулятор перестанет использовать последнюю команду скорости.

## Результаты

Команды, измерения и объяснение опыта приведены в [demo.md](evidence/pr03/demo.md). Вывод тестов находится в [tests.txt](evidence/pr03/tests.txt). Локальная проверка отчёта из распакованного course kit:

```bash
python3 .course-kit/v1/tools/check_practice.py PR03 --submission .
```
