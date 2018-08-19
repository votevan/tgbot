import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@user_admin
@loggable
def mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Necesitás darme un nombre de usuario para silenciar, o responderle algún para silenciarlo.")
                           #Original: You'll need to either give me a username to mute, or reply to someone to be muted.
        return ""

    if user_id == bot.id:
        message.reply_text("I'm not muting myself!") #Original: ¡No me voy a silenciar!
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("¡No puedo evitar que un administrador hable!") #Original: Afraid I can't stop an admin from talking!

        elif member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, can_send_messages=False)
            message.reply_text("¡Silenciado!") #Original: Muted!
            return "<b>{}:</b>" \
                   "\n#MUTE" \
                   "\n<b>Administrador:</b> {}" \
                   "\n<b>Usuario:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))

                   #Original:
                   #\n#MUTE
                   #\n<b>Admin:</b> {}
                   #\n<b>User:</b> {}

        else:
            message.reply_text("¡Este usuario ya está silenciado!") #Original: This user is already muted!
    else:
        message.reply_text("¡Este usuario no está en el chat!") #Original: This user isn't in the chat!

    return ""


@run_async
@bot_admin
@user_admin
@loggable
def unmute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Necesitas darme un alias para quitar el silencio o responderle para que lo haga.")
                           #Original: You'll need to either give me a username to unmute, or reply to someone to be unmuted.
        return ""

    member = chat.get_member(int(user_id))    if member.status != 'kicked' and member.status != 'left':
        if member.can_send_messages and member.can_send_media_messages \
                and member.can_send_other_messages and member.can_add_web_page_previews:
            message.reply_text("Este usuario ya tiene derecho a hablar.") #Original: This user already has the right to speak.
        else:
            bot.restrict_chat_member(chat.id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)
            message.reply_text("Desilenciado!")
            return "<b>{}:</b>" \
                   "\n#MUTE" \
                   "\n<b>Administrador:</b> {}" \
                   "\n<b>Usuario:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))

                   #Original:
                   #\n#MUTE
                   #\n<b>Administrador:</b> {}
                   #\n<b>Usuario:</b> {}
    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("This is an admin, what do you expect me to do?")
            return ""

        elif member.status != 'kicked' and member.status != 'left':
            if member.can_send_messages and member.can_send_media_messages \
                    and member.can_send_other_messages and member.can_add_web_page_previews:
                message.reply_text("This user already has the right to speak.")
                return ""
            else:
                bot.restrict_chat_member(chat.id, int(user_id),
                                         can_send_messages=True,
                                         can_send_media_messages=True,
                                         can_send_other_messages=True,
                                         can_add_web_page_previews=True)
                message.reply_text("Unmuted!")
                return "<b>{}:</b>" \
                       "\n#UNMUTE" \
                       "\n<b>Admin:</b> {}" \
                       "\n<b>User:</b> {}".format(html.escape(chat.title),
                                                  mention_html(user.id, user.first_name),
                                                  mention_html(member.user.id, member.user.first_name))
    else:
        message.reply_text("Este usuario ni siquiera está en el chat. ¡Si les quitás el silencio, no les hará hablar "
                           "más de lo que ya lo hacen!")
                           #Original:
                           #This user isn't even in the chat, unmuting them won't make them talk more than they
                           #already do!

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("No te estás refiriendo a un usuario.") #You don't seem to be referring to a user.
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("No pude encontrar a este usuario.") #Original: I can't seem to find this user
            return ""
        else:
            raise

    if is_user_admin(chat, user_id, member):
        message.reply_text("Me gustaría poder silenciar administradores ...") #Original: I really wish I could mute admins...
        return ""

    if user_id == bot.id:
        message.reply_text("No me voy a silenciar, ¿estás loco?") #Original: I'm not gonna MUTE myself, are you crazy?
        return ""

    if not reason:
        message.reply_text("¡No especificaste el tiempo para silenciar a este usuario!") #Original: You haven't specified a time to mute this user for!
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP MUTED" \
          "\n<b>Administrador:</b> {}" \
          "\n<b>Usuario:</b> {}" \
          "\n<b>Tiempo:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)

          #\n#TEMP MUTED
          #\n<b>Admin:</b> {}
          #\n<b>User:</b> {}
          #\n<b>Time:</b> {}

    if reason:
        log += "\n<b>Razón:</b> {}".format(reason) #Original: Reason:

    try:
        if member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, until_date=mutetime, can_send_messages=False)
            message.reply_text("¡Silenciado por {}!".format(time_val)) #Original: Muted for {}!
            return log
        else:
            message.reply_text("Este usuario ya está silenciado.") #Original: This user is already muted.

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("¡Silenciado por {}!".format(time_val), quote=False) #Original: Muted for {}!
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR silenciando al usuario %s en chat %s (%s) debido a %s.", user_id, chat.title, chat.id,
                             excp.message)
                             #Original: ERROR muting user %s in chat %s (%s) due to %s

            message.reply_text("¡Maldición! No puedo silenciar a ese usuario.") #Original: Well damn, I can't mute that user.

    return ""


__help__ = """
*Solo para administradores:*
 - /mute <usuario>: silencia a un usuario. También se puede usar respondiendo: silencia al usuario respondido.
 - /tmute <usuario> x(m/h/d): silencia a un usuario por x tiempo. (a través de alias o respuesta). m = minutos, h = horas, d = días.
 - /unmute <usuario>: deja de silenciar a un usuario. También se puede usar como respuesta: silencia al usuario respondido.
"""

#Original:
#*Admin only:*
# - /mute <userhandle>: silences a user. Can also be used as a reply, muting the replied to user.
# - /tmute <userhandle> x(m/h/d): mutes a user for x time. (via handle, or reply). m = minutes, h = hours, d = days.
# - /unmute <userhandle>: unmutes a user. Can also be used as a reply, muting the replied to user.

__mod_name__ = "Silencios"

MUTE_HANDLER = CommandHandler("mute", mute, pass_args=True, filters=Filters.group)
UNMUTE_HANDLER = CommandHandler("unmute", unmute, pass_args=True, filters=Filters.group)
TEMPMUTE_HANDLER = CommandHandler(["tmute", "tempmute"], temp_mute, pass_args=True, filters=Filters.group)

dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)
