"""Задания для фронтенд-разработчиков: JavaScript, вёрстка, React, производительность, безопасность."""

import random

from app.models.enums import Specialization
from app.services.assessment.items import Item, choice, computed, numeric, statements

FRONTEND = (Specialization.FRONTEND,)
JS = ("javascript", "typescript")

# --- уровень 1 ------------------------------------------------------------------------------
_EXPRESSIONS = (
    ('"5" + 3', '"53"'),
    ('"5" - 3', "2"),
    ("typeof null", '"object"'),
    ("typeof NaN", '"number"'),
    ("NaN === NaN", "false"),
    ("null == undefined", "true"),
    ("null === undefined", "false"),
    ("[] + []", '""'),
    ('Boolean("0")', "true"),
    ('0 || "default"', '"default"'),
    ('0 ?? "default"', "0"),
)
_OUTPUTS = (
    '"53"',
    "8",
    "2",
    '"object"',
    '"null"',
    '"number"',
    "true",
    "false",
    '""',
    "0",
    '"default"',
)


@computed("frontend.js-values", 1, "Типы в JavaScript", FRONTEND, JS)
def js_values(rng: random.Random) -> Item:
    expression, answer = rng.choice(_EXPRESSIONS)
    wrong = rng.sample([o for o in _OUTPUTS if o != answer], 3)
    return choice(rng, "Чему равно выражение?", answer, wrong, expression)


@computed("frontend.box-model", 1, "Блочная модель CSS", FRONTEND, ())
def box_model(rng: random.Random) -> Item:
    width, padding, border = (
        rng.choice([200, 240, 300]),
        rng.choice([8, 10, 16]),
        rng.choice([1, 2]),
    )
    sizing = rng.choice(["content-box", "border-box"])
    code = (
        f".card {{\n  box-sizing: {sizing};\n  width: {width}px;\n"
        f"  padding: {padding}px;\n  border: {border}px solid;\n}}"
    )
    total = width if sizing == "border-box" else width + 2 * padding + 2 * border
    return numeric("Какую ширину в пикселях займёт элемент на странице?", total, code)


# --- уровень 2 ------------------------------------------------------------------------------
_TASKS = {
    "sync": "console.log('{x}')",
    "micro": "Promise.resolve().then(() => console.log('{x}'))",
    "macro": "setTimeout(() => console.log('{x}'), 0)",
}


def _run_order(kinds: list[str], labels: list[str], phases: tuple[str, ...]) -> list[str]:
    return [x for phase in phases for kind, x in zip(kinds, labels, strict=True) if kind == phase]


@computed("frontend.event-loop", 2, "Цикл событий", FRONTEND, JS)
def event_loop(rng: random.Random) -> Item:
    kinds = ["sync", "micro", "macro", rng.choice(["sync", "micro", "macro"])]
    rng.shuffle(kinds)
    labels = list("ABCD")
    code = ";\n".join(_TASKS[k].format(x=x) for k, x in zip(kinds, labels, strict=True)) + ";"
    answer = " ".join(_run_order(kinds, labels, ("sync", "micro", "macro")))
    # правдоподобные ошибки: «как написано» и «таймер раньше промиса», затем случайные порядки
    wrong = [" ".join(labels), " ".join(_run_order(kinds, labels, ("sync", "macro", "micro")))]
    while len({w for w in wrong if w != answer}) < 3:
        wrong.append(" ".join(rng.sample(labels, len(labels))))
    return choice(rng, "В каком порядке появятся буквы в консоли?", answer, wrong, code)


statements(
    "frontend.react-state",
    2,
    "React: состояние и ключи",
    FRONTEND,
    ("react",),
    true=(
        "Ключ элемента списка помогает React сопоставить элементы между рендерами",
        "Изменение состояния через setState приводит к повторному рендеру компонента",
        "Прямое изменение объекта состояния без setState не гарантирует перерисовку",
        "Индекс массива как ключ ломает состояние элементов при перестановке",
    ),
    false=(
        "Ключ нужен только для стилизации элементов списка",
        "Состояние компонента можно безопасно менять напрямую — React заметит это сам",
        "Каждый вызов setState синхронно перерисовывает весь DOM страницы",
        "useEffect без массива зависимостей выполняется только один раз",
    ),
)


# --- уровень 3 ------------------------------------------------------------------------------
@computed("frontend.closures", 3, "Замыкания", FRONTEND, JS)
def closures(rng: random.Random) -> Item:
    n, keyword = rng.randint(3, 5), rng.choice(["var", "let"])
    code = f"for ({keyword} i = 0; i < {n}; i++) {{\n  setTimeout(() => console.log(i), 0);\n}}"
    same = " ".join([str(n)] * n)
    sequence = " ".join(str(i) for i in range(n))
    answer = same if keyword == "var" else sequence
    wrong = [same, sequence, " ".join(str(i) for i in range(1, n + 1)), " ".join([str(n - 1)] * n)]
    return choice(rng, "Что выведет код?", answer, wrong, code)


statements(
    "frontend.typescript",
    3,
    "TypeScript",
    FRONTEND,
    ("typescript",),
    true=(
        "Значение типа unknown нельзя использовать без проверки или сужения типа",
        "Проверка typeof x === 'string' сужает тип объединения внутри ветки",
        "Типы TypeScript стираются при компиляции и не проверяются во время выполнения",
        "Утилита Partial<T> делает все поля типа необязательными",
    ),
    false=(
        "Тип any и тип unknown ведут себя одинаково",
        "TypeScript проверяет типы данных, пришедших с сервера, во время выполнения",
        "Интерфейс нельзя расширить другим интерфейсом",
        "Утилита Readonly<T> запрещает изменения объекта во время выполнения",
    ),
)


# --- уровень 4 ------------------------------------------------------------------------------
statements(
    "frontend.performance",
    4,
    "Производительность интерфейса",
    FRONTEND,
    ("react", "javascript"),
    true=(
        "Анимация transform и opacity обычно не вызывает пересчёт раскладки",
        "Чтение offsetHeight после изменения стилей вызывает принудительный reflow",
        "Виртуализация списка рендерит только видимые элементы",
        "Ленивая загрузка маршрутов уменьшает размер начального бандла",
    ),
    false=(
        "Анимация свойства width дешевле, чем transform",
        "React.memo предотвращает рендер даже при изменении пропсов",
        "Чем больше компонентов в одном файле, тем быстрее загрузка страницы",
        "Виртуализация списка увеличивает число DOM-узлов",
    ),
)

statements(
    "frontend.web-security",
    4,
    "Безопасность в браузере",
    FRONTEND,
    ("javascript",),
    true=(
        "Токен в localStorage доступен любому скрипту на странице при XSS",
        "Cookie с флагом HttpOnly недоступна из JavaScript",
        "CORS ограничивает чтение ответов скриптами с других источников, а не отправку запросов",
        "Content-Security-Policy может запретить выполнение встроенных скриптов",
    ),
    false=(
        "CORS защищает сервер от любых запросов с других сайтов",
        "Экранирование нужно только для данных, введённых администратором",
        "SameSite=Strict делает cookie доступной для JavaScript",
        "HTTPS защищает от XSS",
    ),
)


# --- уровень 5 ------------------------------------------------------------------------------
statements(
    "frontend.rendering",
    5,
    "Стратегии рендеринга",
    FRONTEND,
    ("react",),
    true=(
        "SSR ускоряет первый показ контента, но нагружает сервер на каждый запрос",
        "SSG подходит для страниц, которые редко меняются",
        "Гидратация делает отрендеренную на сервере разметку интерактивной",
        "CSR-приложение без SSR хуже индексируется поисковиками без дополнительных мер",
    ),
    false=(
        "SSR не требует JavaScript на клиенте для интерактивности",
        "SSG пересобирает страницу на каждый запрос пользователя",
        "Гидратация заменяет серверную разметку новой без повторного использования",
        "CSR всегда быстрее показывает первый контент, чем SSR",
    ),
)

statements(
    "frontend.delivery",
    5,
    "Доставка и кэширование фронтенда",
    FRONTEND,
    ("javascript",),
    true=(
        "Хеш содержимого в имени файла позволяет кэшировать его надолго",
        "index.html нельзя кэшировать надолго: он ссылается на новые версии бандлов",
        "Разделение кода по маршрутам уменьшает объём JavaScript для первой страницы",
        "CDN сокращает задержку, отдавая статику с ближайшего к пользователю узла",
    ),
    false=(
        "Файлы бандла без хеша в имени безопасно кэшировать на год",
        "Один большой бандл всегда загружается быстрее нескольких маленьких",
        "Service Worker обновляет кэш мгновенно у всех пользователей",
        "CDN не может отдавать сжатые файлы",
    ),
)
