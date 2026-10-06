# Фронтенд

Одно SPA (Vite + React 19 + TypeScript strict), три портала, которые грузятся лениво.
Сборка — статика, её раздаёт Caddy в контейнере `web`; API — тот же домен (`/api/*`), CORS не нужен.

## Маршруты

| Путь | Что | Доступ |
|---|---|---|
| `/` | лендинг (две аудитории) | все |
| `/login`, `/register?role=candidate\|employer` | вход и регистрация; слева — тезисы для выбранной стороны | гость |
| `/verify-email`, `/forgot-password`, `/reset-password` | операции по ссылкам из писем (токен во фрагменте `#token=`) | все |
| `/passport/:id` | публичная проверка паспорта навыков (QR, печать) | все |
| `/app/*` | кабинет кандидата: профиль, ФСП и паспорт, рост и зарплаты, собеседования, офферы | `candidate` |
| `/company/*` | кабинет компании: вакансии, каталог, собеседования, офферы | `employer` |
| `/admin/*` | модерация: компании, вакансии, пользователи, аудит, модели ИИ | `admin` |

`RequireRole` (`src/auth/RequireRole.tsx`): гость → на вход с `?next=`, чужая роль → в свой кабинет.
После входа `safeNext` пускает только на путь своего портала (защита от open redirect).

## Структура `frontend/src`

```
api/          клиент и контракт
  schema.d.ts   типы из OpenAPI (генерируются, руками не править)
  types.ts      короткие имена типов домена поверх schema.d.ts
  endpoints.ts  все вызовы API по группам (authApi, candidateApi, insightsApi, …) — компоненты URL не собирают
  client.ts     fetch: токен из памяти, единый формат ошибок, refresh при 401, массивы в query
  errors.ts     ApiError, fieldErrors (ошибки 422 → поля), errorMessage
  session.ts    access-токен в памяти + подписка
  broadcast.ts  вход/выход синхронно во всех вкладках (BroadcastChannel)
  queries.ts    общие запросы: справочник навыков, useCursorList (пагинация «Показать ещё»)
auth/         AuthProvider (сессия), RequireRole, portal (пути порталов)
features/     экраны по доменам: auth, landing, candidate, employer, admin, interviews, passport, insights
lib/          форматирование (labels, деньги, даты), общие поля zod, тона бейджей, хуки
ui/           UI-kit: Button, Card, Dialog, ConfirmDialog, form (Field, Input, Select, Switch), Badge,
              Alert, Toast, Segmented, SkillPicker, CursorListView, EmptyState, AppShell, Spinner, QrCode
test/         render.tsx (renderWithApp, serveRoutes, json, bodyOf), setup.ts
styles.css    дизайн-токены (цвета) — единственное место с цветами
```

Внутри фичи: `XxxPage.tsx` (экран), компоненты, `hooks.ts` (запросы и мутации TanStack Query),
`schemas.ts` (zod-схемы форм), тесты рядом (`*.test.tsx`).

## Сессия

- Access-токен только в памяти (`api/session.ts`), не в localStorage — XSS не унесёт долгоживущий токен.
- При загрузке `AuthProvider` восстанавливает сессию по refresh-cookie (`POST /auth/refresh` с CSRF).
- `client.ts` на `401` один раз обновляет токен и повторяет запрос. Параллельные обновления в вкладке
  делят один промис, между вкладками — Web Locks: refresh-токен одноразовый, два одновременных запроса
  сервер принял бы за кражу.
- Смена пользователя (выход, вход в другой вкладке) очищает кэш запросов — данные одного пользователя
  не покажутся другому.

## Данные и формы

- Запросы — TanStack Query; ключи по доменам (`["profile"]`, `["insights", "salary"]`, `["vacancies", status]`).
  Мутация сама обновляет или инвалидирует связанные ключи (пример — `useUpdateProfile` сбрасывает
  `["insights"]`). Повторы — только при сетевых ошибках и 5xx (`main.tsx`).
- Списки — `useCursorList` + `CursorListView` (пусто / ошибка / «Показать ещё»).
- Формы — react-hook-form + zod; правила совпадают с бэком (`lib/fields.ts`: деньги, вилка, грейды).
  Ошибки сервера раскладываются по полям через `applyServerErrors` (`lib/forms.ts`).
- Подписи перечислений — `lib/format.ts` (`labels.grade`, `labels.offerStatus`, …), цвета бейджей —
  `lib/tones.ts`.

## Дизайн

- Тёмная тема, токены в `styles.css` (`--bg`, `--surface`, `--accent` …), Tailwind 4 читает их через
  `@theme inline` (`bg-surface`, `text-muted`, `border-line`). Брендбук ФСП подменяется здесь.
- Анимации — Motion, только transform/opacity; `MotionConfig reducedMotion="user"`.
- Доступность: подписи полей связаны с ошибками (`aria-describedby`), диалоги на нативном `<dialog>`,
  у графиков есть текстовая подпись и таблица.
- Графики радара зарплат — `features/insights/RangeChart.tsx`: полоса — 25–75 %, риска — медиана,
  пунктир — сравниваемое значение; один цвет; подсказка при наведении и фокусе; «Показать таблицей».
  Шкала с «круглыми» делениями — `features/insights/scale.ts`.

## Как добавить страницу

1. Эндпоинт в бэке → `npm run gen:api` (при запущенном стеке, пишет `src/api/schema.d.ts`).
2. Тип в `api/types.ts`, функция в `api/endpoints.ts` (+ строка в `api/endpoints.test.ts`).
3. `features/<домен>/<что>/hooks.ts` — `useQuery`/`useMutation`.
4. Компонент страницы; заголовок — `PageHeader`, загрузка — `LoadingBlock`, ошибка — `Alert`
   с `errorMessage(err)`, пусто — `EmptyState`.
5. Маршрут и пункт меню в `CandidatePortal.tsx` / `EmployerPortal.tsx` / `AdminPortal.tsx` (`NAV`).
6. Тест рядом: `renderWithApp(<Page />)` + `serveRoutes({"/путь": () => json(ответ)})`.

## Команды

Node на ПК не обязателен: `make test-frontend` собирает и тестирует в контейнере.
Если Node есть: `npm ci`, `npm run dev` (прокси на API — `vite.config.ts`), `npm test`,
`npm run coverage`, `npm run typecheck`, `npm run build`.
