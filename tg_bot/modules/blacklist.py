import html
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async

import tg_bot.modules.sql.blacklist_sql as sql
from tg_bot import dispatcher, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin, user_not_admin
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.misc import split_message

BLACKLIST_GROUP = 11

BASE_BLACKLIST_STRING = "palabras en la <b>lista negra</b>:\n" #Original: Current <b>blacklisted</b> words:


@run_async
def blacklist(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]

    all_blacklisted = sql.get_chat_blacklist(chat.id)

    filter_list = BASE_BLACKLIST_STRING

    if len(args) > 0 and args[0].lower() == 'copy':
        for trigger in all_blacklisted:
            filter_list += "<code>{}</code>\n".format(html.escape(trigger))
    else:
        for trigger in all_blacklisted:
            filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if text == BASE_BLACKLIST_STRING:
            msg.reply_text("¡No hay palabras en la lista negra!") #Original: There are no blacklisted messages here!
            return
        msg.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
@user_admin
def add_blacklist(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_blacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        for trigger in to_blacklist:
            sql.add_to_blacklist(chat.id, trigger.lower())

        if len(to_blacklist) == 1:
            msg.reply_text("¡Añadido <code>{}</code> a la lista negra!".format(html.escape(to_blacklist[0])), 
                            
                           #Original: Added <code>{}</code> to the blacklist!

                           parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "Añadido <code>{}</code> a la lista negra.".format(len(to_blacklist)), parse_mode=ParseMode.HTML)

                #Original: Added <code>{}</code> to the blacklist!

    else:
        msg.reply_text("Dígame qué palabras desea eliminar de la lista negra.")


@run_async
@user_admin
def unblacklist(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        successful = 0
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat.id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                msg.reply_text("¡Removido <code>{}</code> de la lista negra!".format(html.escape(to_unblacklist[0])),

                               #Original: Removed <code>{}</code> from the blacklist!

                               parse_mode=ParseMode.HTML)
            else:
                msg.reply_text("¡Esta no es una palabra de la lista negra!") 

                               #Original: This isn't a blacklisted trigger...!

        elif successful == len(to_unblacklist):
            msg.reply_text(
                "Removido <code>{}</code> de la lista negra.".format(  
   
                #Original: Removed <code>{}</code> triggers from the blacklist.

                    successful), parse_mode=ParseMode.HTML)

        elif not successful:
            msg.reply_text(
                "Ninguna de estas palabras existen, por lo que no se eliminaron.".format( 
 
                #Original: None of these triggers exist, so they weren't removed.

                    successful, len(to_unblacklist) - successful), parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "Removido <code>{}</code> de la lista negra. {} no existe, "
                "por lo tanto no fue removida.".format(successful, len(to_unblacklist) - successful), 

                #Original:
                #Removed <code>{}</code> triggers from the blacklist. {} did not exist,
                #so were not removed.
                parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("Dígame qué palabras desea eliminar de la lista negra.")

                       #Original: Tell me which words you would like to remove from the blacklist.


@run_async
@user_not_admin
def del_blacklist(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    to_match = extract_text(message)
    if not to_match:
        return

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("Error al eliminar palabra de la lista negra.")

                                     #Original: Error while deleting blacklist message.

            break


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "Hay {} palabras en la lista negra.".format(blacklisted)


def __stats__():
    return "{} palabras en la lista negra, entre {} chats.".format(sql.num_blacklist_filters(),
           #Original: {} blacklist triggers, across {} chats.
                                                            sql.num_blacklist_filter_chats())


__mod_name__ = "Blacklist" 

__help__ = """
Las listas negras se usan para evitar que ciertas palabras se digan en un grupo. Cada vez que se menciona \
la palabra, el mensaje se borrará inmediatamente. ¡Un buen combo es combinar esto con los filtros de advertencias!
*NOTA:* La lista negra no afecta a los administadores de un grupo.
- /blacklist: Ver las palabras en lista negra.
*Solo para administradores:*
- /addblacklist <palabras>: Agregue una palabra a la lista negra. Cada línea se considera una palabra, por lo que usar \
diferentes líneas le permitirán agregar múltiples palabras fácilmente.
- /unblacklist <palabras>: Elimine palabras de la lista negra. La misma lógica de distintas líneas se aplica aquí, por \
lo que puede eliminar múltiples palabras a la vez.
- /rmblacklist <oalabras>: Igual que arriba.
"""

<<<<<<< HEAD
#Original:
#Blacklists are used to stop certain triggers from being said in a group. Any time the trigger is mentioned, \
#the message will immediately be deleted. A good combo is sometimes to pair this up with warn filters!
#*NOTE:* blacklists do not affect group admins.
# - /blacklist: View the current blacklisted words.
#*Admin only:*
# - /addblacklist <triggers>: Add a trigger to the blacklist. Each line is considered one trigger, so using different \
#lines will allow you to add multiple triggers.
# - /unblacklist <triggers>: Remove triggers from the blacklist. Same newline logic applies here, so you can remove \
#multiple triggers at once.
# - /rmblacklist <triggers>: Same as above.

BLACKLIST_HANDLER = DisableAbleCommandHandler("blacklist", blacklist, filters=Filters.group, admin_ok=True)
=======
BLACKLIST_HANDLER = DisableAbleCommandHandler("blacklist", blacklist, filters=Filters.group, pass_args=True,
                                              admin_ok=True)
>>>>>>> 08b0a4151c3ba54fea367b5dacb83a966efb2659
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist, filters=Filters.group)
UNBLACKLIST_HANDLER = CommandHandler(["unblacklist", "rmblacklist"], unblacklist, filters=Filters.group)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.group, del_blacklist)

dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)
