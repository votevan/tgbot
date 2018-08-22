import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_admin, can_delete
from tg_bot.modules.log_channel import loggable


@run_async
@user_admin
@loggable
def purge(bot: Bot, update: Update, args: List[str]) -> str:
    msg = update.effective_message  # type: Optional[Message]
    if msg.reply_to_message:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        if can_delete(chat, bot.id):
            message_id = msg.reply_to_message.message_id
            if args and args[0].isdigit():
                delete_to = message_id + int(args[0])
            else:
                delete_to = msg.message_id - 1
            for m_id in range(delete_to, message_id - 1, -1):  # Reverse iteration over message ids
                try:
                    bot.deleteMessage(chat.id, m_id)
                except BadRequest as err:
                    if err.message == "Message can't be deleted":
                        bot.send_message(chat.id, "No pude borrar todos los mensajes: pueden ser muy viejos, podría "
                                                  "no tener permisos o esto no es un supergrupo.")

                                                  #Original:
                                                  #Cannot delete all messages. The messages may be too old, I might
                                                  #not have delete rights, or this might not be a supergroup.

                    elif err.message != "Message to delete not found":
                        LOGGER.exception("Error al eliminar mensajes de chat.") #Original: Error while purging chat messages.

            try:
                msg.delete()
            except BadRequest as err:
                if err.message == "Message can't be deleted":

                    bot.send_message(chat.id, "No pude borrar todos los mensajes: pueden ser muy viejos, podría "
                                              "no tener permisos o esto no es un supergrupo.")

                                              #Original:
                                              #Cannot delete all messages. The messages may be too old, I might
                                              #not have delete rights, or this might not be a supergroup.

                elif err.message != "Message to delete not found":
                    LOGGER.exception("Error al eliminar mensajes de chat.") #Original: Error while purging chat messages.

            bot.send_message(chat.id, "Eliminación completada.") #Original: Purge complete.
            return "<b>{}:</b>" \
                   "\n#PURGE" \
                   "\n<b>Administrador:</b> {}" \
                   "\nEliminó <code>{}</code> mensajes.".format(html.escape(chat.title),
                                                               mention_html(user.id, user.first_name),
                                                               delete_to - message_id)

                   #Original:
                   #\n#PURGE
                   #\n<b>Admin:</b> {}
                   #\nPurged <code>{}</code> messages.

    else:
        msg.reply_text("Respondé a un mensaje para seleccionar desde dónde comenzar a eliminar.")
                       #Original: Reply to a message to select where to start purging from.

    return ""


@run_async
@user_admin
@loggable
def del_message(bot: Bot, update: Update) -> str:
    if update.effective_message.reply_to_message:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        if can_delete(chat, bot.id):
            update.effective_message.reply_to_message.delete()
            update.effective_message.delete()
            return "<b>{}:</b>" \
                   "\n#DEL" \
                   "\n<b>Administrador:</b> {}" \
                   "\nMensaje borrado.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))

                   #Original:
                   #\n#DEL" \
                   #\n<b>Admin:</b> {}" \
                   #\nMessage deleted.
    else:
        update.effective_message.reply_text("¿Qué querés borrar?") #Original: Whadya want to delete?

    return ""


__help__ = """
*Solo para administradores:*
 - /del: borra el mensaje al que respondiste.
 - /purge: borra todos los mensajes entre este y el mensaje respondido.
 - /purge <valor>: borra el mensaje respondido y los X mensajes que le siguen.
"""

#Original:
#*Admin only:*
# - /del: deletes the message you replied to
# - /purge: deletes all messages between this and the replied to message.
# - /purge <integer X>: deletes the replied message, and X messages following it.

__mod_name__ = "Borrado" #Original: Purges

DELETE_HANDLER = CommandHandler("del", del_message, filters=Filters.group)
PURGE_HANDLER = CommandHandler("purge", purge, filters=Filters.group, pass_args=True)

dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(PURGE_HANDLER)
