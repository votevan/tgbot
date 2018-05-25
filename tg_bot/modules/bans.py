import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, BAN_STICKER, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Parece que no estás haciendo referencia a un usuario.") #Original: You don't seem to be referring to a user.
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("No puedo encontrar a este usuario.") #Original: I can't seem to find this user
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Desearía poder banear administradores...") #Original: I really wish I could ban admins...
        return ""

    if user_id == bot.id:
        message.reply_text("No me voy a banear a mi mismo, ¿Estás loco?") #Original: I'm not gonna BAN myself, are you crazy?
        return ""

    log = "<b>{}:</b>" \
          "\n#BANEADO" \
          "\n<b>Administrador:</b> {}" \
          "\n<b>Usuario:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    #Original "<b>{}:</b>" \
    #      "\n#BANNED" \
    #      "\n<b>Admin:</b> {}" \
    #      "\n<b>User:</b> {}"
    if reason:
        log += "\n<b>Razón:</b> {}".format(reason) #Original: \n<b>Reason:</b> {}

    try:
        chat.kick_member(user_id)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("¡Baneado!") #Original: Banned!
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('Banned!', quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR baneando al usuario %s en el chat %s (%s) debido a %s", user_id, chat.title, chat.id, excp.message) #Original: ERROR banning user %s in chat %s (%s) due to %s
            message.reply_text("Demonios, no puedo banear a ese usuario.") #Original: Well damn, I can't ban that user.

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Parece que no puedo encontrar a este usuario.") #Original: You don't seem to be referring to a user.
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Parece que no puedo encontrar a este usuario.") #Original: I can't seem to find this user
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Desearía poder banear administradores...") #Original: I really wish I could ban admins...
        return ""

    if user_id == bot.id:
        message.reply_text("No me voy a banear a mi mismo, ¿Estás loco?") #Original: I'm not gonna BAN myself, are you crazy?
        return ""

    if not reason:
        message.reply_text("¡No especificaste un tiempo de baneo para este usuario!") #Original: You haven't specified a time to ban this user for!
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return ""

    log = "<b>{}:</b>" \
          "\n#BANEADO TEMPORALMENTE" \
          "\n<b>Admin:</b> {}" \
          "\n<b>Usuario:</b> {}" \
          "\n<b>Tiempo:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
      #Original"<b>{}:</b>" \
      #    "\n#TEMP BANNED" \
      #    "\n<b>Admin:</b> {}" \
      #    "\n<b>User:</b> {}" \
      #    "\n<b>Time:</b> {}"
    if reason:
        log += "\n<b>Razón:</b> {}".format(reason) #Original: \n<b>Reason:</b> {}

    try:
        chat.kick_member(user_id, until_date=bantime)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("¡Baneado! El usuario será baneado por {}.".format(time_val)) #Original: Banned! User will be banned for {}.
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("Banned! User will be banned for {}.".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR baneando al usuario %s en el chat %s (%s) debido a %s", user_id, chat.title, chat.id, #Original: ERROR banning user %s in chat %s (%s) due to %s
                             excp.message)
            message.reply_text("Demonios, no puedo banear a ese usuario.") #Original: Well damn, I can't ban that user.

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def kick(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Parece que no puedo encontrar a este usuario.") #Original: I can't seem to find this user
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id):
        message.reply_text("Desearía poder expulsar administradores...") #Original: I really wish I could kick admins...
        return ""

    if user_id == bot.id:
        message.reply_text("No voy a hacer eso.") #Original Yeahhh I'm not gonna do that
        return ""

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("Kicked!")
        log = "<b>{}:</b>" \
              "\n#KICKEADO" \
              "\n<b>Admin:</b> {}" \
              "\n<b>Usuario:</b> {}".format(html.escape(chat.title),
                                         mention_html(user.id, user.first_name),
                                         mention_html(member.user.id, member.user.first_name))
          #Original: "<b>{}:</b>" \
          #    "\n#KICKED" \
          #    "\n<b>Admin:</b> {}" \
          #    "\n<b>User:</b> {}"
        if reason:
            log += "\n<b>Razón:</b> {}".format(reason) #Original: "\n<b>Reason:</b> {}"

        return log

    else:
        message.reply_text("Demonios, no puedo expulsar a ese usuario.") #Original: Well damn, I can't kick that user.

    return ""


@run_async
@bot_admin
@can_restrict
def kickme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Desearia poder hacerlo... pero eres un administrador.") #Original: I wish I could... but you're an admin.
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("No hay problema.") #Original: No problem.
    else:
        update.effective_message.reply_text("¿Qué? No puedo :/") #Original: Huh? I can't :/


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Parece que no puedo encontrar a este usuario.") #Original: I can't seem to find this user
            return ""
        else:
            raise

    if user_id == bot.id:
        message.reply_text("¿Cómo podria desbanearme si no estuviera aquí...?") #Original: How would I unban myself if I wasn't here...?
        return ""

    if is_user_in_chat(chat, user_id):
        message.reply_text("¿Por qué tratas de desbanear a alguien que ya está en el grupo?") #Original: Why are you trying to unban someone that's already in the chat?
        return ""

    chat.unban_member(user_id)
    message.reply_text("¡Usuario desbaneado correctamente!") #Original: Yep, this user can join!

    log = "<b>{}:</b>" \
          "\n#DESBANEADO" \
          "\n<b>Admin:</b> {}" \
          "\n<b>Usuario:</b> {}".format(html.escape(chat.title),
                                     mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
      #Original "<b>{}:</b>" \
      #    "\n#UNBANNED" \
      #    "\n<b>Admin:</b> {}" \
      #    "\n<b>User:</b> {}"
    if reason:
        log += "\n<b>Razón:</b> {}".format(reason) #Original Reason

    return log


__help__ = """
 - /kickme: expulsa a la persona que ha utilizado el comando.

*Solo para administradores:*
 - /ban <nombre_de_usuario>: banea a un usuario. (via alias o respuesta)
 - /tban <nombre_de_usuario> x(m/h/d): banea a un usuario por x tiempo. (via alias o respuesta). m = minutos, h = horas, d = días.
 - /unban <nombre_de_usuario>: desbanea a un usuario. (via alias o respuesta)
 - /kick <nombre_de_usuario>: expulsa a un usuario. (via alias o respuesta)
"""

#Original:
#- /kickme: kicks the user who issued the command
#
#*Admin only:*
# - /ban <userhandle>: bans a user. (via handle, or reply)
# - /tban <userhandle> x(m/h/d): bans a user for x time. (via handle, or reply). m = minutes, h = hours, d = days.
# - /unban <userhandle>: unbans a user. (via handle, or reply)
# - /kick <userhandle>: kicks a user, (via handle, or reply)

__mod_name__ = "Ban"

BAN_HANDLER = CommandHandler("ban", ban, pass_args=True, filters=Filters.group)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True, filters=Filters.group)
KICK_HANDLER = CommandHandler("kick", kick, pass_args=True, filters=Filters.group)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True, filters=Filters.group)
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=Filters.group)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
