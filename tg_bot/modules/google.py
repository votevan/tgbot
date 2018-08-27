import subprocess
from telegram import Update, Bot
from telegram.ext import run_async, Filters

from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler

def google(bot: Bot, update: Update):
        query = update.effective_message.text.split(None, 1)
        result_ = subprocess.run(['gsearch', str(query)], stdout=subprocess.PIPE)
        result = str(result_.stdout.decode())
        update.effective_message.reply_markdown('*ℹ️ Búsqueda: *\n`' + str(query) + '`\n\n*ℹ️ Resultados:*\n' + result)

__help__ = """
 - /google: Google search
 """

__mod_name__ = "Google"

GOOGLE_HANDLER = DisableAbleCommandHandler("google", google)

dispatcher.add_handler(GOOGLE_HANDLER)

        update.effective_message.reply_markdown('ℹ️ Búsqueda: ' + str(query) + '\nℹ️ Resultados:\n' + result)
