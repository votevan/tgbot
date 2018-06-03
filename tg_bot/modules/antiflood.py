import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(bot: Bot, update: Update) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if not user:  # ignore channels
        return ""

    # ignore admins
    if is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        chat.kick_member(user.id)
        msg.reply_text("Me gusta que haya actividad en el grupo, pero tú, tú solo eres una decepción. Sal de aquí.")

                       #Original:
                       #I like to leave the flooding to natural disasters. But you, you were just a
                       #disappointment. Get out.

        return "<b>{}:</b>" \
               "\n#BANEADO" \
               "\n<b>Usuario:</b> {}" \
               "\nFloodeó el grupo.".format(html.escape(chat.title),
                                             mention_html(user.id, user.first_name))
               #Original:
               #\nBANNED
               #\n<b>User:</b> {}
               #\nFlooded the group. 
   
    except BadRequest:
        msg.reply_text("No puedo expulsar usuarios aquí, ¡dame permisos antes! Hasta entonces, deshabilitaré el antiflood.")
        sql.set_flood(chat.id, 0)
        return "<b>{}:</b>" \
               "\n#INFORMACIÓN" \
               "\nNo tengo permisos de expulsión; desactivaré el antiflood.".format(chat.title)
 
               #Original:
               #\nINFO
               #\nDon't have kick permissions, so automatically disabled antiflood.  

@run_async
@user_admin
@can_restrict
@loggable
def set_flood(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat.id, 0)
            message.reply_text("Antiflood has been disabled.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat.id, 0)
                message.reply_text("He desactivado el antiflood.")
                return "<b>{}:</b>" \
                       "\n#FLOOD" \
                       "\n<b>Administrador:</b> {Antiflood has been disabled.}" \
                       "\nAntiflood desactivado.".format(html.escape(chat.title), mention_html(user.id, user.first_name))
                       
                       #Original:
                       #\nETFLOOD
                       #\n<b>Admin:</b> {Antiflood has been disabled.}
                       #\nDisabled antiflood.

            elif amount < 3:
                message.reply_text("¡El antiflood debe ser configurado a 0 (desactivado), o un número mayor a 3!")

                                   #Original: Antiflood has to be either 0 (disabled), or a number bigger than 3!
                return ""

            else:
                sql.set_flood(chat.id, amount)
                message.reply_text("El antiflood ha sido actualizado y configurado a {}".format(amount))

                                   #Original: Antiflood has been updated and set to {}.
                return "<b>{}:</b>" \
                       "\n#FLOOD" \
                       "\n<b>Administrador:</b> {}" \
                       "\nAntiflood configurado a <code>{}</code>.".format(html.escape(chat.title),
                                                                    mention_html(user.id, user.first_name), amount)

                       #\n#SETFLOOD
                       #\n<b>Admin:</b> {}
                       #\nSet antiflood to <code>{}</code>.

        else:
            message.reply_text("Argumento no reconocido; usa un número, 'off', o 'no'.")

                               #Original: Unrecognised argument - please use a number, 'off', or 'no'.

    return ""


@run_async
def flood(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    limit = sql.get_flood_limit(chat.id)
    if limit == 0:
        update.effective_message.reply_text("¡El antiflood está desactivado!")

                                            #Original: I'm not currently enforcing flood control!                                  

    else:
        update.effective_message.reply_text(
            "El antiflood está configurado a {} mensajes consecutivos.".format(limit))

            #Original: I'm currently banning users if they send more than {} consecutive messages.

def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "*Not* currently enforcing flood control."
    else:
        return "Antiflood is set to `{}` messages.".format(limit)


__help__ = """
 - /flood: obtiene la configuración actual de flood.

*Solo para administradores:*
 - /setflood <número/'no'/'off'>: Activa o desactiva el antiflood.

Si activas el control de flood, significa que el usuario que envie mas de X mensajes consecutivos será baneado.

*Esta configuración no afecta a los administradores.*
"""	

#Original:
# - /flood: Get the current flood control setting
# *Admin only:*
# - /setflood <int/'no'/'off'>: enables or disables flood control

__mod_name__ = "AntiFlood"

FLOOD_BAN_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.group, check_flood)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, pass_args=True, filters=Filters.group)
FLOOD_HANDLER = CommandHandler("flood", flood, filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)
