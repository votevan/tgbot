import html
from typing import Optional, List

from telegram import Message, Update, Bot, User
from telegram import ParseMode, MAX_MESSAGE_LENGTH
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.userinfo_sql as sql
from tg_bot import dispatcher, SUDO_USERS
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user


@run_async
def about_me(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]
    user_id = extract_user(message, args)

    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_me_info(user.id)

    if info:
        update.effective_message.reply_text("*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        update.effective_message.reply_text(username + " no ha establecido un mensaje de información sobre ellos todavia!")
#Orignal: " hasn't set an info message about themselves  yet!"
    else:
        update.effective_message.reply_text("¡Aún no estableciste un mensaje de información sobre ti!")
#Original: "You haven't set an info message about yourself yet!"

@run_async
def set_about_me(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    user_id = message.from_user.id
    text = message.text
    info = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
    if len(info) == 2:
        if len(info[1]) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_me_info(user_id, info[1])
            message.reply_text("¡Tu info esta actualizada!")
#Original: "Updated your info!"
        else:
            message.reply_text(
                "¡Tu info tiene que tener menos de {} caracteres! Tienes {}.".format(MAX_MESSAGE_LENGTH // 4, len(info[1])))
#Original: "Your info needs to be under {} characters! You have {}."

@run_async
def about_bio(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_bio(user.id)

    if info:
        update.effective_message.reply_text("*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = user.first_name
        update.effective_message.reply_text("¡{} no estableció un conjunto de mensaje sobre ellos todavía!".format(username))
#Original: "{} hasn't had a message set about themselves yet!"
    else:
        update.effective_message.reply_text("¡No estableciste un conjunto de biografía sobre tí todavía!")
#Original: "You haven't had a bio set about yourself yet!"


@run_async
def set_about_bio(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    sender = update.effective_user  # type: Optional[User]
    if message.reply_to_message:
        repl_message = message.reply_to_message
        user_id = repl_message.from_user.id
        if user_id == message.from_user.id:
            message.reply_text("Ha, ¡No puedes establecer tu propia biografía! Estaś a merced de otros aquí...")
#Original: "Ha, you can't set your own bio! You're at the mercy of others here..."
            return
        elif user_id == bot.id and sender.id not in SUDO_USERS:
            message.reply_text("Emm... se, yo solo confío en los administradores para cambiar mi biografía.")
#Original: "Erm... yeah, I only trust sudo users to set my bio."
            return

        text = message.text
        bio = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
        if len(bio) == 2:
            if len(bio[1]) < MAX_MESSAGE_LENGTH // 4:
                sql.set_user_bio(user_id, bio[1])
                message.reply_text("¡Actualizado la biografía de {}!".format(repl_message.from_user.first_name))
#Original: Updated {}'s bio!
            else:
                message.reply_text(
                    "Una biografía debe tener menos de {} caracteres! Trataste de poner {}.".format(
                        MAX_MESSAGE_LENGTH // 4, len(bio[1])))
#Original: "A bio needs to be under {} characters! You tried to set {}."
    else:
        message.reply_text("¡Responde al mensaje de alguien para editar su biografía!")
#Original: "Reply to someone's message to set their bio!"


def __user_info__(user_id):
    bio = html.escape(sql.get_user_bio(user_id) or "")
    me = html.escape(sql.get_user_me_info(user_id) or "")
    if bio and me:
        return "<b>Acerca del usuario:</b>\n{me}\n<b>Qué dicen los demás:</b>\n{bio}".format(me=me, bio=bio)
#Original: "<b>About user:</b>\n{me}\n<b>What others say:</b>\n{bio}"
    elif bio:
        return "<b>Qué dicen los demás:</b>\n{bio}\n".format(me=me, bio=bio)
#Original: "<b>What others say:</b>\n{bio}\n"
    elif me:
        return "<b>Acerca del usuario:</b>\n{me}""".format(me=me, bio=bio)
#Original "<b>About user:</b>\n{me}"""
    else:
        return ""


__help__ = """
 - /setbio <texto>: mientras respondas, guarda la biografía de otro usuario.
 - /bio: Retorna tu biografía o la de otro usuario. No puede ser editado por tí.
 - /setme <texto>: Guarda tu información.
 - /me: Retorna tu info o la de otro usuario.
"""

#Original: """
# - /setbio <text>: while replying, will save another user's bio
# - /bio: will get your or another user's bio. This cannot be set by yourself.
# - /setme <text>: will set your info
# - /me: will get your or another user's info
#"""

__mod_name__ = "Bios and Abouts"

SET_BIO_HANDLER = DisableAbleCommandHandler("setbio", set_about_bio)
GET_BIO_HANDLER = DisableAbleCommandHandler("bio", about_bio, pass_args=True)

SET_ABOUT_HANDLER = DisableAbleCommandHandler("setme", set_about_me)
GET_ABOUT_HANDLER = DisableAbleCommandHandler("me", about_me, pass_args=True)

dispatcher.add_handler(SET_BIO_HANDLER)
dispatcher.add_handler(GET_BIO_HANDLER)
dispatcher.add_handler(SET_ABOUT_HANDLER)
dispatcher.add_handler(GET_ABOUT_HANDLER)
