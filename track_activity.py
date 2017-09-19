import datetime

from db_call import execute

def track(type, id_bot, id_user, activity_content, date):
    execute("""INSERT INTO activity(
            id_bot, id_user, content, date, type)
            VALUES(%s, %s, %s, %s, %s)""",
            (id_bot, 
            id_user, 
            activity_content, 
            date,
            type)
    )

def command(bot, update):
    bot_id, sep, actual_token = bot.token.partition(':')
    track("command", 
          bot_id, 
          update.message.from_user.id, 
          update.message.text,
          update.message.date
    )

def text(bot, update):
    bot_id, sep, actual_token = bot.token.partition(':')
    track("text",
          bot_id,
          update.message.from_user.id,
          update.message.text,
          update.message.date
    )