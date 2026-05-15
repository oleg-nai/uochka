# Деплой Уочки

## 1. Создай Telegram-бота

1. Открой @BotFather в Telegram
2. `/newbot` → задай имя и юзернейм
3. Скопируй токен — это `BOT_TOKEN`

---

## 2. Настрой Supabase

1. Зарегистрируйся на [supabase.com](https://supabase.com) → New project
2. Дождись запуска проекта (1–2 мин)
3. Зайди в **SQL Editor** и выполни содержимое файла `supabase_setup.sql`
4. В настройках проекта (Settings → API) скопируй:
   - **Project URL** → `SUPABASE_URL`
   - **anon public key** → `SUPABASE_KEY`

---

## 3. Запушь код на GitHub

```bash
cd ~/Desktop/project
git init
git add .
git commit -m "init"
gh auth login
gh repo create uochka --public --source=. --push
```

---

## 4. Задеплой на Railway

1. Зайди на [railway.app](https://railway.app) → **Start a New Project**
2. Выбери **Deploy from GitHub repo** → выбери `uochka`
3. Railway определит Python автоматически

---

## 5. Добавь переменные окружения в Railway

В Railway → твой проект → **Variables** добавь:

| Name | Value |
|------|-------|
| `BOT_TOKEN` | токен от BotFather |
| `SUPABASE_URL` | URL из Supabase |
| `SUPABASE_KEY` | anon key из Supabase |

Нажми **Deploy** — бот запустится.

---

## Проверка

Напиши `/start` своему боту — должно прийти приветствие.
Отправь геолокацию — бот вернёт ближайшие туалеты.

---

## Структура проекта

```
project/
├── main.py                 # Точка входа (polling)
├── Procfile                # Railway: worker: python main.py
├── bot/
│   ├── app.py
│   ├── keyboards.py
│   └── handlers/
│       ├── start.py
│       ├── location.py
│       ├── add_toilet.py
│       └── report.py
├── db/
│   └── queries.py
├── supabase_setup.sql
├── requirements.txt
└── .env.example
```
