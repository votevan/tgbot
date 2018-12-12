import html
import json
import random
from datetime import datetime
from typing import Optional, List
import time
import requests
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from tg_bot.__main__ import STATS, USER_INFO
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters

RUN_STRINGS = (
)

SLAP_TEMPLATES = (
    "{user1} se hizo el piola y {user2} le rompió la jeta.",
    "{user1} usó los poderes de @votevan para romperle el celular a {user2}.",
    "{user1} envió un meme y {admin} lo muteó.",
)

ITEMS = (
)

THROW = (
)

HIT = (
)

ADMIN = (
     "@GastiRevol",
     "@manaosypitusas",
     "@manuell_15",
     "@SebAt0mix",
     "Francisco Zorat",
     "@Santy_TrabajadorDeSamsung",
     "@Gatica1996",
)

GMAPS_LOC = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_TIME = "https://maps.googleapis.com/maps/api/timezone/json"


@run_async
def runs(bot: Bot, update: Update):
    update.effective_message.reply_text(random.choice(RUN_STRINGS))


@run_async
def slap(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id:
        slapped_user = bot.get_chat(user_id)
        user1 = curr_user
        if slapped_user.username:
            user2 = "@" + escape_markdown(slapped_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(slapped_user.first_name,
                                                   slapped_user.id)

    # if no target found, bot targets the sender
    else:
        user1 = "[{}](tg://user?id={})".format(bot.first_name, bot.id)
        user2 = curr_user

    temp = random.choice(SLAP_TEMPLATES)
    item = random.choice(ITEMS)
    hit = random.choice(HIT)
    throw = random.choice(THROW)
    admin = random.choice(ADMIN)

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw, admin=admin)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)


@run_async
def get_bot_ip(bot: Bot, update: Update):
    """ Sends the bot's IP address, so as to be able to ssh in if necessary.
        OWNER ONLY.
    """
    res = requests.get("http://ipinfo.io/ip")
    update.message.reply_text(res.text)


@run_async
def get_id(bot: Bot, update: Update, args: List[str]):
    user_id = extract_user(update.effective_message, args)
    if user_id:
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.forward_from:
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            update.effective_message.reply_text(
                "ℹ️ ID de {}: `{}`.\nℹ️ ID del reenviador ({}): `{}`.".format(
                    escape_markdown(user2.first_name),
                    user2.id,
                    escape_markdown(user1.first_name),
                    user1.id),
                parse_mode=ParseMode.MARKDOWN)
        else:
            user = bot.get_chat(user_id)
            update.effective_message.reply_text("ℹ️ ID de {}: `{}`.".format(escape_markdown(user.first_name), user.id),
                                                parse_mode=ParseMode.MARKDOWN)
    else:
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == "private":
            update.effective_message.reply_text("ℹ️ Tu ID es `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)

        else:
            update.effective_message.reply_text("ℹ️ ID del grupo: `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)


@run_async
def info(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]
    user_id = extract_user(update.effective_message, args)

    if user_id:
        user = bot.get_chat(user_id)

    elif not msg.reply_to_message and not args:
        user = msg.from_user

    elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
        [MessageEntity.TEXT_MENTION]))):
        msg.reply_text("No puedo extraer la información de un usuario a partir de la información proporcionada.")
        return

    else:
        return

    text = "<b>⬇️ Información del usuario:</b>" \
           "\nℹ️ ID: <code>{}</code>" \
           "\nℹ️ Nombre: {}".format(user.id, html.escape(user.first_name))

    if user.last_name:
        text += "\nℹ️ Apellido: {}".format(html.escape(user.last_name))

    if user.username:
        text += "\nℹ️ Usuario: @{}".format(html.escape(user.username))

    text += "\nℹ️ Link del usuario: {}".format(mention_html(user.id, "link"))

    if user.id == OWNER_ID:
        text += "\n\n⚠️ Esta persona es mi creador. ¡Nunca haría nada contra el!"
    else:
        if user.id in SUDO_USERS:
            text += "\n\n⚠️ ¡Esta persona es uno de mis usuarios sudo! Es " \
                    "casi tan poderoso como mi dueño, así que tené cuidado."
        else:
            if user.id in SUPPORT_USERS:
                text += "\n\n⚠️ ¡Esta persona es uno de mis usuarios de soporte! " \
                        "No es exactamente un usuario sudo, pero puede borrarte del mapa."

            if user.id in WHITELIST_USERS:
                text += "\n\n⚠️ ¡Esta persona ha sido incluida en la lista blanca! " \
                        "Eso significa que no puedo banearlo/expulsarlo."

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def get_time(bot: Bot, update: Update, args: List[str]):
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text("Hora del ban 🔨")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    res = requests.get(GMAPS_LOC, params=dict(address=location))

    if res.status_code == 200:
        loc = json.loads(res.text)
        if loc.get('status') == 'OK':
            lat = loc['results'][0]['geometry']['location']['lat']
            long = loc['results'][0]['geometry']['location']['lng']

            country = None
            city = None

            address_parts = loc['results'][0]['address_components']
            for part in address_parts:
                if 'country' in part['types']:
                    country = part.get('long_name')
                if 'administrative_area_level_1' in part['types'] and not city:
                    city = part.get('long_name')
                if 'locality' in part['types']:
                    city = part.get('long_name')

            if city and country:
                location = "{}, {}".format(city, country)
            elif country:
                location = country

            timenow = int(datetime.utcnow().timestamp())
            res = requests.get(GMAPS_TIME, params=dict(location="{},{}".format(lat, long), timestamp=timenow))
            if res.status_code == 200:
                offset = json.loads(res.text)['dstOffset']
                timestamp = json.loads(res.text)['rawOffset']
                time_there = datetime.fromtimestamp(timenow + timestamp + offset).strftime("%H:%M")
                update.message.reply_text("🌎 Lugar: {}\n🕒 Hora: {}".format(location, time_there))


@run_async
def echo(bot: Bot, update: Update):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)
    message.delete()

@run_async
def ping(bot: Bot, update: Update):
    start_time = time.time()
    requests.get('https://api.telegram.org')
    end_time = time.time()
    ping_time = float(end_time - start_time)*1000
    update.effective_message.reply_text("ℹ️ La velocidad es: {}ms".format(ping_time))

@run_async
def gdpr(bot: Bot, update: Update):
    update.effective_message.reply_text("ℹ️ Eliminando tu información...")
    for mod in GDPR:
        mod.__gdpr__(update.effective_user.id)

    update.effective_message.reply_text("ℹ️ Tu información ha sido eliminada.\n\nEsto no te desbaneará "
                                        "de ningún grupo ya que eso es información de Telegram, no del bot. "
                                        "El flood, los warns, y el gban son respaldados. Para saber más, tocá  "
                                        "[acá](https://ico.org.uk/for-organisations/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/).",parse_mode=ParseMode.MARKDOWN)


MARKDOWN_HELP = """
Markdown es una herramienta de formato compatible con Telegram. {} tiene algunas mejoras para asegurarte de que \
los mensajes guardados se analicen correctamente y así permitirte crear botones.

➡️ <code>_italic_</code>: al envolver el texto con '_' se mostrará el texto en cursiva.
➡️ <code>*bold*</code>: al envolver el texto con '*' se mostrará el texto en negrita.
➡️ <code>`code`</code>: al envolver el texto con ''' se mostrará el texto monoespaciado, también conocido como 'código'.
➡️ <code>[sometext](someURL)</code>: esto creará un enlace; el mensaje solo mostrará <code>sometext</code>, \
y al tocarlo se abrirá la página en <code>someURL</code>.
Ejemplo: <code>[test](example.com)</code>

➡️ <code>[buttontext](buttonurl:someURL)</code>: esto sirve para permitir que los usuarios tengan \
botones en su markdown. <code>buttontext</code> será lo que se muestra en el botón, y <code>someURL</code> \
será la URL que se abrirá.
Ejemplo: <code>[Este es un botón](buttonurl:example.com)</code>

ℹ️ Si desea tener varios botones en la misma línea, use :same, como tal:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
Esto creará dos botones en una sola línea, en lugar de un botón por línea.

¡Tené en cuenta que tu mensaje <b>debe</b> contener algún texto que no sea solo un botón!
""".format(dispatcher.bot.first_name)


@run_async
def markdown_help(bot: Bot, update: Update):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text("Intentá reenviar el siguiente mensaje a mí, y lo verás!")
    update.effective_message.reply_text("/save test Esta es una prueba de markdown. _cursiva_, *negrita*, `código`, "
                                        "[URL](example.com) [button](buttonurl:github.com) "
                                        "[button2](buttonurl://google.com:same)")


@run_async
def stats(bot: Bot, update: Update):
    update.effective_message.reply_text("Estado actual:\n" + "\n".join([mod.__stats__() for mod in STATS]))


# /ip is for private use
__help__ = """
➡️ /id: obtener la ID del grupo actual. Si se usa respondiendo a un mensaje, obtiene la ID de ese usuario.
➡️ /runs: responde una cadena aleatoria de respuestas.
➡️ /slap: golpeá a un usuario, o sé golpeado si no respondes a nadie.
➡️ /time <lugar>: envía la hora local del lugar elegido.
➡️ /info: obtener información acerca de un usuario.
➡️ /gdpr: eliminar tu información de la base de datos del bot. Solo funciona mediante chats privados.
➡️ /markdownhelp: resumen rápido de cómo funciona el markdown en telegram: sólo se puede usar en chats privados.
➡️ /ping: conocer la velocidad de respuesta del bot.
"""

__mod_name__ = "Misc."

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=Filters.chat(OWNER_ID))

TIME_HANDLER = CommandHandler("time", get_time, pass_args=True)

RUNS_HANDLER = DisableAbleCommandHandler("runs", runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, pass_args=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)
PING_HANDLER = DisableAbleCommandHandler("ping", ping)

ECHO_HANDLER = CommandHandler("echo", echo, filters=Filters.user(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)

STATS_HANDLER = CommandHandler("stats", stats, filters=CustomFilters.sudo_filter)
GDPR_HANDLER = CommandHandler("gdpr", gdpr, filters=Filters.private)

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(IP_HANDLER)
dispatcher.add_handler(TIME_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
dispatcher.add_handler(GDPR_HANDLER)
dispatcher.add_handler(PING_HANDLER)
