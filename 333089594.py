#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import json
import re
import sys
import os

from telegram.ext import (
    Updater,
    MessageHandler,
    RegexHandler,
    Filters,
    CallbackQueryHandler
)

from utils import new_command

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

def get_user(user):
    default_null = "!"
    user = {
        'id': user.id,
        'username': getattr(user, 'username', None),
        'first_name': getattr(user, 'first_name', None),
        'last_name': getattr(user, 'last_name', None),
        'language_code': getattr(user, 'language_code', None),
    }
    return user

def get_bot(bot):
    bot = get_user(bot)
    bot['date'] = now()
    return bot

def get_info(bot, update):
    user = get_user(update.message.from_user)
    user['date'] = update.message.date
    bot_id, sep, actual_token = bot.token.partition(':')
    add_user(user, int(bot_id))
    if re.search("^[.!/]", update.message.text):
        track_activity.command(bot, update)
    elif Filters.all(update.message):
        track_activity.text(bot, update)

def button(bot, update):
    query = update.callback_query
    bot.edit_message_text(text="Selected option: %s" % query.data,
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id)

def echo(bot, update):
    update.message.reply_text(update.message.text)

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))
    
def start_bot(token):
    updater = Updater(token)
    
    username = updater.bot.username
    #add_bot(get_bot(updater.bot))
    # Create the EventHandler and pass it your bot's token.

    # Get the dispatcher to register handlers
    disp = updater.dispatcher
    
    # Handler to get username and other info
    # disp.add_handler(MessageHandler(Filters.all, get_info), -1)

    disp.add_handler(RegexHandler("^[.!/]", new_command))
    
    # on different commands - answer in Telegram
    disp.add_handler(CallbackQueryHandler(button, pattern="\d"))
    disp.add_handler(CallbackQueryHandler(new_command, pattern="^[/.!]dice"))

    # on noncommand i.e message - echo the message on Telegram
    disp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    disp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def main():
    # Create the EventHandler and pass it your bot's token.
    TOKEN = "333089594:AAFossfi9mGnY648Eb5mv3wKO0NbHedrXq0"
    PORT = int(os.environ.get('PORT', '5000'))
    
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    disp = updater.dispatcher

    # Handler to get username and other info
    # disp.add_handler(MessageHandler(Filters.all, get_info), -1)

    disp.add_handler(RegexHandler("^[.!/]", new_command))
    
    # on different commands - answer in Telegram
    disp.add_handler(CallbackQueryHandler(button, pattern="\d"))
    disp.add_handler(CallbackQueryHandler(new_command, pattern="^[/.!]dice"))

    # on noncommand i.e message - echo the message on Telegram
    disp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    disp.add_error_handler(error)

    # Start the Bot
    #updater.start_polling()
    updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN)
    updater.bot.set_webhook("https://fancazzistibot.herokuapp.com/" + TOKEN)
    
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
