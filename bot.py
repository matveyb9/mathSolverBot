import os
import logging
import uuid
from telegram import (
    Update, InlineQueryResultArticle, InputTextMessageContent,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    InlineQueryHandler, ContextTypes, filters,
)
from telegram.constants import ParseMode
from solver import parse_and_solve, format_result_message

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────
EXAMPLES = [
    "2x + 5 = 11",
    "x^2 - 5x + 6 = 0",
    "x^3 - 6x^2 + 11x - 6 = 0",
    "sin(x) = 0.5",
    "2^x = 8",
    "log(x, 10) = 2",
    "x^4 - 5x^2 + 4 = 0",
]

HELP_TEXT = """
🤖 *Бот-решатель уравнений*

Просто отправь мне уравнение, и я его решу\!

*Поддерживаемые типы:*
• Линейные:  `2x + 5 = 11`
• Квадратные: `x^2 - 5x + 6 = 0`
• Кубические: `x^3 - 6x^2 + 11x - 6 = 0`
• Степень 4\+: `x^4 - 5x^2 + 4 = 0`
• Тригонометрические: `sin(x) = 0.5`
• Показательные: `2\*\*x = 8`
• Логарифмические: `log(x, 10) = 2`

*Синтаксис:*
• `^` или `**` — степень
• `*` — умножение \(можно опускать перед переменной\)
• `sqrt(x)` — квадратный корень
• `pi`, `e` — константы

*Инлайн режим:*
Введи `@имя\_бота уравнение` в любом чате\!

Команды: /start /help /examples
"""


def escape_md(text: str) -> str:
    """Escape special characters for MarkdownV2."""
    special = r'\_*[]()~`>#+-=|{}.!'
    return "".join(f'\\{c}' if c in special else c for c in text)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name or "друг"
    text = (
        f"👋 Привет, {escape_md(name)}\\!\n\n"
        "Я умею решать уравнения разных типов\\. "
        "Просто отправь мне уравнение, например:\n\n"
        "`x^2 - 5x + 6 = 0`\n\n"
        "Или воспользуйся /help для подробной справки\\."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_examples(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = ["📚 *Примеры уравнений:*\n"]
    for ex in EXAMPLES:
        lines.append(f"• `{escape_md(ex)}`")
    lines.append("\nПросто скопируй и отправь любое из них\\!")
    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2
    )


async def handle_equation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain-text messages as equations."""
    text = update.message.text.strip()

    # Skip commands
    if text.startswith("/"):
        return

    await update.message.chat.send_action("typing")

    try:
        result = parse_and_solve(text)
        answer = format_result_message(result)
        await update.message.reply_text(
            f"```\n{answer}\n```",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except ValueError as e:
        await update.message.reply_text(
            f"⚠️ *Ошибка разбора*\n\n{escape_md(str(e))}\n\n"
            "Проверь синтаксис\\. Пример: `x^2 - 5x + 6 = 0`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as e:
        logger.exception("Unexpected error solving: %s", text)
        await update.message.reply_text(
            "😔 Не удалось решить уравнение\\. Попробуй переформулировать\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline queries."""
    query = update.inline_query.query.strip()
    results = []

    if not query:
        # Show hint when no query
        hint = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="✏️ Введи уравнение...",
            description="Например: x^2 - 5x + 6 = 0",
            input_message_content=InputTextMessageContent("x^2 - 5x + 6 = 0"),
        )
        await update.inline_query.answer([hint], cache_time=10)
        return

    try:
        result = parse_and_solve(query)
        answer = format_result_message(result)

        # Main result card
        article = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=f"✅ {result.equation_type}",
            description=result.solution_text.replace("\n", " | "),
            input_message_content=InputTextMessageContent(
                f"```\n{answer}\n```",
                parse_mode=ParseMode.MARKDOWN_V2,
            ),
            thumb_url="https://cdn-icons-png.flaticon.com/512/2103/2103633.png",
        )
        results.append(article)

    except Exception as e:
        err_article = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="⚠️ Не удалось разобрать уравнение",
            description=str(e)[:100],
            input_message_content=InputTextMessageContent(
                f"Ошибка при разборе «{query}»: {e}"
            ),
        )
        results.append(err_article)

    await update.inline_query.answer(results, cache_time=5)


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Переменная окружения BOT_TOKEN не задана!\n"
            "Установи её в .env файле или передай в docker run."
        )

    app = (
        Application.builder()
        .token(token)
        .build()
    )

    # Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("examples", cmd_examples))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_equation))

    logger.info("🚀 Бот запущен. Ожидаю уравнения...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
