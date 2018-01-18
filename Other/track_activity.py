import datetime

from telegram.ext import BaseFilter, MessageHandler
import emoji


# def track(type, id_bot, id_user, activity_content, date):
#     execute("""INSERT INTO activity(
#             id_bot, id_user, content, date, type)
#             VALUES(%s, %s, %s, %s, %s)""",
#             (id_bot,
#             id_user,
#             activity_content,
#             date,
#             type)
#     )
#
# def command(bot, update):
#     bot_id, sep, actual_token = bot.token.partition(':')
#     track("command",
#           bot_id,
#           update.message.from_user.id,
#           update.message.text,
#           update.message.date
#     )
#
# def text(bot, update):
#     bot_id, sep, actual_token = bot.token.partition(':')
#     track("text",
#           bot_id,
#           update.message.from_user.id,
#           update.message.text,
#           update.message.date
#     )
#
class Track:
    """Classe per il track delle activity sul gruppo dei Fancazzisti"""
    def __init__(self,updater, db , filter):
        self.db=db
        self.types=["text","audio","photo","sticker","video","voice"]


        disp = updater.dispatcher

        disp.add_handler(MessageHandler(filter,self.log_activity))


    def log_activity(self, bot, update):
        """Funzione per loggare le activity dentro il db"""

        message=update.message

        msg_type, msg_content= self.get_type_content(message)
        msg_user_id=message.from_user.id

        self.db.add_activity(msg_user_id,str(msg_content),msg_type)

    def get_activity_by(self, what):
        """Prendi le actiity dal db secondo what
        @:param what: puo essere un int per id_user, una str per typo o un datetime per le date"""

        if what not in self.types:
            return False

        return self.db.get_activity(type=type)


    def get_type_content(self, message):
        """Ritorna il tipo del messaggio ricevuto
        @:param message: il messaggio ricevuto
        @type: Telegram.message
        #:return: stringa rappresentante il tipo di messaggio ricevuto + content"""

        if message.text:
            return "text",emoji.demojize(message.text)
        elif message.audio:
            return "audio",message.audio.file_id
        elif message.document:
            return "document", message.document.file_id
        elif message.photo:
            return "photo", message.photo[0].file_id

        elif message.sticker:
            return "sticker",message.sticker.file_id

        elif message.video:
            return "video",message.video.file_id

        elif message.voice:
            return "voice", message.voice.file_id

        else:
            return "unkown",message.message_id




class TrackFilter(BaseFilter):
    """Filtro personalizzato per il track activity sul gruppo dei fancazzisti"""
    def __init__(self):
        #id del gruppo
        self.bot_per_i_boss=-1001284891867
        self.fancazzisti=-1001050402153

    def filter(self, message):
        """Ritorna true se il messaggio proviene dal gruppo e non è un comando"""
        #print(message)
        if message.chat.id ==self.fancazzisti:
            try:
                if message.text.startswith('/'): return False
            finally:
                return True
        return False
