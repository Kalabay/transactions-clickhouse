# Домашка 2

Калабай Михаил Иванович

TLDR 
Отправляем транзакции из csv в kafka, дальше в ClickHouse. Ну и запросом находим категорию самой большой транзакции в каждом штате.

## Как запускать это

Как и в прошлой дз у меня Docker Desktop с WSL 2 и линукс контейнерами. Использую порт 8124

Берём `test.csv` из Kaggle и кладём в папку `data`. Сам CSV в репозиторий я не добавлял

В терминале из папки проекта:

```
docker compose --profile tools build
docker compose up -d
docker compose ps -a
```
Как все сетапы закончатся загружаем данные и запускаем проверку:

```bash
docker compose run --rm tools python send.py
docker compose run --rm tools python check.py
```

Затем строки должны отправится. Ответ будет в `results/answer.csv`: штат, категория и сумма (см. результат в самом конце). Получилось 51 значение по итогу

## Три варианта того, что запускал

Оставил все три, чтобы сравнить на одинаковых данных

| Вариант | Таблицы | Запрос |
| --- | --- | --- |
| Обычный | `sql/tables.sql` | `sql/query_old.sql` |
| Оптимизация | `sql/fast.sql` | `sql/query.sql` |
| Читерский предварительный расчёт      | `sql/max.sql` | `sql/query_max.sql` |

Во втором варианте для штата и категории поставил `LowCardinality`, сортировку по `(us_state, cat_id)` и сжатие `ZSTD(1)`

В третьем оптимизация плюс максимумы считаются при поступлении данных из второй таблицы. Для этого добавил `AggregatingMergeTree`, `maxState` и `maxMerge`. Понятное дело не надо каждый раз перебирать все транзакции, он объединяет уже посчитанные максимумы, для этого хранится отдельная таблица под этот запрос, зато это самый шустрый вариант (см. сравнение ниже)

## Что получилось по таймингам

| Вариант | Медиана времени | Медиана пиковой RAM запроса, МБ |
| --- | --- | --- |
| Обычный | 12 мс | 10.18 |
| Оптимизация | 11 мс | 5.45 |
| Читерский предварительный расчёт | 2 мс | 5.43 |

Это 10 замеров каждого запроса после прогрева, два потока, query cache выключен. На этом запуске получилось примерно в 6 раз быстрее исходного. Все три результата понятное дело совпали. Читерский предварительный расчёт оказался самым выгодным по времени. Оптимизация из лекции уменьшила RAM (с 10 до примерно 5,5 МБ).

## Ответ

| Штат | Категория | Сумма |
| --- | --- | --- |
| AK | shopping_net | 1099.67 |
| AL | travel | 4154.78 |
| AR | travel | 3579.08 |
| AZ | shopping_pos | 2393.29 |
| CA | travel | 9861.17 |
| CO | travel | 8217.23 |
| CT | travel | 8266.86 |
| DC | shopping_net | 1201.86 |
| DE | shopping_net | 1012.77 |
| FL | travel | 9995.78 |
| GA | travel | 11960.97 |
| HI | misc_pos | 1477.41 |
| IA | travel | 6934.27 |
| ID | shopping_pos | 1144.02 |
| IL | travel | 3774.18 |
| IN | misc_net | 2863.71 |
| KS | travel | 3436.85 |
| KY | shopping_pos | 3593.23 |
| LA | shopping_net | 3718.83 |
| MA | shopping_net | 3833.36 |
| MD | travel | 6665.34 |
| ME | shopping_pos | 3598.04 |
| MI | shopping_pos | 4248.63 |
| MN | shopping_net | 1694.21 |
| MO | travel | 4530.58 |
| MS | shopping_pos | 2673.07 |
| MT | travel | 2589.22 |
| NC | shopping_pos | 7747.73 |
| ND | shopping_pos | 2194.79 |
| NE | travel | 28948.9 |
| NH | travel | 1242.41 |
| NJ | travel | 4551.94 |
| NM | travel | 3343.52 |
| NV | shopping_net | 1077.27 |
| NY | shopping_net | 4951.14 |
| OH | travel | 3923.87 |
| OK | travel | 4029.6 |
| OR | shopping_net | 4982.7 |
| PA | shopping_pos | 4180.78 |
| RI | travel | 11629.34 |
| SC | travel | 8255.19 |
| SD | travel | 4284.52 |
| TN | shopping_pos | 2929.92 |
| TX | travel | 15047.03 |
| UT | shopping_net | 5801.49 |
| VA | shopping_net | 3904.95 |
| VT | shopping_pos | 4522.11 |
| WA | shopping_net | 3026.86 |
| WI | shopping_net | 5122.54 |
| WV | travel | 6527.88 |
| WY | misc_pos | 2165.99 |
