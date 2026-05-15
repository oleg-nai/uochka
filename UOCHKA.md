# Уочка — Telegram-бот для поиска туалетов

Пользователь отправляет геолокацию → получает список ближайших туалетов с адресом, расстоянием и ссылкой на маршрут.

---

## Стек

- **Python 3.12 + aiogram 3.x**
- **Supabase** — PostgreSQL + PostGIS, геозапросы
- **Vercel** — деплой (webhook через serverless function)

---

## MVP

- `/start` — приветствие
- Геолокация → 3–5 ближайших туалетов (адрес, расстояние, платный/нет)
- Кнопка "Маршрут" → ссылка на Google/Yandex Maps
- Добавить туалет — геолокация + описание
- Кнопка "Сообщить о проблеме" на карточке туалета
  - Причины: закрыт / не существует / очень грязно
  - 3+ жалоб за 7 дней → точка скрывается до верификации

Данные: OpenStreetMap (Overpass API) + пользовательские добавления.

---

## БД

```sql
toilets (id, location GEOGRAPHY, name, address, is_paid, is_accessible, working_hours, verified, reports_count, hidden_at)
users   (id, telegram_id, username, created_at, is_banned)
reviews (id, toilet_id, user_id, rating, comment, created_at)
reports (id, toilet_id, user_id, reason, created_at)  -- закрыт / не существует / грязно
```
