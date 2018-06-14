import re
from io import BytesIO
from typing import Optional, List

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, RegexHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.notes_sql as sql
from tg_bot import dispatcher, MESSAGE_DUMP, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.misc import build_keyboard
from tg_bot.modules.helper_funcs.msg_types import get_note_type

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


# Do not async
def get(bot, update, notename, show_none=True):
    chat_id = update.effective_chat.id
    note = sql.get_note(chat_id, notename)
    message = update.effective_message  # type: Optional[Message]

    if note:
        # If not is replying to a message, reply to that message (unless its an error)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id

        if note.is_reply:
            if MESSAGE_DUMP:
                try:
                    bot.forward_message(chat_id=chat_id, from_chat_id=MESSAGE_DUMP, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Message to forward not found":
                        message.reply_text("Este mensaje parece haberse perdido. Lo eliminaré "
                                           "de tu lista de notas.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
            else:
                try:
                    bot.forward_message(chat_id=chat_id, from_chat_id=chat_id, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Message to forward not found":
                        message.reply_text("Parece que el remitente original de esta nota ha eliminado su "
                                           "mensaje. ¡Lo siento! Eliminaré esta nota de tus notas guardadas.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
        else:
            keyb = []
            if note.msgtype == sql.Types.BUTTON_TEXT:
                buttons = sql.get_buttons(chat_id, notename)
                keyb = build_keyboard(buttons)
            keyboard = InlineKeyboardMarkup(keyb)

            try:
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    bot.send_message(chat_id, note.value, reply_to_message_id=reply_id,
                                     parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
                                     reply_markup=keyboard)
                else:
                    ENUM_FUNC_MAP[note.msgtype](chat_id, note.file, caption=note.value, reply_to_message_id=reply_id,
                                                parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
                                                reply_markup=keyboard)

            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    message.reply_text("Parece que estás tratando de mencionar a alguien que no había visto nunca antes. "
                                       "¡Si realmente querés mencionarlo, enviá uno de sus mensajes y voy a poder hacerlo!")
                elif FILE_MATCHER.match(note.value):
                    message.reply_text("Esta nota es un archivo incorrectamente importado de otro bot; no puedo usarlo. "
                                       "Si realmente la necesitás, tenés que guardarlo nuevamente. Mientras tanto, lo eliminaré "
                                       "de tu lista de notas.")
                    sql.rm_note(chat_id, notename)
                else:
                    message.reply_text("Esta nota no pudo enviarse; está mal creada.")
                    LOGGER.exception("No se pudo analizar el mensaje #%s en el chat %s", notename, str(chat_id))
                    LOGGER.warning("El mensaje fué: %s", str(note.value))
        return
    elif show_none:
        message.reply_text("Esta nota no existe.")


@run_async
def cmd_get(bot: Bot, update: Update, args: List[str]):
    if len(args) >= 1:
        notename = args[0]
        get(bot, update, notename, show_none=True)
    else:
        update.effective_message.reply_text("Get rekt")


@run_async
def hash_get(bot: Bot, update: Update):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:]
    get(bot, update, no_hash, show_none=False)


# TODO: FIX THIS
@run_async
@user_admin
def save_replied(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message

    notename, text, data_type, content, buttons = get_note_type(msg, replied=True)

    if data_type is None:
        msg.reply_text("Amigo, no hay nota.")
        return

    sql.add_note_to_db(chat_id, notename, text, data_type, buttons, content)
    msg.reply_text("¡Si! Añadí el mensaje respondido: {}".format(notename))

    if msg.reply_to_message.from_user.is_bot:
        if text:
            msg.reply_text("Parece que estás tratando de guardar un mensaje de un bot. Lamentablemente, "
                           "los bots no pueden reenviar mensajes de otro bot, por lo que no puedo guardar "
                           "el mensaje exacto.\nGuardaré todo el texto que pueda, pero si querés guardar más, tenés que "
                            "reenvíar el mensaje, y luego guardarlo.")
        else:			
            msg.reply_text("Los bots son perjudicados por Telegram, lo que dificulta que los bots interactúen "
                           "con otros bots. No puedo guardar este mensaje como solía hacerlo. "
                           "¿Podés reenviarlo y después guardar ese nuevo mensaje? ¡Gracias!")
        return


@run_async
@user_admin
def save(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    raw_text = msg.text
    args = raw_text.split(None, 2)  # use python's maxsplit to separate Cmd, note_name, and data

    note_name, text, data_type, content, buttons = get_note_type(msg)

    if data_type is None:
        msg.reply_text("No hay ninguna nota.")
        return

    sql.add_note_to_db(chat_id, note_name, text, data_type, buttons=buttons, file=content)

    msg.reply_text(
        "Agregué la nota {note_name}.\nObtenela con /get {note_name}, o #{note_name}".format(note_name=note_name))


@run_async
@user_admin
def clear(bot: Bot, update: Update, args: List[str]):
    chat_id = update.effective_chat.id
    if len(args) >= 1:
        notename = args[0]

        if sql.rm_note(chat_id, notename):
            update.effective_message.reply_text("Nota eliminada correctamente.")
        else:
            update.effective_message.reply_text("¡Esa nota no en mi base de datos!")


@run_async
def list_notes(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    note_list = sql.get_all_chat_notes(chat_id)

    msg = "*Notas en el chat:*\n"
    for note in note_list:
        note_name = escape_markdown(" - {}\n".format(note.name))
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if msg == "*Notas en el chat:*\n":
        update.effective_message.reply_text("No hay notas en el chat.")

    elif len(msg) != 0:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get('extra', {}).items():
        match = FILE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            notedata = notedata[match.end():].strip()
            if notedata:
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(chat_id, document=output, filename="failed_imports.txt",
                                         caption="Estos archivos/fotos fallaron en la importación porque provienen "
                                                 "de otro bot. Esta es una restricción de la API de Telegram, y no se puede "
                                                 "saltear. ¡Disculpas por el inconveniente!")


def __stats__():
    return "{} notas, entre {} chats.".format(sql.num_notes(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return "Hay `{}` notas en este chat.".format(len(notes))


__help__ = """
 - /get <nombredenota>: obtener la nota con este nombre.
 - #<nombredenota>: igual que /get.
 - /notes o /saved: enumera todas las notas guardadas en este chat.

*Solo para administradores:*
 - /save <nombredenota> <nota>: guarda una nota con ese nombre.
Se puede agregar un botón a una nota mediante el uso de la sintaxis estándar del enlace de markdown: el enlace debe ser precedido por un \
buttonurl:, como tal: `[somelink](buttonurl:example.com)`. Mira /markdownhelp para obtener más información.
 - /save <nombredenota>: guarda el mensaje respondido como una nota con el nombre nombredenota.
 - /clear <nombredenota>: borrar nota con aquel nombre.
"""

__mod_name__ = "Notas"

GET_HANDLER = CommandHandler("get", cmd_get, pass_args=True)
HASH_GET_HANDLER = RegexHandler(r"^#[^\s]+", hash_get)

SAVE_HANDLER = CommandHandler("save", save, filters=~Filters.reply)
REPL_SAVE_HANDLER = CommandHandler("save", save_replied, filters=Filters.reply)
DELETE_HANDLER = CommandHandler("clear", clear, pass_args=True)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(REPL_SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
