# Запуск пакета и проверка доставки Twist

Опыт выполнялся в ROS 2 Lyrical, домен 16, область обнаружения `LOCALHOST`. В выводе ниже `<workspace>` обозначает корень репозитория. Для повторяемого замера симулятор запускался с Qt `offscreen`, а поза считывалась через ROS CLI.

## Навигация и среда Bash

| Команда | Зачем применялась | Полученный результат |
| --- | --- | --- |
| `pwd` | Проверить текущий каталог перед вызовом colcon | Корень workspace `<workspace>` |
| `ls -a` | Найти скрытые каталоги и убедиться, что это корень репозитория | Среди записей видны `.git`, `.github`, `src` и `evidence` |
| `printenv ROS_DISTRO ROS_DOMAIN_ID` | Узнать выбранную среду и домен запуска | `lyrical`, `16` |

`>` перенаправляет stdout в файл и заменяет его содержимое. `|` передаёт stdout одной команды на stdin другой. Здесь `tee` отправляет результат и на экран, и в файл. `2>&1` включает stderr в тот же поток, а `set -o pipefail` сохраняет ошибку сборки в коде возврата всего конвейера.

`source /opt/ros/lyrical/setup.bash` выполняет сценарий в текущем Bash. Поэтому переменные и пути ROS остаются в этом терминале. Отдельная дочерняя программа получает собственное окружение и не меняет окружение родительской оболочки.

## Сборка и установка

До появления `launch/` выполнилась сборка пустого пакета:

```bash
set -o pipefail
colcon build --symlink-install --packages-select turtle_bringup 2>&1 | tee evidence/pr02/build-empty.txt
source install/setup.bash
ros2 pkg prefix turtle_bringup
```

Получен путь `<workspace>/install/turtle_bringup`. Пустой пакет уже был в индексе, но sim.launch.py в нём ещё не было. `ros2 pkg prefix turtlesim` показывал установленную базовую ROS в `/opt/ros/lyrical`.

После добавления launch и правила установки в `setup.py`:

```console
$ colcon build --symlink-install --packages-select turtle_bringup 2>&1 | tee evidence/pr02/build.txt
$ source install/setup.bash
$ ros2 pkg prefix turtle_bringup
<workspace>/install/turtle_bringup
$ ls "$(ros2 pkg prefix turtle_bringup)/share/turtle_bringup/launch"
__pycache__
sim.launch.py
```

Обе сборки завершились успешно. Наличие файла в `share/turtle_bringup/launch` позволяет найти его по имени пакета.

## Запуск и остановка

```console
$ ros2 launch turtle_bringup sim.launch.py
[INFO] [turtlesim_node-1]: process started with pid [60697]
[INFO] [turtlesim_node-1]: process has finished cleanly [pid 60697]
```

До запуска список `ros2 node list --no-daemon --spin-time 2` был пуст. Во время запуска в нём появилась `/turtlesim`. После сигнала SIGINT, который соответствует `Ctrl+C`, процесс симулятора завершился, launch вернул код `0`, список снова был пуст. Для измерения позы launch был запущен повторно.

## Команда движения

```console
$ ros2 topic type /turtle1/pose --no-daemon --spin-time 2
turtlesim_msgs/msg/Pose
$ ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Положительный `linear.x` задаёт движение вперёд, а положительный `angular.z` поворачивает черепаху против часовой стрелки. Каждая поза была прочитана отдельным вызовом:

```bash
timeout 7s ros2 topic echo /turtle1/pose turtlesim_msgs/msg/Pose --once
```

| Момент замера | x | y | theta |
| --- | ---: | ---: | ---: |
| Старт | `5.544445` | `5.544445` | `0.000000` |
| После разовой команды | `6.509309` | `5.796991` | `0.504000` |
| Публикация в `/cmd_vel` | `6.509309` | `5.796991` | `0.504000` |
| После исправления имени и остановки издателя | `5.794906` | `9.527668` | `3.008000` |

Разовая команда сдвинула и повернула черепаху. После прекращения команд симулятор остановил движение.

## Сбой и повторная проверка

Сначала издатель работал с именем `/cmd_vel`. Флаг `--wait-matching-subscriptions 0` позволяет отправлять сообщение без совпавших подписчиков.

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Проверка конечных точек в другом терминале дала:

```console
$ ros2 topic info /cmd_vel --verbose --no-daemon --spin-time 2
Type: geometry_msgs/msg/Twist
Publisher count: 1
Node name: _ros2cli_60967
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

Издатель отправлял сообщения в `/cmd_vel`, но неподвижная черепаха сохранила все три координаты. После `Ctrl+C` команда была повторена с одним изменением — полным именем топика.

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 /turtle1/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

```console
$ ros2 topic info /turtle1/cmd_vel --verbose --no-daemon --spin-time 2
Type: geometry_msgs/msg/Twist
Publisher count: 1
Node name: _ros2cli_61097
Node namespace: /
Endpoint type: PUBLISHER
Subscription count: 1
Node name: turtlesim
Node namespace: /
Endpoint type: SUBSCRIPTION
```

В графе появились один издатель и один подписчик, `/turtlesim`. Координаты снова изменились. Обнаружение издателя показывает, что его конечная точка существует. Для доставки требуются совпадающие полное имя и тип топика, а также совместимый QoS. Тип `geometry_msgs/msg/Twist` в обоих запусках был одинаковым, но имена `/cmd_vel` и `/turtle1/cmd_vel` обозначают разные топики.
