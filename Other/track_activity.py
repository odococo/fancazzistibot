import datetime

import itertools
import operator
import re
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
        self.inline_activity_main = [
            [InlineKeyboardButton("Emoji piu usato", callback_data="/activity_main emoji"),
             InlineKeyboardButton("Msg Salvati", callback_data="/activity_main messaggi")],
            [InlineKeyboardButton("Attività", callback_data="/activity_main attivita"),
             InlineKeyboardButton("Altro", callback_data="/activity_main altro"),
             InlineKeyboardButton("Esci", callback_data="/activity_main esci")]]

        self.inline_activity_time = InlineKeyboardMarkup([
            [InlineKeyboardButton("Oraria", callback_data="/activity_time oraria"),
             InlineKeyboardButton("Giornaliera", callback_data="/activity_time giornaliera"),
             InlineKeyboardButton("Indietro", callback_data="/activity_time indietro")],


        ])

        self.inline_activity_user = InlineKeyboardMarkup([
            [InlineKeyboardButton("Msg Inviati", callback_data="/activity_user msg"),
             InlineKeyboardButton("Top emoji", callback_data="/activity_user emoji"),
             InlineKeyboardButton("Top parole", callback_data="/activity_user parole")],
             [InlineKeyboardButton("Analisi sentimenti", callback_data="/activity_user sentimenti"),
             InlineKeyboardButton("Tipi inviati", callback_data="/activity_user tipi"),
             InlineKeyboardButton("Indietro", callback_data="/activity_user indietro")],


        ])

        self.main_message="""
Benvenuto caro utente in questo nuovo comando pieno di cose belle 🌈
Di seguito troverai vari bottoni per poter visualizzare tutte le informazioni dei messaggi inviati sul gruppo Fancazzisti
<b>Emoji piu usato</b> : semplicemente la lista degli emoji piu utilizzati sul gruppo
<b>Msg Salvati</b> : il numero di messaggi salvati dentro il bot
<b>Attività</b> : mostra varie informazioni temporali relative all'attivita presente nel gruppo
<b>Esci</b> : per uscire dalla visualizzazione
<b>Il tuo username</b> : qui potrai visualizzare le info relative al tuo account personale
Alcune funzioni non sono ancora disponibili, pazienta e arriveranno"""

        self.time_message="""
In questa sezione potrai visualizzare l'attività del gruppo, intesa come quantità di messaggi inviati in un certo intervallo temporale
<b>Oraria</b> : intervallo orario
<b>Giornaliera</b> : intervallo giornaliero
Con il passare del tempo saranno disponibili dei dati sempre piu precisi"""

        self.user_message ="""
In questa sezione potrai visualizzare le informazioni relative ai messaggi inviati da <b>te</b> sul gruppo dei Fancazzisti
<b>Msg Inviati</b> : il numero di messaggi che hai inviato sul gruppo 
<b>Top emoji</b> : le emoji che usi di piu
<b> Analisi sentimenti </b> : una stima dei sentimenti espressi dai tuoi messaggi
<b> Tipi inviati </b> : i diversi tipi di messaggio che hai inviato (ex: photo, video, audio....)"""

        disp = updater.dispatcher

        disp.add_handler(MessageHandler(filter,self.log_activity))
        disp.add_handler(CommandHandler("activity",self.activity_init, pass_user_data=True))
        disp.add_handler(CallbackQueryHandler(self.activity_main, pattern="/activity_main", pass_user_data=True))
        disp.add_handler(CallbackQueryHandler(self.activity_time, pattern="/activity_time", pass_user_data=True))
        disp.add_handler(CallbackQueryHandler(self.activity_user, pattern="/activity_user", pass_user_data=True))

        #disp.add_handler(CommandHandler("mostactiveuser",self.get_most_active_user))

    # ===================LOOPS=================================

    def activity_init(self,bot, update, user_data):
        """Funzione per iniziare la visualizzazione delle activity"""
        if not self.db.is_loot_admin(update.message. from_user.id):
            update.message.reply_text("Non hai i privilegi necessari per visualizzare queste info...schiappa")
            return
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è possibile solo in privata")

            return


        # prendi lo username
        username = update.message.from_user.username
        # cambia l'inline
        new_inline=self.inline_activity_main
        new_inline[0].insert(0,InlineKeyboardButton(username, callback_data="/activity_main utente"))
        inline_new_main=InlineKeyboardMarkup(new_inline)
        user_data['inline_main']=inline_new_main



        update.message.reply_text(self.main_message,reply_markup=inline_new_main, parse_mode="HTML")

    def activity_main(self, bot, update,user_data):
        """Funzione per la visualizzazione della sezione principale di activity"""

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        to_send="ciao"

        if param=="attivita":
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.time_message,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_activity_time
            )
            return

        elif param == "utente":
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.user_message,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_activity_user
            )
            return


        elif param == "emoji":
            #prendi tutti i messaggi dal database
            activity=self.get_activity_by("all")
            activity=[elem['content'] for elem in activity]

            #crea un'unica stringa e passala alla funzione get_top_emoji
            top_emoji=self.get_top_emoji(" ".join(activity))
            print(top_emoji)

            #calcola la len
            max_len=len(top_emoji)

            #se questa è maggiore di 10 impostala a 10
            if max_len>10: max_len=10

            #inizzializza il to_send
            to_send="Le top "+str(max_len)+ " emoji sono:\n"

            #genera il resto del to send
            for idx in range(0,max_len):
                to_send+=top_emoji[idx][0]+" ripetuto <b>"+str(top_emoji[idx][1])+"</b> volte\n"


        elif param == "messaggi":
            to_send="Fino ad ora ci sono stati un totale di <b>"+str(len(self.get_activity_by("all")))+"</b> messaggi registrati"

        elif param == "esci":
            update.callback_query.message.reply_text("Hasta la vista, baby")
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
            reply_markup=user_data['inline_main']
        )

    def activity_time(self, bot, update,user_data):

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        to_send=""

        if param == "giornaliera":

            to_send= self.get_day_activity()

        elif param=="oraria":
            to_send=self.get_hour_activity()

        elif param == "indietro":
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.main_message,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=user_data['inline_main']
            )
            return


        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_send,
            message_id=update.callback_query.message.message_id,
            parse_mode="HTML",
            reply_markup=self.inline_activity_time
        )

    def activity_user(self, bot, update,user_data):

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        activity=self.get_activity_by(update.callback_query.from_user.id)

        if not activity and param!="indietro":
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text="Non sono presenti dati relativi al tuo account...",
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=user_data['inline_main']
            )
            return

        to_send=""

        if param == "msg":

            to_send= "Sono presenti <b>"+str(len(activity))+"</b> messaggi legati al tuo account"

        elif param == "emoji":

            #prendi il testo
            activity=[elem['content'] for elem in activity]

            top_emoji=self.get_top_emoji(" ".join(activity))

            #se non ci sono emoi relative all'account
            if not top_emoji:
                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text="Non sono presenti emoji relative al tuo account...che tristezza",
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML",
                    reply_markup=self.inline_activity_user
                )
                return

            # calcola la len
            max_len = len(top_emoji)

            # se questa è maggiore di 10 impostala a 10
            if max_len > 10: max_len = 10

            # inizzializza il to_send
            to_send = "Le top " + str(max_len) + " emoji sono:\n"

            # genera il resto del to send
            for idx in range(0, max_len):
                to_send += top_emoji[idx][0] + " ripetuto <b>" + str(top_emoji[idx][1]) + "</b> volte\n"


        elif param == "parole":
            to_send= "Comando non ancora implementato...sorry"


        elif param == "sentimenti":
            to_send= "Comando non ancora implementato...sorry"


        elif param == "tipi":
            to_send= "Comando non ancora implementato...sorry"


        elif param == "indietro":
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.main_message,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=user_data['inline_main']
            )
            return


        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_send,
            message_id=update.callback_query.message.message_id,
            parse_mode="HTML",
            reply_markup=self.inline_activity_user
        )


#=====================DB INTERACTION======================================

    def log_activity(self, bot, update):
        """Funzione per loggare le activity dentro il db"""

        message=update.message

        msg_type, msg_content= self.get_type_content(message)
        msg_user_id=message.from_user.id

        self.db.add_activity(msg_user_id,str(msg_content),msg_type)

    def get_activity_by(self, what ,min=False):
        """Prendi le actiity dal db secondo what
        @:param what: puo essere un int per id_user, una str per typo o un datetime per le date
        @:param min: se è presente un datetime allora min indica che vuoi le date minori """

        print(what)

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


#============================UTILS===========================================

    def get_most_active_user(self):
        """Ritorna lo user piu attivo nel gruppo"""
        activity=self.get_activity_by("all")
        if not activity: return

    def get_top_emoji(self, text, emoji_bool=True):
        """Ritorna le top emoji trovate nel testo
        @:param text: il testo in cui cercare le emoji
        @:type: str
        @:param emoji_bool: boolean per trasformare le emoji da testo in emoji
        @:type:bool default true
        @:return: lista con di tuple del tipo (emoji, ripetizioni)"""

        #trovo le emoji nel testo
        emoji_regex = re.compile(r":([a-z_]+):")
        find=re.findall(emoji_regex,text)

        counter=Counter(find)
        # sorto il dizionario
        sorted_x = sorted(counter.items(), key=operator.itemgetter(1), reverse=True)


        if emoji_bool:
            res=[]
            for elem in sorted_x:
                res.append((emoji.emojize(":"+elem[0]+":"),elem[1]))
        else:
            res=sorted_x

        return res


    def get_day_activity(self):
        """Questa funzione ritorna l'attivita giornaliera
        @:return: stringa da inviare all'utente"""

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

    def get_hour_activity(self):
        """Questa funzione ritorna l'attivita oraria
        @:return: stringa da inviare all'utente"""


        to_send = "Attività oraira:\n"
        # prendi tutte le activity
        activity = self.get_activity_by("all")
        # seleziona solo le date
        activity = [elem['date'] for elem in activity]
        # aggiungi un ora
        activity = [elem + datetime.timedelta(hours=1) for elem in activity]
        # trasforma in giorni
        activity = [elem.hour for elem in activity]
        # conta le ripetizioni
        counter = Counter(activity)

        tot = sum(counter.values())

        for elem in counter.keys():
            to_send += "<b>" + str(elem) + ":00</b> " + self.filler(tot, counter[elem]) + "\n"

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

    def word_count(self, text):
        """Conta le ripetizioni di delle parole nel testo
        @:param text: la stringa dove cercare le parole
        @:type: str"""
        counts = dict()
        words = text.split()

        for word in words:
            if word in counts and len(word)>2:
                counts[word] += 1
            else:
                counts[word] = 1

        sorted_x = sorted(counts.items(), key=operator.itemgetter(1), reverse=True)


        return sorted_x




class TrackFilter(BaseFilter):
    """Filtro personalizzato per il track activity sul gruppo dei fancazzisti"""
    def __init__(self):
        #id del gruppo
        self.bot_per_i_boss=-1001284891867
        self.fancazzisti=-1001050402153

    def filter(self, message):
        """Ritorna true se il messaggio proviene dal gruppo e non è un comando"""
        #print(message)
        if message.from_user.is_bot: return False
        if message.chat.id ==self.fancazzisti:
            try:
                if message.text.startswith('/'): return False
            finally:
                return True
        return False
