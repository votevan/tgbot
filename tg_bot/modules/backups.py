import json
from io import BytesIO
from typing import Optional

from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async

from tg_bot import dispatcher, LOGGER
from tg_bot.__main__ import DATA_IMPORT
from tg_bot.modules.helper_funcs.chat_status import user_admin


@run_async
@user_admin
def import_data(bot: Bot, update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    # TODO: allow uploading doc with command, not just as reply
    # only work with a doc
    if msg.reply_to_message and msg.reply_to_message.document:
        try:
            file_info = bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text("Intenta descargar y resubir el archivo como tu mismo antes de importar. Este documento parece "
                           "dudoso.") 
                           #Original: "Try downloading and reuploading the file as yourself before importing - this one seems
                           #to be iffy!

            return

        with BytesIO() as file:
            file_info.download(out=file)
            file.seek(0)
            data = json.load(file)

        # only import one group
        if len(data) > 1 and str(chat.id) not in data:
            msg.reply_text("Hay más de un grupo en este archivo y ninguno de ellos tiene la misma ID que éste grupo. "
                           "¿Cómo elijo qué importar?") 
                           #Original:
                           #Theres more than one group here in this file, and none have the same chat id as this group 
                           #- how do I choose what to import?

            return

        # Select data source
        if str(chat.id) in data:
            data = data[str(chat.id)]['hashes']
        else:
            data = data[list(data.keys())[0]]['hashes']

        try:
            for mod in DATA_IMPORT:
                mod.__import_data__(str(chat.id), data)
        except Exception:
            msg.reply_text("Ocurrió una excepción mientras se restauraban tus datos. El proceso pudo no haberse completado.")
                           #Original: 
                           #An exception occured while restoring your data. The process may not be complete. If 
                           #you're having issues with this, message @MarieSupport with your backup file so the
                           #issue can be debugged. My owners would be happy to help, and every bug
                           #reported makes me better! Thanks! :)"

            LOGGER.exception("La mportación del chat %s con nombre %s falló.", str(chat.id), str(chat.title))
                             #Original: Import for chatid %s with name %s failed."

            return

        # TODO: some of that link logic
        # NOTE: consider default permissions stuff?
        msg.reply_text("Backup importado. ¡Hola de nuevo! :D") #Original: Backup fully imported. Welcome back! :D


@run_async
@user_admin
def export_data(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    msg.reply_text("")


__mod_name__ = "Backups"

__help__ = """
*Solo para administradores:*
 - /import: responde a un backup de un admin del grupo para poder importar lo más que se pueda haciendo el proceso muy sencillo. Ten en cuenta \
que archivos/fotos no pueden ser importados debido a restricciones de Telegram.
 - /export: Esto no es un comando aún, ¡pero lo sera pronto!
"""

#Original: 
#*Admin only:*
# - /import: reply to a group butler backup file to import as much as possible, making the transfer super simple! Note \
#that files/photos can't be imported due to telegram restrictions.
# - /export: !!! This isn't a command yet, but should be coming soon!

IMPORT_HANDLER = CommandHandler("import", import_data)
EXPORT_HANDLER = CommandHandler("export", export_data)

dispatcher.add_handler(IMPORT_HANDLER)
# dispatcher.add_handler(EXPORT_HANDLER)
