import os, asyncio, logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (Application, CommandHandler,
                           MessageHandler, ContextTypes, filters)
from core.agent import get_agent

load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log   = logging.getLogger(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
agent = get_agent()


async def cmd_start(u: Update, _):
    name = u.effective_user.first_name
    await u.message.reply_text(
        f"Hola {name}! Soy SaverAgent.\n\n"
        "Te ayudo a distribuir tus ingresos en metas de ahorro "
        "usando cUSD en Celo.\n\n"
        "Prueba escribir: Recibi $300"
    )

async def cmd_metas(u: Update, _):
    uid = str(u.effective_user.id)
    await u.message.reply_text(agent.chat(uid, "mis metas"))

async def cmd_help(u: Update, _):
    await u.message.reply_text(
        "Comandos disponibles:\n\n"
        "  'Recibi $300'  -> plan de distribucion\n"
        "  'si'           -> ejecutar el plan\n"
        "  /metas         -> ver tus metas\n"
        "  /help          -> esta ayuda\n\n"
        "Powered by Celo"
    )

async def handle(u: Update, ctx):
    uid = str(u.effective_user.id)
    await ctx.bot.send_chat_action(u.effective_chat.id, "typing")
    try:
        reply = agent.chat(uid, u.message.text)
        await u.message.reply_text(reply)
    except Exception as e:
        log.error(e)
        await u.message.reply_text("Error tecnico. Intenta de nuevo.")


async def main():
    if not TOKEN:
        print("ERROR: Falta TELEGRAM_BOT_TOKEN en .env")
        print("  1. Abre Telegram -> @BotFather -> /newbot")
        print("  2. Copia el token -> pegalo en .env")
        return

    print("SaverAgent iniciando...")
    print("Abre Telegram -> busca tu bot -> escribe /start")
    print("Ctrl+C para detener\n")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("metas", cmd_metas))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle)
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    print("Bot activo! Escribe /start en Telegram.\n")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        print("Bot detenido.")


if __name__ == "__main__":
    asyncio.run(main())
