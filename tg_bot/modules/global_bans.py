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
        message.reply_text("Parece que no te estás refiriendo a un usuario.") #Original: You don't seem to be referring to a user.
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Veo veo... ¿Qué veo? ¡PELEA DE ADMINS! ¿Por qué se están peleando ustedes dos?") #Original: I spy, with my little eye... a sudo user war! Why are you guys turning on each other?
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("OOOH ¡Alguien intenta banear globalmente a un usuario de soporte! *come palomitas*") #Original: OOOH someone's trying to gban a support user! *grabs popcorn*
        return

    if user_id == bot.id:
        message.reply_text("-_- Qué divertido, baneemos globalmente a mi mismo, total... Buen intento.") #Original: -_- So funny, lets gban myself why don't I? Nice try.
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("¡Eso no es un usuario!") #Original: That's not a user!
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text("Este usuario ya esta baneado globalmente; Podría cambiarle el motivo, pero no me has dado uno...")
            #Original: This user is already gbanned; I'd change the reason, but you haven't given me one...
            return

        success = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if success:
            message.reply_text("Este usuario ya esta baneado globalmente; Sin embargo, le cambié el motivo.")
            #Original: This user is already gbanned; I've gone and updated the gban reason though!
        else:
            message.reply_text("¿Te molesto si pruebas de nuevo? pensé que esta persona ya estaba baneada globalmente, ¿Pero ahora no?"
                               "Mi estar confundido.")
            #Original "Do you mind trying again? I thought this person was gbanned, but then they weren't? "
            #         "Am very confused"
        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if old_reason:
            message.reply_text("This user is already gbanned, for the following reason:\n"
                               "<code>{}</code>\n"
                               "I've gone and updated it with your new reason!".format(html.escape(old_reason)),
                               parse_mode=ParseMode.HTML)
        else:
            message.reply_text("This user is already gbanned, but had no reason set; I've gone and updated it!")

        return

    message.reply_text("*Sopla el polvo del martillo baneador*") #Original: *Blows dust off of banhammer* 😉

    banner = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} ha globalmente baneado a {} "
                 "porque:\n{}".format(mention_html(banner.id, banner.first_name),
                                       mention_html(user_chat.id, user_chat.first_name), reason or "No reason given"),
                 html=True)
                 #Original:
                 #{} is gbanning user {}
                 #because:\n{}
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
                message.reply_text("No pude banear globalmente porque: {}".format(excp.message))
                #Original: Could not gban due to: {}
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "No pude banear globalmente porque: {}".format(excp.message))
                #Original: Could not gban due to: {}
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "gban completado!")
    #Original: gban complete!
    message.reply_text("El usuario fue globalmente baneado.")
    #Original: Person has been gbanned.

@run_async
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Parece que no te estás refiriendo a un usuario.") #Original: You don't seem to be referring to a user.
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("¡Eso no es un usuario!") #Original: That's not a user!
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("¡Este usuario no esta globalmente baneado!") #Original: This user is not gbanned!
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("Le daré a {} una segunda chance, globalmente.".format(user_chat.first_name)) #Original: I'll give {} a second chance, globally.

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} ha desbaneado globalmente al usuario {}".format(mention_html(banner.id, banner.first_name),
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
                message.reply_text("No pude desbanear globalmente porque: {}".format(excp.message)) #Original: Could not un-gban due to: {}
                bot.send_message(OWNER_ID, "No pude desbanear globalmente porque: {}".format(excp.message)) #Original: Could not un-gban due to: {}
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "un-gban completado!") #Original: un-gban complete!

    message.reply_text("El usuario fue desbaneado globalmente.") #Original: Person has been un-gbanned.


@run_async
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text("¡No hay usuarios baneados globalmente! Eres más bondadoso de lo que pensaba...")
        #Original: There aren't any gbanned users! You're kinder than I expected...
        return

    banfile = 'Espanta a estos muchachos:\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="Esta es la lista de los usuarios baneados globalmente.") #Original: Here is the list of currently gbanned users.


def check_and_ban(update, user_id, should_message=True):
    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_text("Esta persona es mala, ¡No debería estar aquí!") #Original: This is a bad person, they shouldn't be here!


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
        if args[0].lower() in ["on", "si"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Activé los baneos globales en este grupo. Esto te ayudará a protegerte "
                                                "de spammers, personas desagradables, y los mayores trolls.")
            #Original: "I've enabled gbans in this group. This will help protect you "
            #          "from spammers, unsavoury characters, and the biggest trolls."
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Desactivé los baneos globales en este grupo. Tus usuarios no van a ser afectados por "
                                                "esto. ¡Sin embargo estarás menos protegido de cualquier "
                                                "troll o spammer")
            #Original: "I've disabled gbans in this group. GBans wont affect your users "
            #          "anymore. You'll be less protected from any trolls and spammers "
            #          "though!"
    else:
        update.effective_message.reply_text("Dame unos argumentos para elegir una opción! on/off, si/no!\n\n"
                                            "Tu configuración actual es: {}\n"
                                            "Cuando sea True, cualquier baneo global que ocurra también ocurrirá en tu grupo. "
                                            "Cuando sea False, no lo hará, dejandote en la posible merced de "
                                            "spammers.".format(sql.does_chat_gban(update.effective_chat.id)))
#Original: "Give me some arguments to choose a setting! on/off, yes/no!\n\n"
#          "Your current setting is: {}\n"
#          "When True, any gbans that happen will also happen in your group. "
#          "When False, they won't, leaving you at the possible mercy of "
#          "spammers."

def __stats__():
    return "{} usuarios globalmente baneados.".format(sql.num_gbanned_users())


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    text = "Globalmente baneado: <b>{}</b>"
    if is_gbanned:
        text = text.format("Yes")
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
- /gbanstat <on/off/si/no>: Deshabilita el efecto del ban global en tu grupo, o envia tus ajustes actuales.

Gbans, también conocido como baneo global, es usado por los creadores de bots para banear spammers por todos los grupos. Esto ayuda a protegerte \
a ti y a tu grupo removiendo el flood de los spammers lo más pronto posible. Puede ser desactivado para tu grupo si utilizas /gbanstat.
"""
#Original: """
#*Admin only:*
# - /gbanstat <on/off/yes/no>: Will disable the effect of global bans on your group, or return your current settings.
#
#Gbans, also known as global bans, are used by the bot owners to ban spammers across all groups. This helps protect \
#you and your groups by removing spam flooders as quickly as possible. They can be disabled for you group by calling \
#/gbanstat
#"""
__mod_name__ = "GBans"

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
