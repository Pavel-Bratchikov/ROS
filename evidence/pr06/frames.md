# Карта преобразований Ackermann-робота

Проверка выполнена на ROS 2 Lyrical. Модель содержит 12 звеньев и 11 сочленений. Корень дерева — `base_footprint`, а удобная для осмотра система координат RViz — `base_link`. Оси корпуса направлены вперёд, влево и вверх. У оптического фрейма камера смотрит вдоль Z, ось X направлена вправо, ось Y — вниз.

Таблица задаёт смещение и углы дочерней системы в родительской. Для подвижных сочленений указана поза при нулевых углах. Издатель `/joint_states` передаёт углы, а преобразования обоих типов публикует одна нода.

| Родитель | Дочерний фрейм | XYZ, м | RPY, рад | Топик | Владелец |
| --- | --- | --- | --- | --- | --- |
| `base_footprint` | `base_link` | (0, 0, 0.12) | (0, 0, 0) | `/tf_static` | `/robot_state_publisher` |
| `base_link` | `camera_link` | (0.28, 0, 0.38) | (0, 0, 0) | `/tf_static` | `/robot_state_publisher` |
| `camera_link` | `camera_optical_frame` | (0.08, 0, 0) | (-1.57, 0, -1.57) | `/tf_static` | `/robot_state_publisher` |
| `base_link` | `imu_link` | (0.28, 0, 0.38) | (0, 0, 0) | `/tf_static` | `/robot_state_publisher` |
| `base_link` | `lidar_link` | (0.28, 0, 0.38) | (0, 0, 0) | `/tf_static` | `/robot_state_publisher` |
| `base_link` | `front_left_knuckle` | (0.4, 0.31, 0) | (0, 0, 0) | `/tf` | `/robot_state_publisher` |
| `front_left_knuckle` | `front_left_wheel` | (0, 0, 0) | (0, 0, 0) | `/tf` | `/robot_state_publisher` |
| `base_link` | `front_right_knuckle` | (0.4, -0.31, 0) | (0, 0, 0) | `/tf` | `/robot_state_publisher` |
| `front_right_knuckle` | `front_right_wheel` | (0, 0, 0) | (0, 0, 0) | `/tf` | `/robot_state_publisher` |
| `base_link` | `rear_left_wheel` | (-0.4, 0.31, 0) | (0, 0, 0) | `/tf` | `/robot_state_publisher` |
| `base_link` | `rear_right_wheel` | (-0.4, -0.31, 0) | (0, 0, 0) | `/tf` | `/robot_state_publisher` |

## Как проверено дерево

Минимальная версия из корпуса и лидара успешно запустилась и вернула `[0.280, 0.000, 0.380]` в `tf2_echo`. После проверки минимальной связи выполнен полный запуск модели. Реальные команды и вывод: [минимальный запуск](minimal.txt), [полная проверка](model-check.txt), [дерево view_frames](frames.pdf).

При `joint_states` с шестью нулевыми углами в `/tf` наблюдались все шесть подвижных связей. RViz показал модель при Fixed Frame `base_link`. На [снимке окна](rviz.png) Global Status и RobotModel имеют статус `Ok`.

## Поздняя подписка

У единственного издателя `/tf_static` QoS `RELIABLE` и `TRANSIENT_LOCAL`. Поздний подписчик с `transient_local` получил пять преобразований с кодом `0`. Запрос с `volatile` на тот же топик завершился с кодом `124`, потому что при стабильной модели новых сообщений после подписки не было. Подвижные связи идут в `/tf` с `VOLATILE` и обновляются при новых углах. [Вывод CLI](tf-qos.txt).

## Ошибка parent у lidar_link

Для опыта в отдельной ветке `pr06-defect` изменён только родитель `lidar_joint` с `base_link` на `camera_link`. Смещение `(0.28, 0, 0.38)` осталось прежним. Поэтому к смещению лидара добавилось такое же смещение камеры, и `tf2_echo base_link lidar_link` измерил `[0.560, 0.000, 0.760]`. `check_urdf` принял обе структуры. В рабочей версии измерение вернулось к `[0.280, 0.000, 0.380]` м.

| Вариант | Родитель | XYZ от base_link, м | check_urdf | test_lidar_parent |
| --- | --- | --- | --- | --- |
| Ошибочный | `camera_link` | 0.560, 0.000, 0.760 | прошёл | упал |
| Рабочий | `base_link` | 0.280, 0.000, 0.380 | прошёл | прошёл |

Сохранены [однострочный патч](defect.patch), [ошибочное дерево](defect/frames.pdf), [результат tf2_echo в копии](defect/model-check.txt) и одна и та же проверка parent [до](regression-before.txt) и [после](regression-after.txt). Исправный Xacro находится в коммите `2889a68403cc`, копия с ошибкой — в `4cfbc3a5257f`.
