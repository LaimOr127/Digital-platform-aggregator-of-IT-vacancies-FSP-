"""Общие задания для всех специализаций: алгоритмы, структуры данных, SQL, git, архитектура."""

import math
import random
from collections import deque

from app.services.assessment.items import (
    COMMON,
    Item,
    choice,
    computed,
    number,
    numeric,
    statements,
)

ALL = (COMMON,)


# --- уровень 1 ------------------------------------------------------------------------------
@computed("common.loop-sum", 1, "Циклы", ALL, ("python", "algorithms"))
def loop_sum(rng: random.Random) -> Item:
    start, stop, step = rng.randint(0, 5), rng.randint(12, 30), rng.randint(2, 4)
    code = f"s = 0\nfor i in range({start}, {stop}, {step}):\n    s += i\nprint(s)"
    return numeric("Что выведет код?", sum(range(start, stop, step)), code)


@computed("common.slice", 1, "Срезы списков", ALL, ("python",))
def list_slice(rng: random.Random) -> Item:
    data = rng.sample(range(10, 99), 8)
    i, j = rng.randint(1, 3), rng.randint(4, 6)
    code = f"a = {data}\nprint(a[{i}:{j}])"
    wrong = [
        str(data[i : j + 1]),
        str(data[i + 1 : j]),
        str(data[i - 1 : j]),
        str(data[i - 1 : j - 1]),
    ]
    return choice(rng, "Что выведет код?", str(data[i:j]), wrong, code)


@computed("common.filter-count", 1, "Условия", ALL, ("python", "algorithms"))
def filter_count(rng: random.Random) -> Item:
    data = [rng.randint(1, 50) for _ in range(10)]
    k, t = rng.choice([3, 4, 5]), rng.randint(30, 45)
    code = f"data = {data}\nprint(sum(1 for v in data if v % {k} == 0 or v > {t}))"
    return numeric("Что выведет код?", sum(1 for v in data if v % k == 0 or v > t), code)


statements(
    "common.git",
    1,
    "Git",
    ALL,
    ("git",),
    true=(
        "git commit сохраняет снимок проиндексированных изменений в локальный репозиторий",
        "git pull — это git fetch и слияние (или rebase) полученных изменений",
        "git add помещает изменения в индекс для следующего коммита",
        "git revert создаёт новый коммит, отменяющий изменения указанного коммита",
    ),
    false=(
        "git commit сразу отправляет изменения на удалённый сервер",
        "git fetch изменяет файлы в рабочей директории",
        "git revert удаляет коммит из истории",
        "ветка в git — это полная копия всех файлов проекта",
        "git clone скачивает только последнюю версию файлов без истории",
        "git stash удаляет незакоммиченные изменения без возможности вернуть",
    ),
)


# --- уровень 2 ------------------------------------------------------------------------------
_SHAPES = (
    ("for i in range(n):\n    for j in range(n):\n        total += i * j", "O(n²)"),
    ("i = 1\nwhile i < n:\n    i *= 2", "O(log n)"),
    ("for i in range(n):\n    for j in range(i):\n        total += j", "O(n²)"),
    ("for i in range(n):\n    j = n\n    while j > 1:\n        j //= 2", "O(n log n)"),
    ("for i in range(n):\n    total += i\nfor j in range(n):\n    total -= j", "O(n)"),
)
_COMPLEXITIES = ("O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)", "O(2ⁿ)")


@computed("common.big-o", 2, "Сложность алгоритмов", ALL, ("algorithms",))
def big_o(rng: random.Random) -> Item:
    code, answer = rng.choice(_SHAPES)
    wrong = rng.sample([c for c in _COMPLEXITIES if c != answer], 3)
    return choice(rng, "Какова временная сложность фрагмента от n?", answer, wrong, code)


@computed("common.sql-having", 2, "SQL: группировка", ALL, ("sql",))
def sql_having(rng: random.Random) -> Item:
    customers = rng.sample(["anna", "boris", "vera", "gleb", "dina"], 4)
    rows = [(rng.choice(customers), rng.randint(1, 9) * 100) for _ in range(9)]
    k = rng.randint(2, 3)
    table = "\n".join(f"('{c}', {a})" for c, a in rows)
    code = (
        f"-- orders(customer, amount):\n{table}\n\n"
        f"SELECT customer FROM orders\nGROUP BY customer\nHAVING COUNT(*) >= {k};"
    )
    groups = {c: sum(1 for x, _ in rows if x == c) for c, _ in rows}
    return numeric("Сколько строк вернёт запрос?", sum(1 for n in groups.values() if n >= k), code)


@computed("common.stack", 2, "Стек", ALL, ("algorithms",))
def stack_ops(rng: random.Random) -> Item:
    ops, stack, popped = [], [], 0
    for _ in range(9):
        if stack and rng.random() < 0.4:
            ops.append("pop()")
            popped += stack.pop()
        else:
            value = rng.randint(1, 20)
            ops.append(f"push({value})")
            stack.append(value)
    if not any(op == "pop()" for op in ops):
        ops.append("pop()")
        popped += stack.pop()
    return numeric(
        "Над пустым стеком выполнили операции по порядку. Чему равна сумма всех извлечённых значений?",
        popped,
        ", ".join(ops),
    )


@computed("common.bits", 2, "Битовые операции", ALL, ("algorithms",))
def bits(rng: random.Random) -> Item:
    a, b = rng.randint(5, 63), rng.randint(5, 63)
    op, value = rng.choice([("&", a & b), ("|", a | b), ("^", a ^ b)])
    return numeric("Что выведет код?", value, f"print({a} {op} {b})")


# --- уровень 3 ------------------------------------------------------------------------------
@computed("common.word-count", 3, "Словари", ALL, ("python", "algorithms"))
def word_count(rng: random.Random) -> Item:
    words = [rng.choice(["api", "db", "ui", "ml", "qa", "ops"]) for _ in range(12)]
    code = (
        f"words = {words}\ncounts = {{}}\nfor w in words:\n    counts[w] = counts.get(w, 0) + 1\n"
        "print(len([w for w, c in counts.items() if c > 1]))"
    )
    repeated = sum(1 for w in set(words) if words.count(w) > 1)
    return numeric("Что выведет код?", repeated, code)


@computed("common.recursion", 3, "Рекурсия", ALL, ("python", "algorithms"))
def recursion(rng: random.Random) -> Item:
    a, b, k, n = rng.randint(0, 2), rng.randint(1, 3), rng.randint(1, 3), rng.randint(5, 7)
    code = (
        f"def f(n):\n    if n == 0:\n        return {a}\n    if n == 1:\n        return {b}\n"
        f"    return f(n - 1) + {k} * f(n - 2)\n\nprint(f({n}))"
    )
    values = [a, b]
    for _ in range(2, n + 1):
        values.append(values[-1] + k * values[-2])
    return numeric("Что выведет код?", values[n], code)


@computed("common.sql-left-join", 3, "SQL: соединения", ALL, ("sql", "postgresql"))
def sql_left_join(rng: random.Random) -> Item:
    users = rng.randint(3, 5)
    orders = [
        rng.randint(1, users + 1) for _ in range(rng.randint(3, 6))
    ]  # user_id, бывают «чужие»
    code = (
        f"-- users: id = 1..{users}\n-- orders(user_id): {orders}\n\n"
        "SELECT u.id, o.user_id\nFROM users u\nLEFT JOIN orders o ON o.user_id = u.id;"
    )
    rows = sum(max(1, orders.count(uid)) for uid in range(1, users + 1))
    return numeric("Сколько строк вернёт запрос?", rows, code)


@computed("common.binary-search", 3, "Бинарный поиск", ALL, ("algorithms",))
def binary_search(rng: random.Random) -> Item:
    n = rng.randint(50, 2_000_000)
    return numeric(
        "Какое наибольшее число шагов (сравнений с серединой) понадобится бинарному поиску "
        f"в отсортированном массиве из {number(n)} элементов?",
        math.floor(math.log2(n)) + 1,
    )


# --- уровень 4 ------------------------------------------------------------------------------
def _grid(rng: random.Random) -> tuple[list[str], int]:
    while True:
        cells = [["#" if rng.random() < 0.28 else "." for _ in range(6)] for _ in range(5)]
        cells[0][0], cells[4][5] = "S", "E"
        distance = _bfs(cells)
        if distance:
            return ["".join(row) for row in cells], distance


def _bfs(cells: list[list[str]]) -> int | None:
    seen, queue = {(0, 0)}, deque([((0, 0), 0)])
    while queue:
        (r, c), d = queue.popleft()
        if cells[r][c] == "E":
            return d
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            ok = 0 <= nr < 5 and 0 <= nc < 6 and cells[nr][nc] != "#"
            if ok and (nr, nc) not in seen:
                seen.add((nr, nc))
                queue.append(((nr, nc), d + 1))
    return None


@computed("common.bfs", 4, "Графы: кратчайший путь", ALL, ("algorithms",))
def bfs_grid(rng: random.Random) -> Item:
    rows, distance = _grid(rng)
    return numeric(
        "Минимальное число шагов от S до E (ходы вверх, вниз, влево, вправо; # — стена)?",
        distance,
        "\n".join(rows),
    )


@computed("common.dp-stairs", 4, "Динамическое программирование", ALL, ("algorithms",))
def dp_stairs(rng: random.Random) -> Item:
    steps, n = rng.choice([(1, 2), (1, 3), (1, 2, 3), (2, 3)]), rng.randint(5, 15)
    ways = [1] + [0] * n
    for i in range(1, n + 1):
        ways[i] = sum(ways[i - s] for s in steps if i - s >= 0)
    allowed = " или ".join(map(str, steps))
    return numeric(
        f"Сколькими способами можно подняться на {n} ступенек, шагая за раз на {allowed}?",
        ways[n],
    )


statements(
    "common.concurrency",
    4,
    "Конкурентность",
    ALL,
    ("algorithms", "system-design"),
    true=(
        "Взаимная блокировка возможна, когда потоки захватывают блокировки в разном порядке",
        "Операция i += 1 над общей переменной без синхронизации может терять обновления",
        "Оптимистическая блокировка проверяет версию данных при записи, а не блокирует их при чтении",
        "Неизменяемые объекты можно безопасно читать из нескольких потоков без блокировок",
    ),
    false=(
        "Взаимная блокировка невозможна, если потоков всего два",
        "Добавление volatile или atomic к любой переменной делает весь алгоритм потокобезопасным",
        "Состояние гонки возникает только на многопроцессорных машинах",
        "Оптимистическая блокировка не позволяет двум транзакциям прочитать одну строку",
        "Чем больше блокировок, тем выше производительность параллельного кода",
    ),
)


statements(
    "common.data-structures",
    4,
    "Структуры данных",
    ALL,
    ("algorithms",),
    true=(
        "Извлечение минимума из двоичной кучи выполняется за O(log n)",
        "Поиск по ключу в хеш-таблице в среднем выполняется за O(1)",
        "Сбалансированное дерево поиска хранит ключи упорядоченно и ищет за O(log n)",
        "Вставка в начало связного списка выполняется за O(1)",
    ),
    false=(
        "Поиск элемента в несортированном массиве выполняется за O(log n)",
        "Хеш-таблица хранит ключи в отсортированном порядке",
        "Извлечение минимума из двоичной кучи выполняется за O(1)",
        "Доступ к i-му элементу связного списка выполняется за O(1)",
        "Вставка в середину массива выполняется за O(1)",
    ),
)


# --- уровень 5 ------------------------------------------------------------------------------
statements(
    "common.distributed",
    5,
    "Распределённые системы",
    ALL,
    ("system-design",),
    true=(
        "При сетевом разделе система должна выбирать между согласованностью и доступностью",
        "Повтор запроса после таймаута безопасен только для идемпотентных операций",
        "Паттерн Outbox гарантирует, что событие уйдёт тогда и только тогда, когда транзакция зафиксирована",
        "Кворум чтения и записи с R + W > N даёт чтение последней подтверждённой записи",
    ),
    false=(
        "Двухфазный коммит устраняет блокировки при отказе координатора",
        "Exactly-once доставка достигается простым повтором отправки",
        "Шардирование по случайному ключу ускоряет запросы с диапазоном по этому ключу",
        "Часы разных серверов можно считать синхронными с точностью до микросекунд",
        "Репликация сама по себе защищает от логического удаления данных",
    ),
)


statements(
    "common.architecture",
    5,
    "Архитектурные решения",
    ALL,
    ("system-design",),
    true=(
        "Микросервисы упрощают независимый деплой команд ценой сложности эксплуатации",
        "Модульный монолит позволяет выделить сервис позже, если границы модулей чёткие",
        "Асинхронная очередь сглаживает пики нагрузки, но добавляет задержку и eventual consistency",
        "Кэш ускоряет чтение, но требует стратегии инвалидации",
    ),
    false=(
        "Переход на микросервисы всегда снижает стоимость поддержки",
        "Общая база данных у нескольких микросервисов упрощает их независимое развитие",
        "Горизонтальное масштабирование не требует изменений в хранении сессий",
        "Кэш всегда возвращает актуальные данные, если у него большой размер",
        "Синхронная цепочка из пяти сервисов надёжнее, чем один сервис",
    ),
)


@computed("common.capacity", 5, "Оценка нагрузки", ALL, ("system-design",))
def capacity(rng: random.Random) -> Item:
    dau = rng.choice([200_000, 500_000, 1_000_000, 3_000_000])
    per_user, peak = rng.choice([10, 20, 40]), rng.choice([2, 3, 5])
    rps = math.ceil(dau * per_user / 86_400 * peak)
    return numeric(
        f"Сервис: {number(dau)} активных пользователей в день, каждый делает {per_user} запросов "
        f"в сутки, пик в {peak} раз выше среднего. Сколько запросов в секунду нужно выдерживать "
        "в пик? Округлите вверх до целого.",
        rps,
    )


@computed("common.cache-latency", 5, "Кэширование", ALL, ("system-design", "redis"))
def cache_latency(rng: random.Random) -> Item:
    hit, cache_ms, db_ms = (
        rng.choice([80, 90, 95]),
        rng.choice([1, 2, 5]),
        rng.choice([40, 60, 100, 200]),
    )
    average = cache_ms + (100 - hit) * db_ms // 100
    return numeric(
        f"Доля попаданий в кэш — {hit}%. Запрос к кэшу занимает {cache_ms} мс; при промахе после "
        f"кэша идёт запрос к базе — ещё {db_ms} мс. Средняя задержка запроса, мс?",
        average,
    )
