# Частота и параметры ноды patrol

Измерения выполнены в ROS 2 Lyrical. Симулятор работал с платформой Qt `offscreen`. Для рабочего опыта использован домен 184, для версии со сбоем — 185. Топик позы объявлен как `turtlesim_msgs/msg/Pose`. В обоих опытах выход `cmd_vel` переназначен в `/turtle1/cmd_vel`.

## Настройки и таймер

| Имя | Начальное значение | Допустимые значения |
| --- | ---: | ---: |
| `linear_speed` | 0.5 м/с | от 0 до 1 м/с |
| `turn_rate` | 0.3 рад/с | от −1 до 1 рад/с |
| `publish_hz` | 10.0 Гц | от 1 до 30 Гц |

Для каждой транзакции собирается предложенный набор параметров. Проверка выполняется до его принятия. Смену таймера выполняет обработчик принятого изменения: новый таймер создаётся остановленным, предыдущий отменяется и удаляется, затем запускается новый. Для 10 Гц период равен 100 мс, для 5 Гц — 200 мс. После изменения только скоростей таймер остаётся тем же.

## Изменение частоты в работающем графе

```console
$ ros2 param get /patrol publish_hz
Double value is: 10.0
$ ros2 param set /patrol publish_hz 5.0
Set parameter successful
$ ros2 param get /patrol publish_hz
Double value is: 5.0
$ ros2 param set /patrol publish_hz 0.0
Setting parameter failed: publish_hz needs a finite number in [1.0, 30.0]
$ ros2 param get /patrol publish_hz
Double value is: 5.0
```

Каждый замер запускался командой `timeout --signal=INT 7s ros2 topic hz /turtle1/cmd_vel --window 25`. Указано последнее среднее из вывода CLI.

| Момент | Значение параметра | Измеренная частота |
| --- | ---: | ---: |
| После запуска | 10.0 | 10.000 Гц |
| После принятия 5.0 | 5.0 | 5.000 Гц |
| После отклонения 0.0, −1.0 и NaN | 5.0 | 4.999 Гц |

Для NaN в CLI передано `.nan`. После отрицательного и нечислового значений параметр тоже оставался равен 5.0. Полный вывод находится в [fixed-commands.md](fixed-commands.md).

Команды `ros2 param set /patrol linear_speed 0.8` и `ros2 param set /patrol turn_rate -0.5` приняты. Из нового сообщения `Twist` подтверждены `linear.x = 0.8` и `angular.z = -0.5`.

## Воспроизведение и регрессионный тест

В отдельной ветке `pr04-defect` на коммите `9606ca4a5847` из проверки намеренно исключён диапазон `publish_hz`. Изменение описано в [defect.patch](defect.patch), его база — `bc6ed7c3ac71`. Сначала была принята частота 5 Гц. Затем тот же вызов `ros2 param set /patrol publish_hz 0.0` завершил процесс `patrol` с кодом 1. Деление `1.0 / proposed.publish_hz` в обработчике принятого изменения выбросило `ZeroDivisionError`. Вывод клиента и трассировка сохранены в [broken-commands.md](broken-commands.md) и [логе patrol](broken-commands-patrol.txt).

Одинаковый тест запущен в двух рабочих деревьях после сборки и подключения ROS:

```bash
python3 -m pytest 'src/patrol/test/test_node_parameters.py::test_rejected_frequency_preserves_timer[0.0]' -q
```

В изменённой версии он упал на делении на ноль. В рабочей версии он прошёл и подтвердил сохранение значения 5.0, того же таймера и периода 200 мс. См. [вывод для версии со сбоем](regression-before.txt) и [вывод для рабочей версии](regression-after.txt).

## Сервис и действие

```console
$ ros2 service call /clear std_srvs/srv/Empty '{}'
std_srvs.srv.Empty_Response()
$ ros2 action list -t
/turtle1/rotate_absolute [turtlesim_msgs/action/RotateAbsolute]
```

Запрос к сервису `/clear` запускает одну операцию очистки и возвращает один ответ. Цель действия `rotate_absolute` задаёт операцию поворота, во время которой сервер может передавать обратную связь, принять отмену и вернуть результат по завершении.

Полная проверка собрала оба пакета и выполнила 38 тестов `patrol`. [Лог сборки и тестов](tests.txt).
