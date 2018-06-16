from typing import Optional

from telegram import Message, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.rules_sql as sql
from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.string_handling import markdown_parser


@run_async
def get_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    send_rules(update, chat_id)


# Do not async - not from a handler
def send_rules(update, chat_id, from_pm=False):
    bot = dispatcher.bot
    user = update.effective_user  # type: Optional[User]
    try:
        chat = bot.get_chat(chat_id)
    except BadRequest as excp:
        if excp.message == "Chat not found" and from_pm:
            bot.send_message(user.id, "¡El atajo de reglas para este chat no se ha configurado correctamente!"
                                      "Preguntale a los administradores del grupo para corregir esto.")
                                      #Original:
                                      #The rules shortcut for this chat hasn't been set properly! Ask admins to
                                      #fix this.
            return
        else:
            raise

    rules = sql.get_rules(chat_id)
    text = "Las reglas de *{}* son:\n\n{}".format(escape_markdown(chat.title), rules) 
           #Original: The rules for *{}* are:

    if from_pm and rules:
        bot.send_message(user.id, text, parse_mode=ParseMode.MARKDOWN)
    elif from_pm:
        bot.send_message(user.id, "Los administradores del grupo aún no han establecido reglas para este chat.")
                                  #Original:
                                  #The group admins haven't set any rules for this chat yet. 
                                  #This probably doesn't mean it's lawless though...!
    elif rules:
        update.effective_message.reply_text("Contactame en chat privado para obtener las reglas.",
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="Reglas",
                                                                       url="t.me/{}?start={}".format(bot.username,
                                                                                                     chat_id))]]))
    else:
        update.effective_message.reply_text("Los administradores del grupo aún no han establecido reglas para este chat.")
                                  #Original:
                                  #The group admins haven't set any rules for this chat yet. 
                                  #This probably doesn't mean it's lawless though...!


@run_async
@user_admin
def set_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
    if len(args) == 2:
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)

        sql.set_rules(chat_id, markdown_rules)
        update.effective_message.reply_text("¡Reglas establecidas con éxito!") #Original: Successfully set rules for this group.


@run_async
@user_admin
def clear_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    sql.set_rules(chat_id, "")
    update.effective_message.reply_text("¡Reglas eliminadas con éxito!") #Original: Successfully cleared rules!

def __stats__():
    return "{} chats poseen las reglas configuradas.".format(sql.num_chats()) #Original: {} chats have rules set.


def __import_data__(chat_id, data):
    # set chat rules
    rules = data.get('info', {}).get('rules', "")
    sql.set_rules(chat_id, rules)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "Este chat tiene sus reglas establecidas: `{}`".format(bool(sql.get_rules(chat_id))) #Original: This chat has had it's rules set: `{}`


__help__ = """
 - /rules: obtén las reglas del chat.

*Solo para administradores:*
 - /setrules <reglas>: configura las reglas del chat.
 - /clearrules: elimina las reglas del chat.
"""

#Original:
# - /rules: get the rules for this chat.

#*Admin only:*
# - /setrules <your rules here>: set the rules for this chat.
# - /clearrules: clear the rules for this chat.

__mod_name__ = "Reglas"

GET_RULES_HANDLER = CommandHandler("rules", get_rules, filters=Filters.group)
SET_RULES_HANDLER = CommandHandler("setrules", set_rules, filters=Filters.group)
RESET_RULES_HANDLER = CommandHandler("clearrules", clear_rules, filters=Filters.group)

dispatcher.add_handler(GET_RULES_HANDLER)
dispatcher.add_handler(SET_RULES_HANDLER)
dispatcher.add_handler(RESET_RULES_HANDLER)	
