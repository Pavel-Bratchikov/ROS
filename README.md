# ПР02. Пакет и запуск turtlesim

Пакет `turtle_bringup` устанавливает `sim.launch.py`. Этот файл запускает один экземпляр `turtlesim`. Через CLI можно проверить, как полное имя топика влияет на доставку команды скорости.

## Сборка и запуск

Откройте Bash в корне репозитория и подключите базовую среду ROS 2. Для ROS 2 Jazzy используйте `/opt/ros/jazzy/setup.bash`.

```bash
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install --packages-select turtle_bringup
```

В отдельном терминале из корня проекта подключите базовую среду и собранный workspace. Сначала остановите предыдущие экземпляры `turtlesim` и `teleop`. Подставьте свой `ROS_DOMAIN_ID`, если на занятии назначен другой номер.

```bash
source /opt/ros/lyrical/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 pkg prefix turtle_bringup
ls "$(ros2 pkg prefix turtle_bringup)/share/turtle_bringup/launch"
ros2 launch turtle_bringup sim.launch.py
```

Из другого терминала с той же средой и доменом проверьте появление `/turtlesim` через `ros2 node list --no-daemon --spin-time 2`. Нажмите `Ctrl+C` в терминале запуска и повторите проверку списка нод. Для опыта запустите симулятор ещё раз.

## Передача команды из терминала

Посмотрите начальную позу и структуру команды скорости. В новом терминале заранее подключите ROS и задайте те же `ROS_DOMAIN_ID` и `ROS_AUTOMATIC_DISCOVERY_RANGE`, что у симулятора.

```bash
ros2 interface show geometry_msgs/msg/Twist
POSE_TYPE=$(ros2 topic type /turtle1/pose --no-daemon --spin-time 2)
ros2 topic echo /turtle1/pose "$POSE_TYPE" --once
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
ros2 topic echo /turtle1/pose "$POSE_TYPE" --once
```

В отдельном терминале с теми же настройками запустите непрерывную публикацию в `/cmd_vel`:

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Пока издатель активен, сравните конечные точки и посмотрите позу:

```bash
ros2 topic info /cmd_vel --verbose --no-daemon --spin-time 2
ros2 topic info /turtle1/cmd_vel --verbose --no-daemon --spin-time 2
ros2 topic echo /turtle1/pose "$POSE_TYPE" --once
```

Остановите издателя и запустите ту же команду публикации с именем `/turtle1/cmd_vel`. Теперь у издателя появляется подписчик `/turtlesim`, а поза меняется. Остановите публикацию через `Ctrl+C`. Если ноды или конечные точки ещё не видны, подождите обнаружения DDS и повторите команду просмотра.

## Отчёт и проверка

[Команды и наблюдения](evidence/pr02/commands.md) содержат логи опыта. [Типы сообщений](evidence/pr02/types.md) описывают поля скорости и позы. В GitHub Actions пакет собирается в ROS 2 Lyrical, затем проверяются установленный launch-файл и отчёт.

```bash
python3 -m py_compile src/turtle_bringup/launch/sim.launch.py
python3 .course-kit/v1/tools/check_practice.py PR02 --submission .
```
