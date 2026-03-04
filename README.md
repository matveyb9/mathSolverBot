# 📐 Equation Solver Bot

Telegram-бот для решения уравнений в обычном и инлайн-режиме.

## Поддерживаемые типы уравнений

| Тип | Пример |
|-----|--------|
| Линейные | `2x + 5 = 11` |
| Квадратные | `x^2 - 5x + 6 = 0` |
| Кубические | `x^3 - 6x^2 + 11x - 6 = 0` |
| Степень 4+ | `x^4 - 5x^2 + 4 = 0` |
| Тригонометрические | `sin(x) = 0.5` |
| Показательные | `2**x = 8` |
| Логарифмические | `log(x, 10) = 2` |
| Иррациональные | `sqrt(x+1) = 3` |

## Быстрый старт

### 1. Создай бота у @BotFather

1. Напиши `/newbot` в чате с @BotFather
2. Задай имя и username
3. Скопируй токен
4. Для инлайн-режима: `/setinline` → выбери бота → введи placeholder, например `уравнение...`

### 2. Настрой окружение

```bash
cp .env.example .env
# Открой .env и вставь свой токен:
# BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Запусти через Docker Compose

```bash
# Сборка и запуск
docker compose up -d --build

# Просмотр логов
docker compose logs -f

# Остановка
docker compose down
```

### Или через Docker напрямую

```bash
# Сборка
docker build -t equation-bot .

# Запуск
docker run -d \
  --name equation-bot \
  --restart unless-stopped \
  -e BOT_TOKEN=ВАШ_ТОКЕН \
  equation-bot
```

## Структура проекта

```
equation_bot/
├── bot.py            # Telegram-хендлеры, точка входа
├── solver.py         # Парсинг и решение уравнений (SymPy)
├── requirements.txt  # Зависимости Python
├── Dockerfile        # Многоэтапная сборка
├── docker-compose.yml
├── .env.example      # Шаблон конфига
└── README.md
```

## Синтаксис уравнений

- `^` или `**` — возведение в степень
- `*` — умножение (можно опускать перед переменной: `2x` = `2*x`)
- `sqrt(x)` — квадратный корень
- `sin`, `cos`, `tan` — тригонометрия (радианы)
- `log(x, base)` — логарифм
- `exp(x)` или `e**x` — экспонента
- `pi`, `e` — математические константы

## Инлайн-режим

В любом чате напечатай:
```
@username_бота x^2 - 4 = 0
```
Бот покажет решение прямо в выпадающем списке.
