import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler, run_async
from telegram.utils.helpers import mention_markdown, mention_html, escape_markdown

import tg_bot.modules.sql.welcome_sql as sql
from tg_bot import dispatcher, OWNER_ID, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_welcome_type
from tg_bot.modules.helper_funcs.string_handling import markdown_parser, \
    escape_invalid_curly_brackets
from tg_bot.modules.log_channel import loggable

VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']

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


# do not async
def send(update, message, keyboard, backup_message):
    try:
        msg = update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except IndexError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\nNota: el mensaje actual es "
                                                                  "inválido debido a problemas de markdown. Puede ser"
                                                                  "debido al nombre del usuario."),
                                                                  #Original:
                                                                  #Note: the current message was
                                                                  #invalid due to markdown issues. Could be
                                                                  #due to the user's name.
                                                  parse_mode=ParseMode.MARKDOWN)
    except KeyError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\nNota: el mensaje actual es "
                                                                  "inválido debido a un problema con algunos corchetes. "
                                                                  "Por favor, corrígelo."),
                                                                  #Original:
                                                                  #Note: the current message is 
                                                                  #invalid due to an issue with some misplaced 
                                                                  #curly brackets. Please update.
                                                  parse_mode=ParseMode.MARKDOWN)
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNota: el mensaje actual tiene una url no válida "
                                                                       "en uno de sus botones. Corrígelo."), 
                                                                      #Note: the current message has an invalid url
                                                                      #in one of its buttons. Please update.
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Unsupported url protocol":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNota: el mensaje actual tiene botones que "
                                                                      "usa protocolos de URL que no son soportados por"
                                                                      "Telegram. Por favor, corrígelo."),
                                                                      #Note: the current message has buttons which "
                                                                      #use url protocols that are unsupported by "
                                                                      #telegram. Please update.
                                                                      
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Wrong url host":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNota: el mensaje actual tiene algunas URL incorrectas. "
                                                                      "Por favor, corrígelo."),
                                                                      #Note: the current message has some bad urls. 
                                                                      #Please update.
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Could not parse! got invalid url host errors")
        else:
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNota: Se produjo un error al enviar el mensaje "
                                                                      "personalizado. Por favor, corrígelo."),
                                                                      #Note: An error occured when sending the
                                                                      #custom message. Please update.
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.exception()

    return msg


@run_async
def new_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    should_welc, cust_welcome, welc_type = sql.get_welc_pref(chat.id)
    if should_welc:
        sent = None
        new_members = update.effective_message.new_chat_members
        for new_mem in new_members:
            # Give the owner a special welcome
            if new_mem.id == OWNER_ID, 134294875:
                update.effective_message.reply_text("El maestro llegó, ¡QUE COMIENCE LA FIESTAAAA!") 
                                                    #Original: Master is in the houseeee, let's get this party started!
                continue

            # Don't welcome yourself
            elif new_mem.id == bot.id:
                continue

            else:
                # If welcome message is media, send with appropriate function
                if welc_type != sql.Types.TEXT and welc_type != sql.Types.BUTTON_TEXT:
                    ENUM_FUNC_MAP[welc_type](chat.id, cust_welcome)
                    return
                # else, move on
                first_name = new_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.

                if cust_welcome:
                    if new_mem.last_name:
                        fullname = "{} {}".format(first_name, new_mem.last_name)
                    else:
                        fullname = first_name
                    count = chat.get_members_count()
                    mention = mention_markdown(new_mem.id, first_name)
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(cust_welcome, VALID_WELCOME_FORMATTERS)
                    res = valid_format.format(first=escape_markdown(first_name),
                                              last=escape_markdown(new_mem.last_name or first_name),
                                              fullname=escape_markdown(fullname), username=username, mention=mention,
                                              count=count, chatname=escape_markdown(chat.title), id=new_mem.id)
                    buttons = sql.get_welc_buttons(chat.id)
                    keyb = build_keyboard(buttons)
                else:
                    res = sql.DEFAULT_WELCOME.format(first=first_name)
                    keyb = []

                keyboard = InlineKeyboardMarkup(keyb)

                sent = send(update, res, keyboard,
                            sql.DEFAULT_WELCOME.format(first=first_name))  # type: Optional[Message]

        prev_welc = sql.get_clean_pref(chat.id)
        if prev_welc:
            try:
                bot.delete_message(chat.id, prev_welc)
            except BadRequest as excp:
                pass

            if sent:
                sql.set_clean_welcome(chat.id, sent.message_id)


@run_async
def left_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)
    if should_goodbye:
        left_mem = update.effective_message.left_chat_member
        if left_mem:
            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text("RIP Master")
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type != sql.Types.TEXT and goodbye_type != sql.Types.BUTTON_TEXT:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = left_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if left_mem.last_name:
                    fullname = "{} {}".format(first_name, left_mem.last_name)
                else:
                    fullname = first_name
                count = chat.get_members_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(cust_goodbye, VALID_WELCOME_FORMATTERS)
                res = valid_format.format(first=escape_markdown(first_name),
                                          last=escape_markdown(left_mem.last_name or first_name),
                                          fullname=escape_markdown(fullname), username=username, mention=mention,
                                          count=count, chatname=escape_markdown(chat.title), id=left_mem.id)
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = sql.DEFAULT_GOODBYE
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(update, res, keyboard, sql.DEFAULT_GOODBYE)


@run_async
@user_admin
def welcome(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    # if no args, show current replies.
    if len(args) == 0 or args[0] == "noformat":
        noformat = args and args[0] == "noformat"
        pref, welcome_m, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            "Este chat tiene su configuración de bienvenida configurada en: `{}`. \n*El mensaje de bienvenida "
            "(no completando el {{}}) es:*".format(pref),
            #This chat has it's welcome setting set to: `{}`.\n*The welcome message 
            #(not filling the {{}}) is:*"

            parse_mode=ParseMode.MARKDOWN)

        if welcome_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)

        else:
            if noformat:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m)

            else:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text("¡Seré educado!") #Original: ¡Seré educado!

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text("Estoy enojado, ya no saludo a nadie más.")
                                                #Original: I'm sulking, not saying hello anymore.

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("¡Solo entiendo 'on/yes' o 'off/no'!")
                                                #Original: I understand 'on/yes' or 'off/no' only!


@run_async
@user_admin
def goodbye(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]

    if len(args) == 0 or args[0] == "noformat":
        noformat = args and args[0] == "noformat"
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            "Este chat tiene su configuración de despedida configurada en: `{}`. \n*El mensaje de despedida "
            "(no completando el {{}}) es:*".format(pref),
            #Original:
            #This chat has it's goodbye setting set to: `{}`.\n*The goodbye  message "
            #"(not filling the {{}}) is:*
            parse_mode=ParseMode.MARKDOWN)

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        else:
            if noformat:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

            else:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("Lo lamentaré cuando la gente se vaya!") #Original: I'll be sorry when people leave!

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("Se van, están muertos por mí.") #Original: They leave, they're dead to me.

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("¡Solo entiendo 'on/yes' o 'off/no'!") #Original: I understand 'on/yes' or 'off/no' only!


@run_async
@user_admin
@loggable
def set_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("¡No especificaste con qué responder!") #Original: You didn't specify what to reply with!
        return ""

    sql.set_custom_welcome(chat.id, content or text, data_type, buttons)
    msg.reply_text("¡Se estableció un mensaje de bienvenida personalizado con exito!") #Original: Successfully set custom welcome message!

    return "<b>{}:</b>" \
           "\n#SET_WELCOME" \
           "\n<b>Admin:</b> {}" \
           "\nSet the welcome message.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    sql.set_custom_welcome(chat.id, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text("¡Se restableció el mensaje de bienvenida al mensaje predeterminado!") #Original: Successfully reset welcome message to default!
    return "<b>{}:</b>" \
           "\n#RESET_WELCOME" \
           "\n<b>Admin:</b> {}" \
           "\nReset the welcome message to default.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def set_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("¡No especificaste con qué responder!") #Original: You didn't specify what to reply with!
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text("¡Se estableció un mensaje de despedida personalizado con exito!") #Original: Successfully set custom goodbye message!
    return "<b>{}:</b>" \
           "\n#SET_GOODBYE" \
           "\n<b>Admin:</b> {}" \
           "\nSet the goodbye message.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text("Se restableció el mensaje de despedida al mensaje predeterminado!") #Original: Successfully reset goodbye message to default!
    return "<b>{}:</b>" \
           "\n#RESET_GOODBYE" \
           "\n<b>Admin:</b> {}" \
           "\nReset the goodbye message.".format(html.escape(chat.title),
                                                 mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def clean_welcome(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text("Borraré los mensajes de bienvenida de hasta dos días de antigüedad.") #Original: I should be deleting welcome messages up to two days old.
        else:
            update.effective_message.reply_text("¡Actualmente no borro los mensajes antiguos de bienvenida!") #Original: I'm currently not deleting old welcome messages!
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text("Intentaré eliminar los mensajes antiguos de bienvenida.") #Original: I'll try to delete old welcome messages!
        return "<b>{}:</b>" \
               "\n#CLEAN_WELCOME" \
               "\n<b>Admin:</b> {}" \
               "\nHas toggled clean welcomes to <code>ON</code>.".format(html.escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text("No eliminaré los mensajes antiguos de bienvenida.")
        return "<b>{}:</b>" \
               "\n#CLEAN_WELCOME" \
               "\n<b>Admin:</b> {}" \
               "\nHas toggled clean welcomes to <code>OFF</code>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        # idek what you're writing, say yes or no
        update.effective_message.reply_text("¡Solo entiendo 'on/yes' o 'off/no'!") #Original: I understand 'on/yes' or 'off/no' only!
        return ""


WELC_HELP_TXT = "Los mensajes de bienvenida/despedida de su grupo se pueden personalizar de múltiples maneras. Si desea los mensajes " \
                "sean generados individualmente al igual que el mensaje de bienvenida predeterminado, puede usar estas variables:\n" \
                "-`{{first}}`: representa el *primer nombre* del usuario\n" \
                "-`{{last}}`: representa el *apellido* del usuario. Por defecto es el *primer nombre* si el usuario no tiene" \
                "apellido.\n" \
                "-`{{fullname}}`:representa el nombre *completo* del usuario. Por defecto es *el primer nombre* si el usuario no tiene " \
                "apellido.\n" \
                "-`{{username}}`: esto representa el *nombre de usuario* del usuario. Por defecto es *mención* del usuario, " \
                "primer nombre si no tiene nombre de usuario.\n" \
                "-`{{mention}}`: esto simplemente *menciona* un usuario, etiquetándolo con su nombre.\n" \
                "-`{{id}}`: esto representa el *ID*\n" \
                "-`{{count}}`: esto representa el *número de miembro del usuario*.\n" \
                "-`{{chatname}}`: esto representa el *nombre de chat actual*.\n" \
                "\nTodas las variables DEBEN estar rodeadas por `{{}}` para ser reemplazadas.\n" \
                "Los mensajes de bienvenida también admiten markdown, por lo que puede hacer que los elementos sean negrita/cursiva/código/enlaces." \
                "Los botones también son compatibles, por lo que puedes hacer que tus bienvenidas se vean increíbles con una buena bienvenida con" \
                "botones.\n" \
                "Para crear un botón que vincule a sus reglas, use esto: `[Rules](buttonurl://t.me/{}?Start=group_id)`." \
                "Simplemente reemplace `group_id` con la ID de su grupo, que se puede obtener a través de /id, y está listo para "\
                "funcionar. Tenga en cuenta que los ID de grupos suelen estar precedidos por un signo `-`; esto es obligatorio, así que no lo "\
                "elimine.\n" \
                "Si te sientes divertido, incluso puedes establecer imágenes/gifs/videos/mensajes de voz como mensaje de bienvenida, con solo" \
                "respondiendo a los medios deseados, y con el comando /setwelcome.".format(dispatcher.bot.username)

                #Original:
                #Your group's welcome/goodbye messages can be personalised in multiple ways. If you want the messages" \
                # to be individually generated, like the default welcome message is, you can use *these* variables:\n" \
                # - `{{first}}`: this represents the user's *first* name\n" \
                # - `{{last}}`: this represents the user's *last* name. Defaults to *first name* if user has no " \
                #last name.\n" \
                # - `{{fullname}}`: this represents the user's *full* name. Defaults to *first name* if user has no " \
                #last name.\n" \
                # - `{{username}}`: this represents the user's *username*. Defaults to a *mention* of the user's " \
                #first name if has no username.\n" \
                # - `{{mention}}`: this simply *mentions* a user - tagging them with their first name.\n" \
                # - `{{id}}`: this represents the user's *id*\n" \
                # - `{{count}}`: this represents the user's *member number*.\n" \
                # - `{{chatname}}`: this represents the *current chat name*.\n" \
                #\nEach variable MUST be surrounded by `{{}}` to be replaced.\n" \
                #Welcome messages also support markdown, so you can make any elements bold/italic/code/links. " \
                #Buttons are also supported, so you can make your welcomes look awesome with some nice intro " \
                #buttons.\n" \
                #To create a button linking to your rules, use this: `[Rules](buttonurl://t.me/{}?start=group_id)`. " \
                #Simply replace `group_id` with your group's id, which can be obtained via /id, and you're good to " \
                #go. Note that group ids are usually preceded by a `-` sign; this is required, so please don't " \
                #remove it.\n" \
                #If you're feeling fun, you can even set images/gifs/videos/voice messages as the welcome message by " \
                #replying to the desired media, and calling /setwelcome."

@run_async
@user_admin
def welcome_help(bot: Bot, update: Update):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    return "This chat has it's welcome preference set to `{}`.\n" \
           "It's goodbye preference is `{}`.".format(welcome_pref, goodbye_pref)
	

__help__ = """
{}

*Solo para administradores:*
 - /welcome <on/off>: activar/desactivar los mensajes de bienvenida.
 - /welcome: muestra la configuración de bienvenida actual.
 - /welcome noformat: muestra la configuración de bienvenida actual, sin el formato, ¡útil para reciclar sus mensajes de bienvenida!
 - /goodbye -> mismo uso y argumentos que /welcome.
 - /setwelcome <algún texto>: establezca un mensaje de bienvenida personalizado. Si se usa respondiendo a los medios, usa ese medio.
 - /setgoodbye <algún texto>: establezca un mensaje de despedida personalizado. Si se usa respondiendo a los medios, usa ese medio.
 - /resetwelcome: restablecer al mensaje de bienvenida predeterminado.
 - /resetgoodbye: restablecer al mensaje de despedida predeterminado.
 - /cleanwelcome <on/off>: en el miembro nuevo, intente eliminar el mensaje de bienvenida anterior para evitar el correo no deseado.

 - /welcomehelp: vea más información de formato para mensajes personalizados de bienvenida/despedida.
""".format(WELC_HELP_TXT)

#Original:
# *Admin only:*
# - /welcome <on/off>: enable/disable welcome messages.
# - /welcome: shows current welcome settings.
# - /welcome noformat: shows current welcome settings, without the formatting - useful to recycle your welcome messages!
# - /goodbye -> same usage and args as /welcome.
# - /setwelcome <sometext>: set a custom welcome message. If used replying to media, uses that media.
# - /setgoodbye <sometext>: set a custom goodbye message. If used replying to media, uses that media.
# - /resetwelcome: reset to the default welcome message.
# - /resetgoodbye: reset to the default goodbye message.
# - /cleanwelcome <on/off>: On new member, try to delete the previous welcome message to avoid spamming the chat.

# - /welcomehelp: view more formatting information for custom welcome/goodbye messages.

__mod_name__ = "Bienvenidas/Despedidas"

NEW_MEM_HANDLER = MessageHandler(Filters.status_update.new_chat_members, new_member)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member, left_member)
WELC_PREF_HANDLER = CommandHandler("welcome", welcome, pass_args=True, filters=Filters.group)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye", goodbye, pass_args=True, filters=Filters.group)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=Filters.group)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=Filters.group)
RESET_WELCOME = CommandHandler("resetwelcome", reset_welcome, filters=Filters.group)
RESET_GOODBYE = CommandHandler("resetgoodbye", reset_goodbye, filters=Filters.group)
CLEAN_WELCOME = CommandHandler("cleanwelcome", clean_welcome, pass_args=True, filters=Filters.group)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help)

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(WELCOME_HELP)
