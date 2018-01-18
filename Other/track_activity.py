import datetime

import itertools
from collections import Counter

import math
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import BaseFilter, MessageHandler, CommandHandler, CallbackQueryHandler
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
        self.activity_main = InlineKeyboardMarkup([
            [InlineKeyboardButton("Utente più attivo", callback_data="/activity_main utente"),
             InlineKeyboardButton("Emoji piu usato", callback_data="/activity_main emoji"),
             InlineKeyboardButton("Msg Salvati", callback_data="/activity_main messaggi")],
            [InlineKeyboardButton("Attività oraria", callback_data="/activity_main attivita"),
             InlineKeyboardButton("Altro", callback_data="/activity_main altro"),
             InlineKeyboardButton("Esci", callback_data="/activity_main esci")]

        ])


        disp = updater.dispatcher

        disp.add_handler(MessageHandler(filter,self.log_activity))
        disp.add_handler(CommandHandler("activity",self.activity_init))
        disp.add_handler(CallbackQueryHandler(self.activity_choice, pattern="/activity_main"))

        #disp.add_handler(CommandHandler("mostactiveuser",self.get_most_active_user))


    def activity_init(self,bot, update):
        """Funzione per iniziare la visualizzazione delle activity"""
        if not self.db.is_loot_admin(update.message. from_user.id):
            update.message.reply_text("Non hai i privilegi necessari per visualizzare queste info...schiappa")
            return

        to_send="Scegli cosa vuoi visualizzare"
        update.message.reply_text(to_send,reply_markup=self.activity_main)

    def get_day_activity(self):
        """Questa funzione ritorna gli orari di attività maggiore"""

        number_to_day={1:"Lunedì",2:"Martedì",3:"Mercoledì",4:"Giovedì",5:"Venerdì",6:"Sabato",7:"Domenica"}
        to_send="Attività giornaliera:\n"
        #prendi tutte le activity
        activity=self.get_activity_by("all")
        #seleziona solo le date
        activity=[elem['date'] for elem in activity]
        #aggiungi un ora
        activity=[elem + datetime.timedelta(hours=1) for elem in activity]
        #trasforma in giorni
        activity=[elem.isoweekday() for elem in activity]
        #conta le ripetizioni
        counter=Counter(activity)

        tot=sum(counter.values())

        for elem in  counter.keys():
            to_send+="<b>"+number_to_day[elem]+"</b> "+self.filler(tot,counter[elem])+"\n"

        return to_send


    def filler(self, tot, val):
        """Ritorna un stringa che indica il valore in percentuale"""
        perc=math.ceil(val/tot*10)

        res=""
        for i in range(0,perc):
            res+="■"

        for i in range(0,10-perc):
            res+="□"

        return res



    def activity_choice(self, bot, update):


        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        to_send="ciao"

        if param=="attivita":
            to_send=self.get_day_activity()

        elif param == "utente":
            print("utente")
        elif param == "emoji":
            print("emoji")
        elif param == "messaggi":
            to_send="Fino ad ora ci sono stati un totale di <b>"+str(len(self.get_activity_by("all")))+"</b> messaggi registrati"

        elif param == "esci":
            update.callback_query.message.reply_text("Ok")
            bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=update.callback_query.message.message_id
            )
            return

        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_send,
            message_id=update.callback_query.message.message_id,
            parse_mode="HTML",
            reply_markup=self.activity_main
        )

    def log_activity(self, bot, update):
        """Funzione per loggare le activity dentro il db"""

        message=update.message

        msg_type, msg_content= self.get_type_content(message)
        msg_user_id=message.from_user.id

        self.db.add_activity(msg_user_id,str(msg_content),msg_type)

    def get_activity_by(self, what,min=False):
        """Prendi le actiity dal db secondo what
        @:param what: puo essere un int per id_user, una str per typo o un datetime per le date
        @:param min: se è presente un datetime allora min indica che vuoi le date minori """


        if isinstance(what,str) and what in self.types:
            return self.db.get_activity(type=what)
        elif isinstance(what,str) and "all" in what:
            return self.db.get_activity()
        elif isinstance(what,int):
            return self.db.get_activity(user=what)
        elif isinstance(what,datetime) and min:
            return self.db.get_activity(date_min=what)
        elif isinstance(what, datetime) and not min:
            return self.db.get_activity(date_max=what)
        else:
            return False

    def get_most_active_user(self):
        """Ritorna lo user piu attivo nel gruppo"""
        activity=self.get_activity_by("all")
        if not activity: return


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
