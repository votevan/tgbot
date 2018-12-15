import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.global_bans_sql as sql
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat"
}

UNGBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Method is available for supergroup and channel chats only",
    "Not in the chat",
    "Channel_private",
    "Chat_admin_required",
}


@run_async
def gban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Parece que no te estás refiriendo a un usuario.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Veo veo... ¿Qué veo? ¡PELEA DE ADMINS! ¿Por qué se están peleando ustedes dos?")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("OOOH ¡Alguien intenta banear globalmente a un usuario de soporte! *come palomitas*") 
        return

    if user_id == bot.id:
        message.reply_text("-_- Qué divertido, baneemos globalmente a mi mismo, total... Buen intento.")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("¡Eso no es un usuario!")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text("❌ Este usuario ya esta baneado globalmente; Podría cambiarle el motivo, pero no me has dado uno...")
            return

        success = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if success:
            message.reply_text("ℹ️ Este usuario ya esta baneado globalmente; Sin embargo, le cambié el motivo.")
        else:
            message.reply_text("¿Te molesto si pruebas de nuevo? pensé que esta persona ya estaba baneada globalmente, ¿Pero ahora no?"
                               "Mi estar confundido.")

        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if old_reason:
            message.reply_text("ℹ️ Este usuario ya estaba baneado globalmente por el motivo:\n"
                               "<code>{}</code>\n"
                               "Lo he actualizado con el nuevo motivo.".format(html.escape(old_reason)),
                               parse_mode=ParseMode.HTML)
        else:
            message.reply_text("This user is already gbanned, but had no reason set; I've gone and updated it!")

        return

    message.reply_text("mmmm hora del gban")
    banner = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "ℹ️ {} baneó globalmente a {}."
                 "\nMotivo: {}".format(mention_html(banner.id, banner.first_name),
                                       mention_html(user_chat.id, user_chat.first_name), reason or "Motivo no dado."),
                 html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.kick_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text("❌ No pude banear globalmente porque: {}".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "❌ No pude banear globalmente porque: {}".format(excp.message))
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "✅ Gban completado!")
    message.reply_text("ℹ️ El usuario fue globalmente baneado.")

@run_async
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Parece que no te estás refiriendo a un usuario.") 
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("¡Eso no es un usuario!") 
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("¡Este usuario no esta globalmente baneado!") 
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("‼️ Le voy a dar a {} una segunda chance, globalmente.".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "ℹ️ {} ha desbaneado globalmente al usuario {}".format(mention_html(banner.id, banner.first_name),
                                                   mention_html(user_chat.id, user_chat.first_name)),
                 html=True)
                 #Original: {} has ungbanned user {}

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text("❌ No pude desbanear globalmente porque: {}".format(excp.message)) #Original: Could not un-gban due to: {}
                bot.send_message(OWNER_ID, "❌ No pude desbanear globalmente porque: {}".format(excp.message)) #Original: Could not un-gban due to: {}
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "✅ Un-gban completado!") #Original: un-gban complete!

    message.reply_text("ℹ️ El usuario fue desbaneado globalmente.") #Original: Person has been un-gbanned.


@run_async
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text("ℹ️ ¡No hay usuarios baneados globalmente! Sos más bondadoso de lo que pensaba...")

        return

    banfile = 'Espanta a estos muchachos:\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Motivo: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="Esta es la lista de los usuarios baneados globalmente ⬇️") 


def check_and_ban(update, user_id, should_message=True):
    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_text("Esta persona es mala, ¡No debería estar acá!")


@run_async
def enforce_gban(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
def gbanstat(bot: Bot, update: Update, args: List[str]):
    if len(args) > 0:
        if args[0].lower() in ["si"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("✅ Activé los baneos globales en este grupo. Esto te ayudará a protegerte "
                                                "de spammers, personas desagradables, y los mayores trolls.")

        elif args[0].lower() in ["no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("ℹ️ Desactivé los baneos globales en este grupo. Tus usuarios no van a ser afectados por "
                                                "esto. ¡Sin embargo estarás menos protegido de cualquier "
                                                "troll o spammer")

    else:
        update.effective_message.reply_text("ℹ️ Argumentos: 'si'/'no'.\n\n"
                                            "Tu configuración actual es: {}\n"
                                            "Cuando sea 'si', cualquier baneo global que ocurra también ocurrirá en tu grupo. "
                                            "Cuando sea 'no', no lo hará, dejandote en la posible merced de " 
                                            "spammers.".format(sql.does_chat_gban(update.effective_chat.id)))

def __stats__():
    return "ℹ️ {} usuarios globalmente baneados.".format(sql.num_gbanned_users())


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    text = "ℹ️ Globalmente baneado: <b>{}</b>"
    if is_gbanned:
        text = text.format("Si")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += "\nRazón: {}".format(html.escape(user.reason))
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat is enforcing *gbans*: `{}`.".format(sql.does_chat_gban(chat_id))


__help__ = """
*Solo administradores:*
- /gbanstat <si/no>: Deshabilita el efecto del baneo global en tu grupo, o envia tus ajustes actuales.

Gbans, también conocido como baneos globales, es usado por los creadores de bots para banear spammers por todos los grupos. Esto ayuda a protegerte
a vos y a tu grupo eliminando el flood de los spammers lo más pronto posible. Puede ser desactivado para tu grupo si usás /gbanstat.
"""

__mod_name__ = "Gbans"

GBAN_HANDLER = CommandHandler("gban", gban, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_LIST = CommandHandler("gbanlist", gbanlist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GBAN_STATUS = CommandHandler("gbanstat", gbanstat, pass_args=True, filters=Filters.group)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
