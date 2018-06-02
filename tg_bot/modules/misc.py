import html
import json
import random
from datetime import datetime
from typing import Optional, List

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
    "¿A dónde crees que vas?",
    "¿Huh? ¿Qué? se escaparon?",
    "ZZzzZZzz... Huh? ¿Qué? oh, solo ellos otra vez, no importa.",
    "¡Regresa aquí!",
    "No tan rapido...",
    "¡Cuidado con la pared!",
    "¡No me dejes solo con ellos!",
    "Usted corre, usted muere.",
    "Bromas sobre ti, estoy en todas partes",
    "Te arrepentirás de ...",
    "También puedes probar / kickme, escuché que es divertido.",
    "Ve a molestar a alguien más, aquí a nadie le importa..",
    "Puedes correr, pero no puedes esconderte.",
    "¿Es todo lo que tienes?",
    "Estoy detrás tuyo...",
    "¡Tienes compañía!",
    "Podemos hacer esto de la manera fácil o por el camino difícil.",
    "Simplemente no lo entiendes, ¿verdad?",
    "Sí, será mejor que corras!",
    "Por favor, recuérdame cuánto me importa??",
    "Yo correría más rápido si fuera tú.",
    "Ese es definitivamente el droide que estamos buscando.",
    "Que las probabilidades estén siempre a tu favor.",
    "¿Tus últimas palabras?",
    "Y desaparecieron para siempre, nunca más serán vistos.",
    "\"¡Oh, mírame! ¡Soy tan genial, puedo huir de un robot!\" - esta persona",
    "Sí, sí, solo toca /kickme ya.",
    "Aquí, toma este anillo y dirígete a Mordor mientras lo haces.",
    "Cuenta la leyenda, todavía están funcionando ...",
    "A diferencia de Harry Potter, tus padres no pueden protegerte de mí.",
    "El miedo lleva a la ira. La ira conduce al odio. El odio lleva al sufrimiento. Si sigues corriendo con miedo, es posible que... "
    "Sé el próximo Vader.",
    "Múltiples cálculos más tarde, he decidido que mi interés en tus chistes y es exactamente 0.",
    "Cuenta la leyenda, todavía están en ejecución.",
    "Sigue así, no estoy seguro de que te queramos aquí de todos modos.",
    "Eres una hechi... Oh. Espere. No, eres Harry.",
    "NO HAY CORRER EN LOS PASILLOS!",
    "Hasta la vista, baby.",
    "¿Quién soltó los perros?",
    "Es gracioso, porque a nadie le importa.",
    "Ah, qué desperdicio. Me gustó ese.",
    "Francamente, querida, no me importa nada.",
    "Mi batido trae a todos los niños al patio ... ¡Así que corre más rápido!",
    "¡No puedes MANEJAR la verdad!",
    "Hace mucho tiempo, en una galaxia muy lejana ... Alguien se habría preocupado por eso. Sin embargo, a nadie le importo.",
    "¡Oye, míralos! Están huyendo del inevitable y lindo banhammer...",
    "Han disparó primero. Yo lo haré.",
    "¿Qué estás persiguiendo, un conejo blanco?",
    "Como el Doctor diría ... ¡CORRE!",
)

SLAP_TEMPLATES = (
    "{user1} {hits} a {user2} con {item}.",
    "{user1} {hits} a {user2} en la cara con {item}.",
    "{user1} {hits} a {user2} un ratito con {item}.",
    "{user1} le {throws} {item} a {user2}.",
    "{user1} agarra {item} y lo {throws} en la cara de {user2}.",
    "{user1} lanza un {item} en la dirección de {user2}.",
    "{user1} comienza a abofetear a {user2} con {item}.",
    "{user1} le saca los ojos a {user2} con una cuchara.",
    "{user1} toma un {item} y {hits} a {user2} con él.",
    "{user1} ata a {user2} a una silla y {throw} un {item} a el",
    "{user1} da un empujón amistoso para ayudar a {user2} a aprender a nadar en lava",
    "{user1} {throw} {item} en la dirección de {user2}" 
)

ITEMS = (
     "un bate de béisbol",
     "un amplificador",
     "un Monitor CRT",
     "un libro de texto de física",
     "un Nokia 1100",
     "un retrato",
     "un televisor",
     "un camión de cinco toneladas",
     "un rollo de cinta adhesiva",
     "un libro",
     "un ordenador portátil",
     "untelevisor antiguo",
     "un saco de rocas",
     "un pollo de goma",
     "un bate de púas",
     "un extintor de incendios",
     "un pedazo de tierra",
     "un pedazo de carne podrida",
     "un oso de peluche",
     "un ladrillo",
     "un destornillador",
     "una cuchara",
     "una sartén",
)

THROW = (
     "tira",
     "arroja",
     "lanza",
)

HIT = (
     "golpea",
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

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

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
                "El remitente original, {}, tiene la ID `{}`.\nEl reenviador, {}, tiene la ID `{}`.".format(
                    escape_markdown(user2.first_name),
                    user2.id,
                    escape_markdown(user1.first_name),
                    user1.id),
                parse_mode=ParseMode.MARKDOWN)
        else:
            user = bot.get_chat(user_id)
            update.effective_message.reply_text("La ID de {} es `{}`.".format(escape_markdown(user.first_name), user.id),
                                                parse_mode=ParseMode.MARKDOWN)
    else:
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == "private":
            update.effective_message.reply_text("Tu ID es `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)

        else:
            update.effective_message.reply_text("La ID de este grupo es `{}`.".format(chat.id),
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

    text = "<b>Información del usuario:</b>:" \
           "\nID: <code>{}</code>" \
           "\nNombre: {}".format(user.id, html.escape(user.first_name))

    if user.last_name:
        text += "\nApellido: {}".format(html.escape(user.last_name))

    if user.username:
        text += "\nUsuario: @{}".format(html.escape(user.username))

    text += "\nLink del usuario: {}".format(mention_html(user.id, "link"))

    if user.id == OWNER_ID:
        text += "\n\nEsta persona es mi dueño. ¡Nunca haría nada contra el!"
    else:
        if user.id in SUDO_USERS:
            text += "\nEsta persona es uno de mis usuarios sudo! Es" \
                    "casi tan poderoso como mi dueño, así que ten cuidado."
        else:
            if user.id in SUPPORT_USERS:
                text += "\n¡Esta persona es uno de mis usuarios de soporte! " \
                        "No es exactamente un usuario sudo, pero puede eliminarte del mapa."

            if user.id in WHITELIST_USERS:
                text += "\n¡Esta persona ha sido incluida en la lista blanca! " \
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
        update.effective_message.reply_text("¡Siempre hay tiempo del martillo de ban para mi!")
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

            timenow = int(datetime.utcnow().strftime("%s"))
            res = requests.get(GMAPS_TIME, params=dict(location="{},{}".format(lat, long), timestamp=timenow))
            if res.status_code == 200:
                offset = json.loads(res.text)['dstOffset']
                timestamp = json.loads(res.text)['rawOffset']
                time_there = datetime.fromtimestamp(timenow + timestamp + offset).strftime("%H:%M:%S on %A %d %B")
                update.message.reply_text("Son las {} en {}".format(time_there, location))


@run_async
def echo(bot: Bot, update: Update):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)
    message.delete()


MARKDOWN_HELP = """
Markdown es una herramienta de formato muy potente compatible con Telegram. {} tiene algunas mejoras, para asegurarse de que \
los mensajes guardados se analicen correctamente y permitirte crear botones.

- <code>_italic _</code>: al envolver el texto con '_' se generará texto en cursiva.
- <code>*bold*</code>: al envolver el texto con '*' se generará texto en negrita.
- <code>`código`</ code>: al envolver el texto con ''' se generará texto monoespaciado, también conocido como'código' \
- <code>[texto](URL)</code>: esto creará un enlace; el mensaje solo mostrará <code>texto</code>, \
y al tocarlo se abrirá la página en <code>URL</code>.
Ejemplo: <code>[test](example.com)</code>

- <code>[buttontext](buttonurl:someURL)</code>: esta es una mejora especial para permitir que los usuarios tengan \
botones en su markdown. <code>buttontext</code> será lo que se muestra en el botón, y <code>someurl</code> \
será la URL que se abre.
Ejemplo: <code>[Este es un botón](buttonurl:example.com)</code>

Si desea tener varios botones en la misma línea, use: mismo, como tal:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
Esto creará dos botones en una sola línea, en lugar de un botón por línea.

¡Tenga en cuenta que su mensaje <b>DEBE</b> contener algún texto que no sea solo un botón!
""".format(dispatcher.bot.first_name)


@run_async
def markdown_help(bot: Bot, update: Update):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text("Intenta reenviar el siguiente mensaje a mí, ¡y lo verás!")
    update.effective_message.reply_text("/save test This is a markdown test. _italics_, *bold*, `code`, "
                                        "[URL](example.com) [button](buttonurl:github.com) "
                                        "[button2](buttonurl://google.com:same)")


@run_async
def stats(bot: Bot, update: Update):
    update.effective_message.reply_text("Estado actual:\n" + "\n".join([mod.__stats__() for mod in STATS]))


# /ip is for private use
__help__ = """
  - /id: obtener la ID del grupo actual. Si se usa respondiendo a un mensaje, obtiene la ID de ese usuario.
  - /runs: responde una cadena aleatoria de respuestas.
  - /slap: abofetear a un usuario, o recibir una bofetada si no es una respuesta.
  - /time <lugar>: da la hora local en el lugar dado.
  - /info: obtener información sobre un usuario.

  - /markdownhelp: resumen rápido de cómo funciona el markdown en telegram: solo se puede usar en chats privados.
"""

__mod_name__ = "Miscelanea"

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=Filters.chat(OWNER_ID))

TIME_HANDLER = CommandHandler("time", get_time, pass_args=True)

RUNS_HANDLER = DisableAbleCommandHandler("runs", runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, pass_args=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)

ECHO_HANDLER = CommandHandler("echo", echo, filters=Filters.user(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)

STATS_HANDLER = CommandHandler("stats", stats, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(IP_HANDLER)
dispatcher.add_handler(TIME_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)     
