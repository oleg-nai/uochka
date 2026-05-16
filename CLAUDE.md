# Уочка — контекст для Claude

Telegram-бот «Уочка» — поиск ближайших публичных туалетов по геолокации (Минск).

## Стек

- Python 3.12, aiogram 3.15
- Supabase (PostgreSQL + PostGIS) — геозапросы через RPC `find_nearest_toilets`
- Railway — деплой через GitHub integration (polling mode, `worker: python main.py`)
- Grafana Cloud Loki — структурированные логи

## Структура

```
main.py                       — точка входа, polling, Loki handler
bot/app.py                    — create_dispatcher(), MetricsMiddleware
bot/keyboards.py              — все клавиатуры
bot/handlers/start.py         — /start
bot/handlers/location.py      — обработка геолокации, лимит 1/10 по premium
bot/handlers/add_toilet.py    — FSM добавления туалета
bot/handlers/report.py        — жалобы на туалеты
bot/handlers/payment.py       — Telegram Stars: buy_premium, pre_checkout, successful_payment, /premium, /balance
db/queries.py                 — все обращения к Supabase
supabase_setup.sql            — схема БД (users, toilets, reviews, reports, bot_events) + функции
tests/                        — pytest, 101 тест, 100% покрытие bot/ и db/
```

**Таблицы БД:** users (с is_premium, premium_since), toilets, reviews, reports, bot_events.

## Env vars

В Railway/`.env`:
- `BOT_TOKEN` — Telegram bot token
- `SUPABASE_URL`, `SUPABASE_KEY` — anon key
- `LOKI_URL`, `LOKI_USERNAME`, `LOKI_PASSWORD` — опционально для Loki
- `ADMIN_TELEGRAM_ID` — опционально, default 509530840 (для `/balance`)

## Монетизация

**Telegram Stars (нативная оплата Telegram), 1 ⭐️ — тестовая цена.**

- Free: 1 туалет рядом
- Premium (lifetime): до 10 туалетов в радиусе 5 км
- Платёж: `answer_invoice` с `currency="XTR"`, payload `premium:<tg_id>`
- `pre_checkout_query` всегда `ok=True`, `successful_payment` → `set_premium`
- Звёзды копятся на балансе бота. Вывод через [Fragment](https://fragment.com) от 1000 ⭐️, холд 21 день
- Команда `/balance` (только для админа) — показывает текущий Stars-баланс через `getMyStarBalance`

**Why Stars вместо CryptoBot/TON:** не нужен внешний токен, работает в любом регионе, реализация в 50 строк.

## Что уже сделано

- ✅ MVP: поиск, добавление, жалобы (3+ за 7 дней → точка скрывается)
- ✅ Платёж через Telegram Stars
- ✅ Supabase миграция `is_premium`, `premium_since` (2026-05-17)
- ✅ Структурированные логи в Loki
- ✅ Тесты: 101 шт, 100% coverage по `bot/` и `db/`
- ✅ `/balance` команда (admin)

## Что осталось (приоритеты)

1. **Нарастить базу туалетов** — сейчас в БД ~3 точки. Импортировать публичные туалеты Минска из OSM Overpass API. Без этого бот бесполезен.
2. **Поднять цену с 1 ⭐️ до ~50-150 ⭐️** ($1-3) когда будет стабильный поток пользователей.
3. **Подумать модель**: lifetime vs подписка; лимит "10 туалетов" заменить на "радиус 500м free / 5км premium" (в Минске редко бывает 10+ в 5 км).
4. Привлечь первых пользователей (TG-каналы про Минск, r/belarus).

## Запуск тестов

```bash
source .venv/bin/activate
pytest tests/ -v
# или с покрытием:
pytest tests/ --cov=bot --cov=db --cov-report=term-missing
```
