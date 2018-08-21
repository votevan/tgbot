from telegram import Message, Update, Bot, User
from telegram.ext import Filters, MessageHandler, run_async
from googletrans import Translator
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot import dispatcher

@run_async
def gtranslate(bot: Bot, update: Update):
  message = update.effective_message
  text = message.reply_to_message.text
  reply_text=translator.translate(text, dest='en').text
  reply_text="`Fuente: `\n"+text+"`Traduccion: `\n"+reply_text
  message.reply_to_message.reply_text(reply_text)

gtranslate_handler = DisableAbleCommandHandler("gtranslate", gtranslate)
dispatcher.add_handler(gtranslate_handler)
