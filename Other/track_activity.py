import collections
import copy
import datetime
import math
import operator
import random
import re
from collections import Counter
from time import sleep

import numpy
from empythy import EmpathyMachines
import emoji
import telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import BaseFilter, MessageHandler, CommandHandler, CallbackQueryHandler
from statsmodels import robust

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
from Sentiment_analisys.Analyzer import Analyzer


class Track:
    """Classe per il track delle activity sul gruppo dei Fancazzisti"""

    def __init__(self, updater, db, filter):
        self.db = db
        self.types = ["text", "audio", "photo", "sticker", "video", "voice"]
        self.ita_types = {"text": "Testo", "audio": "Audio", "photo": "Immagini", "sticker": "Stickers",
                          "video": "Video", "voice": "Vocali", "document": "File", "unkown": "Altro"}

        self.inline_activity_main = [
            [
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
             InlineKeyboardButton("Sticker preferito", callback_data="/activity_user sticker"),
             InlineKeyboardButton("Indietro", callback_data="/activity_user indietro")],

        ])

        self.inline_activity_altro = InlineKeyboardMarkup([
            [InlineKeyboardButton("Emoji +", callback_data="/activity_altro emoji"),
             InlineKeyboardButton("User +", callback_data="/activity_altro user_piu")],
            [InlineKeyboardButton("User -", callback_data="/activity_altro user_meno"),
             InlineKeyboardButton("Indietro", callback_data="/activity_altro indietro")]])

        self.inline_cat = InlineKeyboardMarkup([
            [InlineKeyboardButton("Negativa", callback_data="/activity_sentiment -1"),
             InlineKeyboardButton("Neutrale", callback_data="/activity_sentiment 0"),
             InlineKeyboardButton("Positiva", callback_data="/activity_sentiment +1")],

        ])

        self.main_message = """
Benvenuto caro utente in questo nuovo comando pieno di cose belle 🌈
Di seguito troverai vari bottoni per poter visualizzare tutte le informazioni dei messaggi inviati sul gruppo Fancazzisti
<b>Msg Salvati</b> : il numero di messaggi salvati dentro il bot
<b>Altro</b> : in questa sezione potrai trovare delle informazioni generali
<b>Attività</b> : mostra varie informazioni temporali relative all'attivita presente nel gruppo
<b>Esci</b> : per uscire dalla visualizzazione
<b>Il tuo username</b> : qui potrai visualizzare le info relative al tuo account personale
Alcune funzioni non sono ancora disponibili, pazienta e arriveranno
<b>NB</b> Alcune informazioni sono sbloccabili a seconda del tuo punteggio! 
Per visualizzare il punteggio usa il comando /punteggioact.
Per visualizzare tutti i punteggi usa /topunteggio.
Per aumentarlo usa /classify e rispondi alle domande entro il tempo limite e guadagnerai un punto...
ma attento se risponderai a cazzo oppure non farai in tempo ti verrà detratto un punto """

        self.time_message = """
In questa sezione potrai visualizzare l'attività del gruppo, intesa come quantità di messaggi inviati in un certo intervallo temporale 🕰
<b>Oraria</b> : intervallo orario
<b>Giornaliera</b> : intervallo giornaliero
Con il passare del tempo saranno disponibili dei dati sempre piu precisi"""

        self.user_message = """
In questa sezione potrai visualizzare le informazioni relative ai messaggi inviati da <b>te</b> sul gruppo dei Fancazzisti 👤
<b>Msg Inviati</b> : il numero di messaggi che hai inviato sul gruppo 
<b>Top emoji</b> : le emoji che usi di piu
<b>Sticker Preferito</b> : Invia lo sticker che hai usato di piu
<b> Analisi sentimenti </b> : una stima dei sentimenti espressi dai tuoi messaggi
<b> Tipi inviati </b> : i diversi tipi di messaggio che hai inviato (ex: photo, video, audio....)"""

        self.altro_message = """
In questa sezione puoi visualizzare informazioni varie 📊 tra cui: 
<b>Emoji piu usati (+)</b> : una classifica degli emoji piu usati sul gruppo
<b>User più attivo (+)</b> : il nome dello user piu attivo nel gruppo 
<b>User meno attivo (-)</b> : il nome dello user meno attivo nel gruppo """

        self.min_punteggio_attivita = 10
        self.min_punteggio_altro = 20
        self.min_punteggio_user = 30

        self.min_punteggio_altro_userM_ = 40
        self.min_punteggio_altro_userP = 50

        self.min_punteggio_user_emoji = 60
        self.min_punteggio_user_parole = 55
        self.min_punteggio_user_tipi_inviati = 45
        self.min_punteggio_user_sticker = 50

        self.secondi = 10
        self.is_job_running = False
        self.answered = 0


        disp = updater.dispatcher

        #disp.add_handler(MessageHandler(filter, self.log_activity))
        disp.add_handler(CommandHandler("activity", self.activity_init, pass_user_data=True))
        disp.add_handler(CommandHandler("getallpred", self.get_all_pred))
        disp.add_handler(CommandHandler("punteggioact", self.visualizza_punteggio))
        disp.add_handler(CommandHandler("topunteggio", self.top_punteggio))
        disp.add_handler(
            CommandHandler("classify", self.get_to_classify, pass_job_queue=True, pass_chat_data=True, pass_args=True))
        disp.add_handler(CommandHandler("classified", self.classified))

        disp.add_handler(CallbackQueryHandler(self.activity_main, pattern="/activity_main", pass_user_data=True))
        disp.add_handler(CallbackQueryHandler(self.activity_time, pattern="/activity_time", pass_user_data=True))
        disp.add_handler(CallbackQueryHandler(self.activity_user, pattern="/activity_user", pass_user_data=True))
        disp.add_handler(CallbackQueryHandler(self.activity_altro, pattern="/activity_altro", pass_user_data=True))
        disp.add_handler(CallbackQueryHandler(self.classify, pattern="/activity_sentiment", pass_chat_data=True, ))

        classified = self.get_activity_by("all")
        classified=[{'review':elem['content'],'sentiment':elem['sentiment']} for elem in classified if isinstance(elem['sentiment'], int)]
        labled=[elem for elem in classified if elem['sentiment']!=0]
        unlabled=[elem for elem in classified if elem['sentiment']==0]
        self.analyzer=Analyzer(labled,unlabled)
        self.analyzer.train_models()
        #self.analyzer.predict([elem for elem in self.get_activity_by(24978334) if elem['type']=="text"])



    # ===================LOOPS=================================

    def activity_init(self, bot, update, user_data):
        """Funzione per iniziare la visualizzazione delle activity"""
        # if not self.db.is_loot_admin(update.message. from_user.id):
        #     update.message.reply_text("Non hai i privilegi necessari per visualizzare queste info...schiappa")
        #     return

        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è possibile solo in privata")

            return

        # salva l'utente nella tabella activity_points
        self.db.insert_activity_points(update.message.from_user.id)

        # print(user_data['inline_main'])

        # prendi lo username
        user_data['username'] = username = update.message.from_user.username
        # cambia l'inline
        new_inline = copy.deepcopy(self.inline_activity_main)

        new_inline[0].insert(0, InlineKeyboardButton(username, callback_data="/activity_main utente"))

        inline_new_main = InlineKeyboardMarkup(new_inline)

        user_data['inline_main'] = inline_new_main

        update.message.reply_text(self.main_message, reply_markup=inline_new_main, parse_mode="HTML")

    def activity_main(self, bot, update, user_data):
        """Funzione per la visualizzazione della sezione principale di activity"""

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        # prendi il punteggio dello user
        user_punteggio = self.db.get_activity_points_by_id(update.callback_query.from_user.id)

        if param == "attivita":

            # controlla che lo user possa visualizzare l'informazione
            if user_punteggio < self.min_punteggio_attivita:
                to_send = "Devi avere un minimo di " + str(
                    self.min_punteggio_attivita) + " punti per visualizzare questa " \
                                                   "informazione\nPer ora sei a " + str(
                    user_punteggio) + " punti, usa /classify per guadagnarne altri"

                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML",
                    reply_markup=user_data['inline_main']
                )
                return

            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.time_message,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_activity_time
            )
            return

        elif param == "utente":

            if user_punteggio < self.min_punteggio_user:
                to_send = "Devi avere un minimo di " + str(
                    self.min_punteggio_user) + " punti per visualizzare questa " \
                                               "informazione\nPer ora sei a " + str(
                    user_punteggio) + " punti, usa /classify per guadagnarne altri"

                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML",
                    reply_markup=user_data['inline_main']
                )
                return

            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.user_message,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_activity_user
            )
            return

        elif param == "altro":

            if user_punteggio < self.min_punteggio_altro:
                to_send = "Devi avere un minimo di " + str(
                    self.min_punteggio_altro) + " punti per visualizzare questa " \
                                                "informazione\nPer ora sei a " + str(
                    user_punteggio) + " punti, usa /classify per guadagnarne altri"

                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML",
                    reply_markup=user_data['inline_main']
                )
                return

            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.altro_message,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_activity_altro
            )
            return


        elif param == "messaggi":
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text="Fino ad ora ci sono stati un totale di <b>" + str(
                    len(self.get_activity_by("all"))) + "</b> messaggi registrati",
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=user_data['inline_main']
            )

        elif param == "esci":
            self.esci(user_data)
            update.callback_query.message.reply_text("Hasta la vista, baby")
            bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=update.callback_query.message.message_id
            )
            return

    def activity_time(self, bot, update, user_data):

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        to_send = ""

        if param == "giornaliera":

            to_send = self.get_day_activity()

        elif param == "oraria":
            to_send = self.get_hour_activity()

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

    def activity_user(self, bot, update, user_data):

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        activity = self.get_activity_by(update.callback_query.from_user.id)

        if not activity and param != "indietro":
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text="Non sono presenti dati relativi al tuo account...",
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=user_data['inline_main']
            )
            return

        to_send = ""

        user_punteggio = self.db.get_activity_points_by_id(update.callback_query.from_user.id)

        if param == "msg":

            to_send = "Sono presenti <b>" + str(len(activity)) + "</b> messaggi legati al tuo account"

        elif param == "emoji":
            if user_punteggio < self.min_punteggio_user_emoji:
                to_send = "Devi avere un minimo di " + str(
                    self.min_punteggio_user_emoji) + " punti per visualizzare questa " \
                                                     "informazione\nPer ora sei a " + str(
                    user_punteggio) + " punti, usa /classify per guadagnarne altri"

                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML",
                    reply_markup=self.inline_activity_user
                )
                return

            # prendi il testo
            activity = [elem['content'] for elem in activity]

            top_emoji = self.get_top_emoji(" ".join(activity))

            # se non ci sono emoi relative all'account
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

            if user_punteggio < self.min_punteggio_user_parole:
                to_send = "Devi avere un minimo di " + str(
                    self.min_punteggio_user_parole) + " punti per visualizzare questa " \
                                                      "informazione\nPer ora sei a " + str(
                    user_punteggio) + " punti, usa /classify per guadagnarne altri"

                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML",
                    reply_markup=self.inline_activity_user
                )
                return

            activity = [elem['content'] for elem in activity]
            count = self.get_word_count(" ".join(activity))
            # calcola la len
            max_len = len(count)

            # se questa è maggiore di 10 impostala a 10
            if max_len > 10: max_len = 10

            # inizzializza il to_send
            to_send = "Le tue top " + str(max_len) + " parole sono:\n"

            # genera il resto del to send
            for idx in range(0, max_len):
                to_send += "<b>" + count[idx][0] + "</b> ripetuta <b>" + str(count[idx][1]) + "</b> volte\n"





        elif param == "sentimenti":
            #prendi la predizione dei sentimenti
            pred=self.analyzer.predict(self.analyzer.svc,[elem for elem in self.get_activity_by(update.callback_query.from_user.id) if elem['type']=="text"])
            pred=numpy.array(pred)
            mean=pred.mean()
            std=pred.std()
            to_send="SVC - Mean: "+"{:,}".format(mean)+"\nstd:  "+"{:,}".format(std)+"\n"




        elif param == "tipi":

            if user_punteggio < self.min_punteggio_user_tipi_inviati:
                to_send = "Devi avere un minimo di " + str(
                    self.min_punteggio_user_tipi_inviati) + " punti per visualizzare questa " \
                                                            "informazione\nPer ora sei a " + str(
                    user_punteggio) + " punti, usa /classify per guadagnarne altri"

                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML",
                    reply_markup=self.inline_activity_user
                )
                return

            types = [elem['type'] for elem in activity]
            counter = Counter(types)
            # sorto il dizionario
            sorted_x = sorted(counter.items(), key=operator.itemgetter(1), reverse=True)
            tot = sum([elem[1] for elem in sorted_x])

            #print(sorted_x)

            sorted_x = [(elem[0], math.ceil(elem[1] / tot * 100)) for elem in sorted_x]
            #print(sorted_x)

            to_send = user_data['username'] + " hai inviato un totale di " + str(tot) + " messaggi... di cui:\n"

            for elem in sorted_x:
                to_send += "Il <b>" + str(elem[1]) + "</b>% è <b>" + self.ita_types[elem[0]] + "</b> \n"


        elif param == "sticker":

            if user_punteggio < self.min_punteggio_user_sticker:
                to_send = "Devi avere un minimo di " + str(
                    self.min_punteggio_user_sticker) + " punti per visualizzare questa " \
                                                       "informazione\nPer ora sei a " + str(
                    user_punteggio) + " punti, usa /classify per guadagnarne altri"

                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML",
                    reply_markup=self.inline_activity_user
                )
                return

            stcker_id = self.get_preferred_sticker(activity)
            #print(stcker_id)
            to_send = "Il tuo sticker preferito è "
            bot.sendSticker(update.callback_query.message.chat_id, stcker_id)


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

    def activity_altro(self, bot, update, user_data):

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        to_send = ""

        user_punteggio = self.db.get_activity_points_by_id(update.callback_query.from_user.id)

        if param == "emoji":
            # prendi tutti i messaggi dal database
            activity = self.get_activity_by("all")
            activity = [elem['content'] for elem in activity]

            # crea un'unica stringa e passala alla funzione get_top_emoji
            top_emoji = self.get_top_emoji(" ".join(activity))
            # print(top_emoji)

            # calcola la len
            max_len = len(top_emoji)

            # se questa è maggiore di 10 impostala a 10
            if max_len > 10: max_len = 10

            # inizzializza il to_send
            to_send = "Le top " + str(max_len) + " emoji sono:\n"

            # genera il resto del to send
            for idx in range(0, max_len):
                to_send += top_emoji[idx][0] + " ripetuto <b>" + str(top_emoji[idx][1]) + "</b> volte\n"


        elif param == "user_piu":

            if user_punteggio < self.min_punteggio_altro_userP:
                to_send = "Devi avere un minimo di " + str(
                    self.min_punteggio_altro_userP) + " punti per visualizzare questa " \
                                                      "informazione\nPer ora sei a " + str(
                    user_punteggio) + " punti, usa /classify per guadagnarne altri"

                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML",
                    reply_markup=self.inline_activity_altro
                )
                return

            user, count = self.get_most_active_user()

            if not user:
                to_send = "Non ci sono utenti nel database"
            else:
                to_send = "L'user piu attivo è @" + user['username'] + ", con <b>" + str(
                    count) + "</b> messaggi, grandioso!"

        elif param == "user_meno":

            if user_punteggio < self.min_punteggio_altro_userM_:
                to_send = "Devi avere un minimo di " + str(
                    self.min_punteggio_altro_userM_) + " punti per visualizzare questa " \
                                                       "informazione\nPer ora sei a " + str(
                    user_punteggio) + " punti, usa /classify per guadagnarne altri"

                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML",
                    reply_markup=self.inline_activity_altro
                )
                return

            user, count = self.get_most_active_user(piu=False)

            if not user:
                to_send = "Non ci sono utenti nel database"
            else:
                to_send = "L'user meno attivo è @" + user['username'] + ", con <b>" + str(
                    count) + "</b> messaggi....che pena"





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
            reply_markup=self.inline_activity_altro
        )

    # =====================DB INTERACTION======================================

    def log_activity(self, bot, update):
        """Funzione per loggare le activity dentro il db"""

        message = update.message

        msg_type, msg_content = self.get_type_content(message)
        msg_user_id = message.from_user.id

        self.db.add_activity(msg_user_id, str(msg_content), msg_type)

    def get_activity_by(self, what, min=False):
        """Prendi le actiity dal db secondo what
        @:param what: puo essere un int per id_user, una str per typo o un datetime per le date
        @:param min: se è presente un datetime allora min indica che vuoi le date minori """

        if isinstance(what, str) and what in self.types:
            return self.db.get_activity(type=what)
        elif isinstance(what, str) and "all" in what:
            return self.db.get_activity()
        elif isinstance(what, int):
            return self.db.get_activity(user=what)
        elif isinstance(what, datetime) and min:
            return self.db.get_activity(date_min=what)
        elif isinstance(what, datetime) and not min:
            return self.db.get_activity(date_max=what)
        else:
            return False

    # ============================GETTER UTILS===========================================

    def get_most_active_user(self, piu=True):
        """Ritorna lo user piu attivo nel gruppo
        @:param piu: bool per permettere di prendere il piu attivo o il meno
        @:type: bool
        @:return: user"""
        activity = self.get_activity_by("all")
        if not activity: return
        activity = [elem['id_user'] for elem in activity]

        counter = Counter(activity)
        if piu:
            top = sorted(counter.items(), key=operator.itemgetter(1), reverse=True)
        else:
            top = sorted(counter.items(), key=operator.itemgetter(1))

        user = False
        idx = 0
        # se uno user non è presente nel db prendi il successivo
        while not user and idx != len(top):
            user = self.db.get_user(top[idx][0])
            idx += 1

        return user, top[idx][1]

    def get_top_emoji(self, text, emoji_bool=True):
        """Ritorna le top emoji trovate nel testo
        @:param text: il testo in cui cercare le emoji
        @:type: str
        @:param emoji_bool: boolean per trasformare le emoji da testo in emoji
        @:type:bool default true
        @:return: lista con di tuple del tipo (emoji, ripetizioni)"""

        # trovo le emoji nel testo
        emoji_regex = re.compile(r":([a-z_]+):")
        find = re.findall(emoji_regex, text)

        counter = Counter(find)
        # sorto il dizionario
        sorted_x = sorted(counter.items(), key=operator.itemgetter(1), reverse=True)

        if emoji_bool:
            res = []
            for elem in sorted_x:
                res.append((emoji.emojize(":" + elem[0] + ":"), elem[1]))
        else:
            res = sorted_x

        return res

    def get_day_activity(self):
        """Questa funzione ritorna l'attivita giornaliera
        @:return: stringa da inviare all'utente"""

        number_to_day = {1: "Lunedì", 2: "Martedì", 3: "Mercoledì", 4: "Giovedì", 5: "Venerdì", 6: "Sabato",
                         7: "Domenica"}

        to_send = "Attività giornaliera:\n"
        # prendi tutte le activity
        activity = self.get_activity_by("all")
        # seleziona solo le date
        activity = [elem['date'] for elem in activity]
        # aggiungi un ora
        activity = [elem + datetime.timedelta(hours=1) for elem in activity]
        # trasforma in giorni
        activity = [elem.isoweekday() for elem in activity]
        # conta le ripetizioni
        counter = Counter(activity)

        tot = sum(counter.values())

        for elem in counter.keys():
            to_send += "<b>" + number_to_day[elem] + "</b> " + self.filler(tot, counter[elem]) + "\n"

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

        # print(counter)

        tot = sum(counter.values())
        od = sorted(counter.items())

        for elem in od:
            if elem[0] < 10:
                to_send += "  <b>" + str(elem[0]) + ":00</b> " + self.filler(tot, elem[1] * 5) + "\n"
            else:
                to_send += "<b>" + str(elem[0]) + ":00</b> " + self.filler(tot, elem[1] * 5) + "\n"

        return to_send

    def get_type_content(self, message):
        """Ritorna il tipo del messaggio ricevuto
        @:param message: il messaggio ricevuto
        @type: Telegram.message
        #:return: stringa rappresentante il tipo di messaggio ricevuto + content"""

        if message.text:
            return "text", emoji.demojize(message.text)
        elif message.audio:
            return "audio", message.audio.file_id
        elif message.document:
            return "document", message.document.file_id
        elif message.photo:
            return "photo", message.photo[0].file_id

        elif message.sticker:
            return "sticker", message.sticker.file_id

        elif message.video:
            return "video", message.video.file_id

        elif message.voice:
            return "voice", message.voice.file_id

        else:
            return "unkown", message.message_id

    def get_word_count(self, text):
        """Conta le ripetizioni di delle parole nel testo
        @:param text: la stringa dove cercare le parole
        @:type: str
        @:return: lista di tuple"""

        text = re.sub(r":([a-z_]+):", ' ', text)
        counts = dict()
        words = text.split()

        emoji.get_emoji_regexp()

        for word in words:
            if len(word) < 4: continue
            if word in counts:
                counts[word] += 1
            else:
                counts[word] = 1

        sorted_x = sorted(counts.items(), key=operator.itemgetter(1), reverse=True)

        return sorted_x

    def get_preferred_sticker(self, user_activity):
        """Funzione per prendere lo sticker utilizzato piu volte dall'utente
        @:param user_activity: le attività dell'utente in questione
        @:type: list of dict
        @:return: str rappresentant l'id dello sticker"""

        user_activity = [elem['content'] for elem in user_activity if elem['type'] == "sticker"]

        counts = Counter(user_activity)

        sorted_x = sorted(counts.items(), key=operator.itemgetter(1), reverse=True)

        return sorted_x[0][0]

    # ============================CLASSIFICATION===========================================

    def delete_messages(self, bot, job):
        """Funzione per eliminare i messaggi resudi allo scadere del tempo """

        punteggio = self.db.get_activity_points_by_id(job.context['user_id'])

        # notifica l'utente di quanto tempo gli è rimasto per ripondere alle domande
        sec_message = bot.sendMessage(job.context['chat_id'], "Hai 1 minuto per rispondere a tutti i messaggi")
        seconds = self.secondi + punteggio + math.ceil(punteggio / 5)
        sleep(1)
        # fiche il tempo non scade
        while seconds > 0:
            # decrementa il tempo
            seconds -= 1
            # formatta il messaggio
            to_send = "<b>" + str(seconds) + "</b> secondi rimanenti, hai risposto a <b>" + str(
                self.answered) + "</b> messaggi"
            # modifica quello precedente
            bot.edit_message_text(
                chat_id=sec_message.chat_id,
                text=to_send,
                message_id=sec_message.message_id,
                parse_mode="HTML"
            )

            sleep(1)

        try:
            bot.delete_message(
                chat_id=job.context['last_msg'].chat_id,
                message_id=job.context['last_msg'].message_id
            )
            sleep(1)

        except telegram.error.BadRequest:
            pass

        punteggio = self.db.get_activity_points_by_id(job.context['user_id'])

        punti = math.floor(self.answered / 5)
        print("punti : " + str(punti))
        print("answered  : " + str(self.answered))

        if self.answered - punteggio < 0:
            punti = math.floor((punteggio - self.answered) / 5)
            to_send = "Purtroppo non hai risposto a piu domande dei punti che hai...perdi " + str(
                punti) + " punti\nSei arrivato a " + str(punteggio - punti)
            self.db.update_activity_points(job.context['user_id'], -punti)
        else:
            punti = abs(math.floor((punteggio - self.answered) / 5))

            to_send = "Sei riuscito a rispondere a piu domande dei tuoi punti..guadagni " + str(
                punti) + " punti\nSei arrivato a " + str(punteggio + punti)
            self.db.update_activity_points(job.context['user_id'], punti)
        bot.sendMessage(job.context['chat_id'], to_send)

        # dai la possibilità di usare il comando ad altre persone
        self.is_job_running = False

    def get_to_classify(self, bot, update, job_queue, chat_data, args):
        """Funzione per inviare un tot di messaggi random con la possibilità di classificarli"""

        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è possibile solo in privata")

            return

        if self.is_job_running:
            update.message.reply_text("Qualcun'altro sta utilizzando questo comando...aspetta 1 minuto")
            return

        self.is_job_running = True

        # salva l'utente nella tabella activity_points
        self.db.insert_activity_points(update.message.from_user.id)

        # prendi tutte le activity che non hanno la cella sentiment impostata
        activity = self.get_activity_by("all")
        activity = [elem for elem in activity if not isinstance(elem['sentiment'], int)]

        if len(args) == 0:
            # manda due messaggi di benvenuto e spiegazione
            update.message.reply_text(
                "Grazie per la tua partecipazione! Il tuo contributo è di fondamentale importanza per il nostro bot")
            sleep(3)
            update.message.reply_text(
                "Ti invierò un messaggio alla volta!\n Usa i bottoni"
                " <b>Negativa, Neutrale e Positiva</b> per decidere l'emozione espressa dal messaggio.\nSe "
                "non capisci un messaggio ricorda di classificarlo come <b>Neutrale</b>\nSe risponderai a piu messaggi del tuo punteggio corrente guadagnerai un punto\n"
                "Ma se rispondi a cazzo o non fai in tempo ne perderai uno",
                parse_mode="HTML")
            sleep(13)

        non_sent, sent = self.get_classified_len()

        to_send = "Per ora sono stati classificati " + str(sent) + " messaggi su " + str(non_sent)
        update.message.reply_text(to_send)

        # inizzializza acluni parametri
        chat_data['activity'] = activity
        self.answered = 0
        chat_data['msg'] = None

        # seleziona un messaggio random
        row = random.choice(activity)
        # formatta il messaggio
        to_send = str(row['id']) + "\n" + emoji.emojize(row['content'])
        # salva il messaggio e mandalo
        message = update.message.reply_text(to_send, reply_markup=self.inline_cat)
        # salva il messaggio
        chat_data['msg'] = message

        # crea il dizionario da passare al job
        context_dict = {'chat_id': update.message.chat_id, 'last_msg': chat_data['msg'],
                        'user_id': update.message.from_user.id}
        # runna il job
        job = job_queue.run_once(self.delete_messages, 0, context=context_dict)
        # salvalo
        chat_data['job'] = job

    def classify(self, bot, update, chat_data):
        """Funzione per salvare le scelte dell'utente"""

        # incrementa le risposte
        self.answered += 1

        # prendi l'id del messaggio
        activity_id = update.callback_query.message.text.split("\n")[0]

        # prende la decisione dell'utente
        param = update.callback_query.data.split()[1]
        sentiment = int(param)

        # aggiungi il sentimento nel db
        self.db.add_sentiment_activity(sentiment, activity_id)

        # prendi un altro messaggio
        row = random.choice(chat_data['activity'])
        to_send = str(row['id']) + "\n" + emoji.emojize(row['content'])

        try:

            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=to_send,
                message_id=update.callback_query.message.message_id,
                reply_markup=self.inline_cat

            )
        except telegram.error.BadRequest:
            pass

    def visualizza_punteggio(self, bot, update):
        """Invia all'user il suo punteggio"""

        punteggio = self.db.get_activity_points_by_id(update.message.from_user.id)
        # print(punteggio)

        to_send = "Il tuo punteggio è pari a <b>" + str(punteggio) + "</b>"
        update.message.reply_text(to_send, parse_mode="HTML")

    def top_punteggio(self, bot, update):
        """Visualizza la top dei punteggi"""
        users = self.db.get_activity_points_all()

        users = [(elem['username'], elem['points']) for elem in users]

        sorted_x = sorted(users, key=lambda tup: tup[1], reverse=True)

        to_send = "Top punteggi\n"
        for elem in sorted_x:
            to_send += "@" + elem[0] + " con <b>" + str(elem[1]) + "</b>\n"

        update.message.reply_text(to_send, parse_mode="HTML")

    def classified(self, bot, update):
        classified = self.get_activity_by("all")
       # print([(elem['content'],elem['sentiment']) for elem in classified if isinstance(elem['sentiment'], int) and elem['sentiment'] == 1])
        #print([(elem['content'],elem['sentiment']) for elem in classified if isinstance(elem['sentiment'], int) and elem['sentiment'] == -1])

        all_len = len(classified)
        classified = [elem['sentiment'] for elem in classified if isinstance(elem['sentiment'], int)]
        classified_len = len(classified)
        neutral_len = len([elem for elem in classified if elem == 0])
        positive_len = len([elem for elem in classified if elem == 1])
        negative_len = len([elem for elem in classified if elem == -1])


        to_send = "Sono stati classificati " + str(classified_len) + " messaggi su " + str(all_len) + ", di cui:\n" \
                                                                                                      "Positivi " + str(
            positive_len) + " (" + str(math.ceil(positive_len / classified_len * 100)) + \
                  "%)\nNegativi " + str(negative_len) + " (" + str(math.ceil(negative_len / classified_len * 100)) + \
                  "%)\nNeutrali " + str(neutral_len) + " (" + str(math.ceil(neutral_len / classified_len * 100)) + "%)"

        update.message.reply_text(to_send)

    def get_all_pred(self, bot, update):

        all= self.get_activity_by("all")
        to_send=""

        users_id=set([elem['id_user'] for elem in all if elem['type']=="text"])

        for user_id in users_id:
            to_send="@"+ self.db.get_user(user_id)['username']+"\n"
            pred=self.analyzer.predict(self.analyzer.sgdc,[elem for elem in all if elem['type']=="text" and elem['id_user']==user_id])
            pred = numpy.array(pred)
            median=pred.mean()
            std=pred.std()
            mad=robust.mad(pred)
            mean = numpy.median(pred)
            to_send += "SVC - Median: " + "{:,}".format(mean) + "\nMad:  " + "{:,}".format(mad) + "\nMean: "+ "{:,}".format(mean)+"\nStd: "+ "{:,}".format(std)+" \n"
            update.message.reply_text(to_send)

        #usa mediana e std con meadin absolute deviation



    # ============================OTHER UTILS===========================================

    def esci(self, user_data):
        """Funizione per resettare lo user data"""
        user_data['inline_main'] = None

    def filler(self, tot, val):
        """Ritorna un stringa che indica il valore in percentuale"""
        perc = math.ceil(val / tot * 10)

        res = ""
        for i in range(0, perc):
            res += "■"

        for i in range(0, 10 - perc):
            res += "□"

        return res

    def get_classified_len(self):
        """ritorna la lunghezza dei messaggi classificati e totali"""
        activity = self.get_activity_by("all")
        sentiment = [elem for elem in activity if isinstance(elem['sentiment'], int)]

        # print(activity)
        # print(sentiment)
        return len(activity), len(sentiment)


class TrackFilter(BaseFilter):
    """Filtro personalizzato per il track activity sul gruppo dei fancazzisti"""

    def __init__(self):
        # id del gruppo
        self.bot_per_i_boss = -1001284891867
        self.fancazzisti = -1001050402153

    def filter(self, message):
        """Ritorna true se il messaggio proviene dal gruppo e non è un comando"""
        # print(message)
        if message.from_user.is_bot: return False
        if message.chat.id == self.fancazzisti:

            try:
                if message.forward_from: return False
            except KeyError:
                pass

            try:
                if message.text.startswith('/'): return False

            finally:
                return True
        return False
