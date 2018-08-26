import wikipedia
from telegram import Update, Bot
from telegram.ext import run_async, Filters
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler
def wiki(bot: Bot, update: Update):
        query = update.effective_message.text.split(None, 1)
        result = '**Search:**\n`' + query + '`\n\n**Result:**\n`' + wikipedia.summary(match)
        update.effective_message.reply_markdown(result)
__help__ = """
 - /wiki: Query the Wikipedia
 """
__mod_name__ = "Wikipedia Search"
WIKI_HANDLER = DisableAbleCommandHandler("wiki", wiki)
dispatcher.add_handler(WIKI_HANDLER)
