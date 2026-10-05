# Архитектура

## Функциональная архитектура

```mermaid
flowchart LR
  subgraph cand["Кандидат /app"]
    c1["Профиль и резюме<br/>PDF/DOCX → черновик,<br/>PDF-профиль"]
    c2["Опрос и тест<br/>категория, история,<br/>повтор на грейд ниже/выше"]
    c3["Приглашения и отклики<br/>принять / отклонить"]
    c4["Вакансии<br/>отклик по соответствию"]
    c5["Задача недели"]
    c6["ФСП и паспорт навыков"]
    c7["Приватность и согласие"]
  end
  subgraph emp["Работодатель /company"]
    e1["Профиль компании"]
    e2["Вакансии = описание потребности<br/>+ пример теста"]
    e3["Каталог: категории,<br/>карточки, «Почему»"]
    e4["Приглашения и отклики<br/>статусы, контакты"]
    e5["Задачи для кандидатов"]
    e6["Собеседования и офферы"]
  end
  subgraph core["Ядро"]
    k1["Тестирование<br/>банк шаблонов, IRT"]
    k2["Категоризация<br/>специализация × грейд"]
    k3["Подбор<br/>факторы + объяснения"]
    k4["Выход на контакт<br/>статусы, согласие"]
    k5["Интеграция ФСП"]
  end
  c2 --> k1 --> k2 --> k3
  e2 --> k3
  e3 --> k3
  e4 --> k4
  c3 --> k4
  c4 --> k4
  c6 --> k5 --> k3
  c5 --> k3
  e5 --> c5
  admin["Админка /admin<br/>модерация постфактум, аудит, модели ИИ"]
```

## Компонентная архитектура

```mermaid
flowchart TB
  user["Пользователь<br/>кандидат · работодатель · админ"]
  fspReal["API ФСП / ФСП ID<br/>(прод)"]

  subgraph edge["Сеть edge"]
    caddy["Caddy HTTPS<br/>TLS · заголовки · лимит тела"]
    web["web<br/>статика React<br/>/app · /company · /admin · /api-docs"]
  end

  subgraph backend["Сеть internal (без выхода наружу)"]
    api["api · FastAPI<br/>роутеры + валидация + OpenAPI"]
    svc["services<br/>сценарии + AccessPolicy"]
    repo["repositories<br/>фильтр owner / tenant"]
    worker["worker<br/>синк ФСП · письма · истечение<br/>приглашений и офферов · лимиты"]
    mock["fsp-mock<br/>мок API ФСП"]
    migrate["migrate<br/>one-shot"]
    db[("PostgreSQL<br/>RLS · отдельные роли<br/>лимиты · очередь писем")]
  end

  user -->|HTTPS| caddy
  caddy -->|"/"| web
  caddy -->|"/api/*"| api
  api --> svc
  svc --> repo
  repo --> db
  worker --> svc
  svc -->|FspClient: dev| mock
  svc -.->|FspClient: прод| fspReal
  migrate --> db
```

Монолит с явными слоями и слабо связанными модулями: `api` (HTTP) → `services` (сценарии и права) →
`repositories` (запросы с фильтром владельца) → `models`. Модули предметной области:

| Модуль | Код | Документ |
|---|---|---|
| Тестирование и категории | `services/assessment/`, `services/specializations.py` | [assessment.md](assessment.md) |
| Подбор и каталог | `services/matching/`, `services/catalog.py` | [matching.md](matching.md) |
| Выход на контакт | `services/applications/`, `services/vacancy_board.py` | [matching.md](matching.md) |
| Задачи от работодателей | `services/tasks.py` | [assessment.md](assessment.md) |
| ФСП и паспорт навыков | `services/fsp*.py`, `services/passport.py`, `integrations/fsp.py` | [integrations.md](integrations.md) |
| Резюме и автозаполнение | `services/resume/`, `services/profile_import.py` | [integrations.md](integrations.md) |
| Собеседования и офферы | `services/interviews/`, `services/offers.py` | [api.md](api.md) |
| Процедура оценки | `app/evaluation/` (`make evaluate`) | [validation.md](validation.md) |

Каждый сервис компоуза запускается отдельно (`make up S="db api"`), api и worker — один образ.
Данные пользователей защищены дважды: фильтром репозитория и Row Level Security в PostgreSQL
([data.md](data.md)).
