# Сообщения в графе turtlesim

| Топик | Тип в ROS 2 Lyrical | Роль |
| --- | --- | --- |
| `/turtle1/cmd_vel` | `geometry_msgs/msg/Twist` | CLI публикует скорость, а `/turtlesim` её принимает |
| `/turtle1/pose` | `turtlesim_msgs/msg/Pose` | `/turtlesim` публикует координаты `x`, `y`, ориентацию `theta` и текущие скорости |

По выводу `ros2 interface show geometry_msgs/msg/Twist` сообщение содержит два вектора `Vector3`: `linear` с линейной скоростью и `angular` с угловой. У каждого вектора есть компоненты `x`, `y` и `z`.

В опыте `linear.x = 1.0` задаёт движение вдоль продольной оси черепахи. `angular.z = 0.5` задаёт вращение вокруг оси, перпендикулярной плоскости симулятора. Остальные компоненты команды равны нулю. Угол `theta` и величина `angular_velocity` в позе выражаются в радианах и радианах в секунду соответственно.

В ROS 2 Jazzy тип позы называется `turtlesim/msg/Pose`. Для `ros2 topic echo` используйте тип, возвращённый `ros2 topic type /turtle1/pose` в вашей среде.
