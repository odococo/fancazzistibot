import copy
import inspect
import math
import operator
import os
import random
import re
import time
from collections import Counter
from collections import OrderedDict
from datetime import timedelta, datetime

import emoji
import matplotlib as mpl
import sys
from scipy.optimize import minimize
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, RegexHandler, MessageHandler, Filters, CommandHandler, \
    CallbackQueryHandler

from Loot.comandi import Command
from Other.utils import is_numeric, catch_exception, text_splitter_bytes, pretty_time_date

mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

DEBUG = False


class Loot:
    def __init__(self, updater, db):
        self.bot = updater.bot
        self.db = db

        dispatcher = updater.dispatcher

        converstaion = 0
        # adding dispatchers
        if not DEBUG:
            ricerca_decor = db.elegible_loot_user(self.ricerca)
            stima_decor = db.elegible_loot_user(self.stima)
            dispatcher.add_handler(RegexHandler("^Lista oggetti necessari per", ricerca_decor, pass_user_data=True))
            converstion = ConversationHandler(
                [CallbackQueryHandler(self.decision, pattern="/loot", pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, stima_decor, pass_user_data=True)],

                }, fallbacks=[CommandHandler('Fine', self.annulla, pass_user_data=True)])
        else:

            dispatcher.add_handler(RegexHandler("^Lista oggetti necessari per", self.ricerca, pass_user_data=True))
            converstion = ConversationHandler(
                [CallbackQueryHandler(self.decision, pattern="/loot", pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.stima, pass_user_data=True)],

                }, fallbacks=[CommandHandler('Fine', self.annulla, pass_user_data=True)])

        dispatcher.add_handler(converstion)
        dispatcher.add_handler(CallbackQueryHandler(self.send_negozi, pattern="^/mostraNegozi", pass_user_data=True))

    @catch_exception
    def ricerca(self, bot, update, user_data):
        """Condensa la lista di oggetti di @craftlootbot in comodi gruppi da 3,basta inoltrare la lista di @craftlootbot"""
        # controlla che il messaggio sia mandato in privato
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return

        # inizzializza i campi di user data
        user_data['costo_craft'] = 0
        user_data['stima_flag'] = False
        user_data['quantita'] = []
        user_data['costo'] = []
        user_data['to_send_negozi'] = []
        user_data['to_send'] = []

        # aggiungo l'user nel db items se non è presente
        if not DEBUG: self.db.add_user_to_items(update.message.from_user.id)

        text = update.message.text.lower()
        user_data['to_send'] = self.estrai_oggetti(text, user_data, update.message.from_user.id)
        try:
            # self.costo_craft = text.split("per eseguire i craft spenderai: ")[1].split("§")[0].replace("'", "")
            user_data['costo_craft'] = text.split("per eseguire i craft spenderai: ")[1].split("§")[0].replace("'", "")
        except IndexError:
            # self.costo_craft=0
            user_data['costo_craft'] = 0

        inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("Negozi", callback_data="/loot negozi")],
            [InlineKeyboardButton("Ricerca", callback_data="/loot ricerca")],
            [InlineKeyboardButton("Annulla", callback_data="/loot annulla")]

        ])
        update.message.reply_text("Puoi scegliere se visualizzare i comandi ricerca oppure ottenere una stringa negozi",
                                  reply_markup=inline)

    @catch_exception
    def decision(self, bot, update, user_data):
        param = update.callback_query.data.split()[1]

        bot.delete_message(
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id
        )
        if "ricerca" in param:

            for elem in user_data['to_send']:
                bot.sendMessage(update.callback_query.message.chat.id, elem)

            reply_markup = ReplyKeyboardMarkup([["Annulla", "Stima"]], one_time_keyboard=True)
            update.callback_query.message.reply_text(
                "Adesso puoi inoltrarmi tutti i risultati di ricerca di @lootplusbot per "
                "avere il totale dei soldi da spendere. Quando hai finito premi Stima, altrimenti Annulla.",
                reply_markup=reply_markup)
            # self.stima_flag = True
            user_data['stima_flag'] = True
            return 1
        elif "negozi" in param:
            to_send_list = []
            to_send = "/negozio "
            idx = 0
            for elem in user_data['quantita']:
                to_send += elem[1] + "::" + elem[0] + ","
                idx += 1
                if idx == 9:
                    to_send_list.append(to_send.rstrip(","))
                    to_send = "/negozio "
                    idx = 0

            to_send = to_send.rstrip(",")
            to_send_list.append(to_send)
            for elem in to_send_list:
                bot.sendMessage(update.callback_query.message.chat.id, elem)
            return ConversationHandler.END
        elif "annulla" in param:
            return self.annulla(bot, update, user_data, msg="Ok annullo")

    def stima(self, bot, update, user_data):
        """ Inoltra tutte i messaggi /ricerca di @lootbotplus e digita /stima. Così otterrai il costo totale degli oggetti, la
               top 10 di quelli piu costosi e una stima del tempo che impiegherai a comprarli tutti."""

        if not user_data['stima_flag']: return

        if update.message.text == "Annulla":
            return self.annulla(bot, update, user_data)
        elif update.message.text == "Stima":

            if not user_data['stima_flag']:
                update.message.reply_text(
                    "Per usare questo comando devi aver prima inoltrato la lista di @craftlootbot!")
                return 1

            if len(user_data['costo']) == 0:
                update.message.reply_text("Non hai inoltrato nessun messaggio da @lootbotplus")
                return self.annulla(bot, update, user_data)

            """"merged è una lista di quadruple con i seguenti elementi:
            elem[0]= quantità oggetto
            elem[1]= nome oggetto
            elem[2]= costo oggetto
            elem[3]= numero negozio per oggetto"""
            merged = []

            for q in user_data['quantita']:
                c = [item for item in user_data['costo'] if item[0] == q[1]]
                if (len(c) > 0):
                    c = c[0]
                    merged.append((q[0], q[1], c[1], c[2]))

            tot = 0
            tempo = 0
            for elem in merged:
                if is_numeric(elem[0]):
                    tot += int(elem[0]) * int(elem[2])
                    tempo += 9 + 3 * int(elem[0])

            # tot += int(self.costo_craft)
            tot += int(user_data['costo_craft'])

            update.message.reply_text("Secondo le stime di mercato pagherai " +
                                      "{:,}".format(tot).replace(",", "'") + "§ (costo craft incluso)",
                                      reply_markup=ReplyKeyboardRemove())

            top_ten = []
            """top_ten è una lista con :
            elem[0]= nome oggetto
            elem[1]= costo oggetto*quantita
            elem[2]= quantita
            elem[3]= costo singolo"""
            for elem in merged:
                top_ten.append((elem[1], int(elem[0]) * int(elem[2]), elem[0], elem[2]))
            top_ten.sort(key=lambda tup: tup[1], reverse=True)

            if (len(top_ten) > 3):
                if not len(top_ten) <= 10: top_ten = top_ten[:9]

                to_print = "I " + str(len(top_ten)) + " oggetti piu costosi sono:\n"
                for elem in top_ten:
                    to_print += "<b>" + elem[0] + "</b> : " + str(elem[3]) + "§ "
                    if int(elem[2]) != 1:
                        to_print += "( quantità = <b>" + str(elem[2]) + "</b>, totale = <b>" + str(elem[1]) + "</b>§ )"
                    to_print += "\n"

                update.message.reply_text(to_print, parse_mode="HTML")

            m, s = divmod(tempo, 60)

            update.message.reply_text("Comprando gli oggetti dal negozio impiegherai un tempo di circa :\n "
                                      + str(m) + " minuti e " + str(s) + " secondi\n")

            for elem in merged:

                if int(elem[0]) > 1:
                    user_data['to_send_negozi'].append("Compra <b>" + elem[1] + "</b> (<b>" + str(
                        elem[0]) + "</b>) al negozio:\n<pre>@lootplusbot " + str(elem[3]) + "</pre>\n")

                else:

                    user_data['to_send_negozi'].append("Compra <b>" + elem[
                        1] + "</b> al negozio:\n<pre>@lootplusbot " + str(elem[3]) + "</pre>\n")

            update.message.reply_text("Vuoi visualizzare i negozi?", reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Si", callback_data="/mostraNegoziSi"),
                InlineKeyboardButton("No", callback_data="/mostraNegoziNo")
            ]]))

            user_data['costo'].clear()
            user_data['quantita'].clear()
            user_data['stima_flag'] = False
            return ConversationHandler.END
        elif "Risultati ricerca" in update.message.text:
            self.stima_parziale(update.message.text.lower(), user_data)
            return 1
        else:
            to_send = "Non ho capito il messaggio... sei sicuro di aver inoltrato quello di @lootplusbot (" \
                      "inizia con 'Risultati ricerca di')? Purtroppo ho dovuto annullare tutto altrimenti vado in palla, ma non disperare!\n" \
                      "Basta che ri-inoltri il messaggio lista di @craftlootbot e poi ri-inoltri tutti i messaggi di @lootplusbot, senza" \
                      "dover rieffettuare tutte le ricerche nuovamente 👍🏼👍🏼"
            return self.annulla(bot, update, user_data, to_send)

    @catch_exception
    def stima_parziale(self, msg, user_data):
        """dato un messaggio in lower inoltrato da lootplusbot rappresentate la risposta la comando ricerca
        salva la lista costo con una tripla di elementi:
        elem[0]: nome oggetto
        elem[1]: costo oggetto
        elem[2]: numero negozio"""
        prov = msg.split("negozi per ")[1:]
        lst = []
        for elem in prov:
            lst.append((elem.split(">")[0].replace("\n", "") + elem.split(">")[1].replace("\n", "")))

        regex = re.compile(r"(.*):.*\(([0-9 .]+)")
        regex_negozio = r"§ - ([0-9]+)"

        for elem in lst:
            e = re.findall(regex, elem)
            neg = re.findall(regex_negozio, elem)

            #  self.costo.append((e[0][0], e[0][1].replace(".", "").replace(" ", ""), neg[0]))
            user_data['costo'].append((e[0][0], e[0][1].replace(".", "").replace(" ", ""), neg[0]))

    @catch_exception
    def annulla(self, bot, update, user_data, msg=""):
        """Finisce la conversazione azzerando tutto
         msg: è il messaggio inviato all'utente
         return : fine conversazione"""

        if not msg: msg = "Ok ho annullato tutto"

        user_data['stima_flag'] = False
        user_data['costo_craft'] = 0
        user_data['quantita'] = []

        try:
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        except KeyError:
            bot.sendMessage(update.callback_query.message.chat.id, msg, reply_markup=ReplyKeyboardRemove())
        finally:
            return ConversationHandler.END

    @catch_exception
    def send_negozi(self, bot, update, user_data):
        addon = ""

        if "Si" in update.callback_query.data:

            if not 'to_send_negozi' in user_data.keys():  # se la key non è presente nel dizionario c'è qualcosa che non va
                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text="Si è verificato un errore, contatta @brandimax e riprova",
                    message_id=update.callback_query.message.message_id,
                    parse_mode="HTML"
                )
                return

            if len(user_data['to_send_negozi']) > 0 and len(user_data['to_send_negozi']) < 31:
                to_change = "".join(user_data['to_send_negozi'])
            elif len(user_data['to_send_negozi']) > 0:
                to_change = "".join(user_data['to_send_negozi'][:29])
                addon = "".join(user_data['to_send_negozi'][29:])

            else:
                to_change = "Si è verificato un errore, contatta @brandimax"
        else:
            to_change = "Ok"

        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_change,
            message_id=update.callback_query.message.message_id,
            parse_mode="HTML"
        )
        if addon:
            bot.sendMessage(update.callback_query.message.chat_id, addon, parse_mode="HTML")
            update.message.reply_text(addon, parse_mode="HTML")

            # self.to_send_negozi = []
        user_data['to_send_negozi'] = []

    @catch_exception
    def salva_rarita_db(self, rarita, user_id):
        if not rarita:
            # print("Non ho trovato rarità")
            return
        rarita = dict(Counter(rarita))
        self.db.update_items(rarita, user_id)

    @catch_exception
    def estrai_oggetti(self, msg, user_data, user_id):
        """Estrae gli ogetti piu quantità dal messaggio /lista dicraftlootbot:
                msg: messaggio.lower()
                return string: rappresentante una lista di /ricerca oggetto\n
            Salva anche le rarità nel db"""
        # prendo solo gli oggetti necessari
        restante = msg.split("già possiedi")[0].split(":")[1]
        aggiornato = ""

        # regex in caso di zaino salvato
        regex_numeri = re.compile(r"> ([0-9]+) su ([0-9]+)")
        # regex in caso di zaino non salvato (inizia con 'di')
        to_loop = restante.split("\n")
        to_loop.pop(0)  # il primo elemnto è vuoto
        to_loop = list(filter(None, to_loop))  # anche gli ultimi 4
        for line in to_loop:  # capita di possedere 2 su 3 oggetti, per semplicità sostituisco entrambi i numeri con (3-2=1)
            num = re.findall(regex_numeri, line)  # cerco i sue numeri
            try:
                num = num[0]  # prendo l'elemento trovato
                if num[0] != num[1]:  # se i due numeri sono diversi
                    # new_num = int(num[1]) - int(num[0])  # calcolo la differenza

                    # new_line = line.replace(num[0], str(new_num), 1)  # rimpiazzo il primo
                    new_line = line.replace(num[1], num[0], 1)  # e il secondo
                    aggiornato += new_line + "\n"  # aggiungo la riga aggiornata
                else:
                    aggiornato += line + "\n"

            except IndexError:
                aggiornato += line + "\n"

        regex_comandi = re.compile(r"di (.*)?\(")
        regex_zaino_completo = re.compile(r"su ([0-9]+) di (.*)?\(")
        regex_zaino_vuoto = re.compile(r"> ([0-9]+) di ([A-z ]+)")
        regex_rarita = re.compile(r"\(([a-z]+)\)")
        lst = re.findall(regex_comandi, aggiornato)  # per i comandi
        if not DEBUG: self.salva_rarita_db(re.findall(regex_rarita, aggiornato), user_id)
        quantita = re.findall(regex_zaino_completo, aggiornato)
        if not quantita: quantita = re.findall(regex_zaino_vuoto,
                                               aggiornato)  # se cerchi con lo zaino vuoto cambia il messaggio
        commands = []
        # self.quantita = [(q[0], q[1].rstrip()) for q in quantita]
        user_data["quantita"] = [(q[0], q[1].rstrip()) for q in quantita]
        last_ixd = len(lst) - len(lst) % 3
        for i in range(0, (last_ixd) - 2, 3):
            commands.append("/ricerca " + ",".join(lst[i:i + 3]))

        if last_ixd < len(lst): commands.append("/ricerca " + ",".join(lst[last_ixd:len(lst)]))

        return commands


class Boss:
    def __init__(self, updater, db):
        """Questa classe è utilizzate per gestire gli attacchi al boss, i parametri sono:
        updater : updater per il bot e il dispatcher
        db:
        Le variabili di classe:
        lista_boss : La lista ritornata dalla funzione cerca boss, non vuota solo dopo che un admin ha inoltrato
                    il messaggio team
        punteggi: punteggi può variare a seconda dei dati preseti nel db:
                nel caso in cui nel db ci sia solo un utente con informazioni sia sulla tabella users che punteggi
                allora questo diventa un dizionario con chiavi [date, first_name, id, msg_id, language_code, username,
                 valutazione, last_name, attacchi]
                Se sono presenti piu elementi allora viene ritornata una lista di dizionari come sopra
        last_update_id: viene salvato nel db per impedire che vengano caricati due volte gli stessi messaggi
        phoenix: boolean che fa da flag per la scelta del boss
        single_dict, boolean,serve come falg per sapere se il dizionario del database contiene un solo utente sotto la tabella punteggio
                
        """
        self.bot = updater.bot
        self.db = db

        self.attacca_boss_frasi = ["Attacca il boss dannazzione!",
                                   "Lo hai attaccato il boss?", "Se non attacchi il boss ti prendo a sberle",
                                   "Attacca il boss ORA"]

        dispatcher = updater.dispatcher

        if not DEBUG:
            boss_user_decor = db.elegible_loot_user(self.boss_user)
            boss_admin_decor = db.elegible_loot_user(self.boss_completa)
            reset_boss_ask_decor = db.elegible_loot_admin(self.boss_reset_ask)

            coversation_boss = ConversationHandler(
                [CommandHandler("attacchiboss", boss_user_decor, pass_user_data=True),
                 RegexHandler("^🏆", boss_admin_decor, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.boss_loop, pass_user_data=True)]
                },
                fallbacks=[CommandHandler('Fine', self.fine, pass_user_data=True)]
            )
            dispatcher.add_handler(coversation_boss)

            dispatcher.add_handler(CommandHandler("resetboss", reset_boss_ask_decor))
        else:
            coversation_boss = ConversationHandler(
                [CommandHandler("attacchiboss", self.boss_user, pass_user_data=True),
                 RegexHandler("^🏆", self.boss_completa, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.boss_loop, pass_user_data=True)]
                },
                fallbacks=[CommandHandler('Fine', self.fine, pass_user_data=True)]
            )
            dispatcher.add_handler(coversation_boss)

            dispatcher.add_handler(CommandHandler("resetboss", self.boss_reset_ask))

        dispatcher.add_handler(
            CallbackQueryHandler(self.boss_reset_confirm, pattern="^/resetBoss", pass_user_data=True))

    def cerca_boss(self, msg):
        """Dato il messaggio di attacco ai boss ritorna una lista di liste con elementi nel seguente ordine:\n
        lista[0]: nome \n
        lista[1]: Missione/cava + tempo se in missione o cava, 1 altrimenti\n
        lista[2]: 0 se non c'è stato attacco al boss, tupla altrimenti: tupla[0] danno, tupla[1] numero di boss"""

        # prendi il messaggio
        prova = msg.split("Attività membri:\n")[1]
        # trasforma le omoji in testo
        prova = emoji.demojize(prova)
        # compila i pattern
        name_reg1 = re.compile(r"([0-z_]+) :")
        name_reg2 = re.compile(r"^([0-z_]+) .*")
        obl_reg = re.compile(r":per.*: ([0-z /(/)]+)")
        boss_reg = re.compile(r":boar: ([0-9]+) .*/([0-9]+)")

        res = []

        # cerca tutto con i vari regex
        for elem in prova.split("\n\n"):
            try:
                name = re.findall(name_reg1, elem)[0]
            except IndexError:
                name = re.findall(name_reg2, elem)[0]
            obl = re.findall(obl_reg, elem)
            boss = re.findall(boss_reg, elem)[0]
            if (len(obl) == 0):
                obl = 1
            else:
                obl = obl[0]
            if boss[0] == "0": boss = 0
            res.append([name, obl, boss])

        return res

    def inizzializza_user_data(self, user_data):
        user_data['lista_boss'] = []
        user_data['punteggi'] = []
        user_data['last_update_id'] = 0
        user_data['phoenix'] = False
        user_data['single_dict'] = True

    @catch_exception
    def boss_completa(self, bot, update, user_data):
        """Inoltra il messaggio del boss, solo per admin
        @:return: ritorna lo state del prossimo handler"""

        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return
        # prendi il dizionario, lista  e id
        self.inizzializza_user_data(user_data)
        # prendi i dati dal databse
        boss = self.db.get_punteggi_username()
        # se è vuoto inizzializza
        if not boss:
            boss = {}
            id = 0
        else:
            # differenza tra dizionario e lista
            try:
                id = boss[0]["msg_id"]
                user_data['single_dict'] = False
            except KeyError:
                id = boss["msg_id"]

        # salva i dati
        user_data['punteggi'] = boss
        user_data['last_update_id'] = id

        user_data['lista_boss'] = self.cerca_boss(update.message.text)

        # genera e invia risposta

        if self.db.is_loot_admin(update.message.from_user.id):
            # se il messaggio presenta le stesse info avverti l'user
            if self.same_message(boss, user_data['lista_boss']):
                reply_markup = ReplyKeyboardMarkup([["Phoenix", "Titan"], ["Sveglia", "Annulla"], ["Visualizza"]],
                                                   one_time_keyboard=True)

                update.message.reply_text("Hai gia mandato questo messaggio... il database non verrà aggiornato",
                                          reply_markup=reply_markup)
                return 1

            reply_markup = ReplyKeyboardMarkup([["Phoenix", "Titan"], ["Sveglia", "Annulla"], ["Visualizza"]],
                                               one_time_keyboard=True)
            update.message.reply_text(
                "Scegli un boss per salvare il punteggio, clicca sveglia per mandare un messaggio a chi non ha attaccato, Visualizza per vedere le info senza salvare i punteggi, oppure annulla.",
                reply_markup=reply_markup)
        else:
            reply_markup = ReplyKeyboardMarkup([["Visualizza"]],
                                               one_time_keyboard=True)
            update.message.reply_text("Clicca su visualizza per proseguire",
                                      reply_markup=reply_markup)
        return 1

    @catch_exception
    def boss_user(self, bot, update, user_data):
        """Se un user vuole visualizzare le stesse info degli admin non ha diritto alle modifiche
                @:return: ritorna lo state del prossimo handler"""
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return
        # prendi le info dal db
        self.inizzializza_user_data(user_data)
        user_data['punteggi'] = self.db.get_punteggi_username()

        reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Fine"]],
                                           one_time_keyboard=False)
        update.message.reply_text("Quali info vuoi visualizzare?", reply_markup=reply_markup)
        return 1

    @catch_exception
    def boss_reset_confirm(self, bot, update, user_data):
        """Conferma l'operazione di reset dei punteggi"""
        if "Si" in update.callback_query.data:
            user_data['lista_boss'] = []
            user_data['punteggi'] = {}
            user_data['last_update_id'] = 0
            user_data['phoenix'] = False

            self.db.reset_punteggio()
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text="Punteggi resettati!",
                message_id=update.callback_query.message.message_id)
        else:
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text="Hai annullato il reset dei punteggi",
                message_id=update.callback_query.message.message_id
            )

    @catch_exception
    def boss_reset_ask(self, bot, update):
        """Chiede la conferma per il reset dei punteggi"""
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return
        update.message.reply_text("Sei sicuro di voler resettare i punteggi?\nNon potrai piu recuperarli",
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton("Si", callback_data="/resetBossSi"),
                                      InlineKeyboardButton("No", callback_data="/resetBossNo")
                                  ]]))

    @catch_exception
    def boss_loop(self, bot, update, user_data):
        """Funzione di loop dove ogni methodo , tranne fine, ritorna dopo aver inviato il messaggio"""

        choice = update.message.text
        if choice == "Non Attaccanti":
            return self.non_attaccanti(bot, update, user_data)
        elif choice == "Punteggio":
            return self.punteggio(bot, update, user_data)
        elif choice == "Completa":
            return self.completa(bot, update, user_data)
        elif choice == "Fine":
            return self.fine(bot, update, user_data)

        # se l'admin vuole modificare la lista
        # todo: cerca perche triplo sette non appare nel db
        elif choice == "Phoenix" or choice == "Titan":
            if choice == "Phoenix":
                user_data['phoenix'] = True
            else:
                user_data['phoenix'] = False

            # todo: trova un'equivalente di id che non cambia ongi volta che rinvii lo stesso messaggio

            if user_data['last_update_id'] == update.message.message_id:
                update.message.reply_text("Stai cercando di salvare lo stesso messaggio due volte!")
                return 1
            else:
                user_data['last_update_id'] = update.message.message_id

            # aggiunge i membri nel dizionario se non sono gia presenti
            skipped = []
            users = self.db.get_users()
            users_name = [elem["username"] for elem in users]
            users_name_id = [(elem["username"], elem['id']) for elem in users]

            # se ho un solo dizionario ne creo una lista per far funzionare il cilo successivo
            if user_data['single_dict']: user_data['punteggi'] = [user_data['punteggi']]

            for username in user_data['lista_boss']:
                # se lo username è presente nella tabella users del db ma la tabella dei punteggi è vuota
                if username[0] in users_name and not bool(user_data['punteggi'][0]):
                    user_data['punteggi'].append({'username': username[0],
                                                  # aggiungo l'id associato
                                                  'id': [elem[1] for elem in users_name_id if
                                                         elem[0] == username[0]].pop(0),
                                                  'valutazione': 0,
                                                  'attacchi': 0})  # aggiungo l'user alla lista

                # se lo username è presente nella tabella users del db ma non nel dizionario (quindi non nella tabella punteggi del db)
                elif username[0] in users_name and not username[0] in [elem['username'] for elem in
                                                                       user_data['punteggi']]:
                    user_data['punteggi'].append({'username': username[0],
                                                  'id': [elem[1] for elem in users_name_id if
                                                         elem[0] == username[0]].pop(0),
                                                  # aggiungo l'id associato
                                                  'valutazione': 0,
                                                  'attacchi': 0})  # aggiungo l'user alla lista

            # print(user_data)
            found = False
            # rimuovi dizionari vuoti
            user_data['punteggi'] = list(filter(None, user_data['punteggi']))
            print(user_data)

            # per ogni elemento nel messaggio inviato
            for username in user_data['lista_boss']:

                # per ogni username in punteggi
                for single_dict in user_data['punteggi']:

                    # se è gia presente nel db
                    if single_dict['username'].lower() == username[0].lower():
                        found = True

                        single_dict['msg_id'] = user_data['last_update_id']

                        # non ha attaccato ed è phoenix
                        if user_data['phoenix'] and isinstance(username[2], int):
                            single_dict['valutazione'] += 2

                        # non ha attaccato ed è titan
                        elif not user_data['phoenix'] and isinstance(username[2], int):
                            single_dict['valutazione'] += 1

                        elif isinstance(username[2], tuple):  # ha attaccato
                            # aggiungo gli attacchi
                            single_dict['attacchi'] = username[2][1]

                if not found:
                    skipped.append(username)
                found = False

            # se non ho saltato tutti gli username
            if not len(skipped) == len(user_data['lista_boss']):
                print("all skipped")
                self.db.update_punteggi(user_data['punteggi'])

            # notifica gli users che il punteggio è stato aggiornato
            # for elem in user_data['punteggi']:
            #     bot.sendMessage(elem['id'],"Le valutazioni sono state aggiornate!\n"
            #                                "Sei arrivato al punteggio <b>"+str(elem['valutazione'])+"</b>\n"
            #                                 "Per consultare le regole usa il comando /regoleboss")

            if len(skipped) > 0:
                to_send = "I seguenti users non sono salvati nel bot :\n"
                for users in skipped:
                    to_send += "@" + users[0] + "\n"
                to_send += "Chiedigli di inviare /start a @" + bot.username + " , in privato"
                update.message.reply_text(to_send)

            reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Completa", "Fine"]],
                                               one_time_keyboard=False)
            update.message.reply_text("Dati salvati!\nAdesso fammi sapere in che formato vuoi ricevere le info",
                                      reply_markup=reply_markup)

            return 1

        elif choice == "Annulla":
            return self.fine(bot, update, user_data, "Ok")
        elif choice == "Sveglia":
            # prendo gli users in punteggi e nel messaggio
            punteggi_users = self.db.get_punteggi_username()
            attacchi_users = user_data['lista_boss']

            # prendo solo gli username di chi non ha attaccato
            attacchi_users = [elem[0] for elem in attacchi_users if elem[2] == 0]
            # faccio lo stesso con i punteggi
            punteggi_users = [elem for elem in punteggi_users if elem['username'] in attacchi_users]

            if not punteggi_users:
                update.message.reply_text("Tutti gli users presenti nel bot hanno attaccato il boss")
                return self.fine(bot, update, user_data)

            # mando il messaggio a tutti i non attaccanti e creo la risposta
            to_send = "Ho mandato un messaggio ai seguenti users:\n"
            for elem in punteggi_users:
                bot.sendMessage(elem['id'], random.choice(self.attacca_boss_frasi))
                to_send += "@" + elem['username'] + "\n"

            update.message.reply_text(to_send)

        elif choice == "Visualizza":
            reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Completa", "Fine"]],
                                               one_time_keyboard=False)
            update.message.reply_text("Quali info vuoi visualizzare?", reply_markup=reply_markup)
            return 1


        else:
            # print(choice)
            update.message.reply_text("Non ho capito")
            return self.fine(bot, update, user_data, msg="Non ho capito, annullo tuttto")

    @catch_exception
    def punteggio(self, bot, update, user_data):
        """Visualizza la sita di tutti con punteggio annesso"""

        if not user_data['punteggi']:
            return self.fine(bot, update, user_data, "La lista è vuota! Chiedi agli admin di aggiornarla")

        # sortedD = sorted([(elem['username'], elem['valutazione']) for elem in self.punteggi], reverse=True)
        punteggi = user_data['punteggi']
        if not isinstance(punteggi, list): punteggi = [punteggi]
        sortedD = sorted([(elem['username'], elem['valutazione']) for elem in punteggi], reverse=True)

        num = [elem[1] for elem in sortedD]

        to_send = ""

        if any(elem > 3 for elem in num): to_send = "\n⛔️⛔️<b>Giocatori da espellere</b>⛔️⛔️\n"
        for elem in sortedD:
            if elem[1] > 3: to_send += "@" + str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

        if 3 in num: to_send += "\n❗️❗️<b>Giocatori a rischio espulsione</b>❗️❗️️\n"
        for elem in sortedD:
            if elem[1] == 3: to_send += "@" + str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

        if 2 in num: to_send += "\n⚠<b>️Non proprio i migliori</b>⚠️\n"
        for elem in sortedD:
            if elem[1] == 2: to_send += "@" + str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

        if 1 in num: to_send += "\n✅<b>Buono ma non buonissimo</b>✅\n"
        for elem in sortedD:
            if elem[1] == 1: to_send += "@" + str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

        if 0 in num: to_send += "\n🎉<b>I nostri best players</b>🎉\n"
        for elem in sortedD:
            if elem[1] == 0: to_send += str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

        update.message.reply_text(to_send, parse_mode="HTML")
        return 1  # 1 è l'id del boss_loop nel conversation handler

    @catch_exception
    def completa(self, bot, update, user_data):
        """Visualizza la lista completa ti tutte le info"""

        if not len(user_data['lista_boss']) > 0:
            return self.fine(bot, update, user_data, "Devi prima inoltrare il messaggio dei boss!")

        to_send = "✅ <b>Hanno attaccato</b>:\n"

        attaccato = sorted([elem for elem in user_data['lista_boss'] if elem[2] != 0], key=lambda tup: int(tup[2][0]),
                           reverse=True)
        non_attaccato = [elem for elem in user_data['lista_boss'] if elem[2] == 0]

        i = 1
        for elem in attaccato:
            if i == 1:
                to_send += "🥇" + str(i) + ") "
            elif i == 2:
                to_send += "🥈" + str(i) + ") "
            elif i == 3:
                to_send += "🥉" + str(i) + ") "
            else:
                to_send += str(i) + ") "
            to_send += str(elem[0]) + " : facendo <b>" + '{:,}'.format(int(elem[2][0])).replace(',',
                                                                                                '\'') + "</b> danno con <b>" + str(
                elem[2][1]) + "</b> attacchi\n"
            i += 1

        if non_attaccato: to_send += "\n❌ <b>Non hanno attaccato</b>:\n"

        i = 1
        for elem in non_attaccato:
            to_send += str(i) + ") @" + str(elem[0])
            if elem[1] == 1:
                to_send += ", può attaccare\n"
            else:
                to_send += ", non può attaccare perchè in " + str(elem[1]) + "\n"
            i += 1

        update.message.reply_text(to_send, parse_mode="HTML")
        return 1

    @catch_exception
    def fine(self, bot, update, user_data, msg=""):
        if not msg: msg = "Fine"
        update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        user_data['lista_boss'] = []
        return ConversationHandler.END

    @catch_exception
    def non_attaccanti(self, bot, update, user_data):
        """Visualizza solo la lista di chi non ha ancora attaccato"""

        punteggi = user_data['punteggi']
        if not isinstance(punteggi, list): punteggi = [punteggi]

        if not len(punteggi) > 0:
            return self.fine(bot, update, user_data, "La lista è vuota! Chiedi agli admin di aggiornarla")

        to_send = ""

        for elem in [(elem['attacchi'], elem['username']) for elem in punteggi]:
            if (elem[0] == 0): to_send += str(elem[1]) + "\n"

        if not to_send: to_send = "Hanno attaccato tutti quelli iscritti al bot!"

        update.message.reply_text(to_send)
        return 1

    def same_message(self, boss_db, boss_admin):
        """Controlla che le info inviate siano uguali a quelle nel db"""
        if not boss_db:
            return False

        if not isinstance(boss_db, list):
            boss_db = [boss_db]  # rende boss_db una lista

        # print(boss_db)
        users_db = self.db.get_users()
        if not users_db: return False
        users_id = [(elem['username'], elem['id']) for elem in users_db]  # contiene la tupla username,id
        users_punteggio = [elem for elem in users_id if elem[1] in [punteggio['id'] for punteggio in
                                                                    boss_db]]  # ha solo gli elementi (username,id) che sono prenseti nel db punteggio
        users_db = [elem['username'] for elem in users_db]  # ha gli username presenti nel db users

        # guarda se ci sono nuovi utenti nel messaggio team che sono anche dentro users
        for elem in boss_admin:
            if elem[0] in users_db and not elem[0] in users_punteggio: return False

        for db in boss_db:
            for admin in boss_admin:
                if db['username'] == admin[0]:  # per ogni username gia salvato nel db punteggio
                    if isinstance(admin[2], tuple) and not admin[2][1] == db[
                        'attacchi']:  # controllo che gli attacchi siano invariati
                        return True
                    elif admin[2] == 0 and db['attacchi'] == 0:
                        return True

        return False


class Cerca:
    def __init__(self, updater, db, oggetti):
        self.bot = updater.bot
        self.db = db
        self.craftabili = oggetti

        dispatcher = updater.dispatcher

        cerca_craft_el = db.elegible_loot_user(self.cerca_craft)

        dispatcher.add_handler(CommandHandler("cercacraft", cerca_craft_el, pass_user_data=True))
        dispatcher.add_handler(CallbackQueryHandler(self.filtra_rarita, pattern="/rarita", pass_user_data=True))
        dispatcher.add_handler(CallbackQueryHandler(self.filtra_rinascita, pattern="/rinascita", pass_user_data=True))
        dispatcher.add_handler(CallbackQueryHandler(self.ordina, pattern="/ordina", pass_user_data=True))

    def inizzializza_user_data(self, user_data):
        user_data['risultati'] = []

    @catch_exception
    def cerca_craft(self, bot, update, user_data):
        """Cerca oggetti nell'intervallo craft specificato dall'utente"""
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return
        # prendi l'intervallo
        param = update.message.text.split()[1:]
        self.inizzializza_user_data(user_data)

        # controlla che ci siano 1 o due parametri
        if len(param) == 0 or len(param) > 2:
            update.message.reply_text("Il comando deve essere usato in due modi:\n"
                                      "/cercaCcraft maggioreDi minoreDi\n"
                                      "/cercaCraft maggioreDi\nIn cui maggioreDi e minoreDi sono due numeri rappresentanti"
                                      " l'intervallo di punti craft in cui vuoi cercare.")
            return

        # controlla che siano numerici
        elif len(param) == 1 and is_numeric(param[0]):
            user_data['risultati'] = [elem for elem in self.craftabili if elem['craft_pnt'] >= int(param[0])]
        elif len(param) == 2 and is_numeric(param[0]) and is_numeric(param[1]):
            magg = int(param[0])
            min = int(param[1])
            # print(magg, min)
            if magg > min:
                update.message.reply_text("Il numero maggioreDi non può essere minore del numero minoreDi")
                return
            user_data['risultati'] = [elem for elem in self.craftabili if elem['craft_pnt'] >= magg and
                                      elem['craft_pnt'] <= min]

        else:
            update.message.reply_text("Non hai inviato dei numeri corretti")
            return

        # cerca quanti oggetti sono stati trovati
        num_ris = len(user_data['risultati'])
        if num_ris == 0: return self.no_results(bot, update)

        # inline per la selezione della rarità
        inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("X", callback_data="/rarita X"),
             InlineKeyboardButton("UE", callback_data="/rarita UE"),
             InlineKeyboardButton("E", callback_data="/rarita E")],
            [InlineKeyboardButton("L", callback_data="/rarita L"), InlineKeyboardButton("U", callback_data="/rarita U"),
             InlineKeyboardButton("UR", callback_data="/rarita UR")],
            [InlineKeyboardButton("Tutti", callback_data="/rarita tutti")]
        ])
        # generazione e invio del messaggio
        text = "Ho trovato <b>" + str(num_ris) + "</b> oggetti che rispettano i tuoi parametri\n"

        update.message.reply_text(text +
                                  "Secondo quale rarità vuoi filtrare?", reply_markup=inline, parse_mode="HTML"
                                  )

    @catch_exception
    def filtra_rarita(self, bot, update, user_data):
        """Filtra i risultati trovati precedentemente a seconda della rarità"""
        # todo: prova a far scegliere piu rarità
        # prendi la rarità scelte dall'utente
        # user_data['rarita'] = update.callback_query.data.split()[1]
        rarita = update.callback_query.data.split()[1]
        # filtra se non sono state scelte tutte
        if not "tutti" in rarita:
            user_data['risultati'] = [elem for elem in user_data['risultati'] if elem['rarity'] == rarita]

        # conta i risultati
        num_ris = len(user_data['risultati'])
        if num_ris == 0: return self.no_results(bot, update)

        # genera e invia risposta
        inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("r0", callback_data="/rinascita 1"),
             InlineKeyboardButton("r1", callback_data="/rinascita 2"),
             InlineKeyboardButton("r2", callback_data="/rinascita 3")]

        ])
        text = "Ho trovato <b>" + str(num_ris) + "</b> oggetti che rispettano i tuoi parametri\n"

        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=text + "Perfetto, ora dimmi a quale rinascita sei interessato, ricorda che i risultati mostrati saranno quelli"
                        " per tutte le rinascite minori uguali a quella che hai selzionato.\nEsempio scegli r2, ti verranno mostrati i "
                        "risultati per r0, r1 e r2\n",
            message_id=update.callback_query.message.message_id,
            reply_markup=inline,
            parse_mode="HTML"

        )

    @catch_exception
    def no_results(self, bot, update):
        """Funzione da chiamare in caso non ci siano risultati della ricerca"""
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text="Non ho trovato risultati per i tuoi criteri di ricerca",
            message_id=update.callback_query.message.message_id,
        )
        return

    @catch_exception
    def filtra_rinascita(self, bot, update, user_data):
        """Filtra i risualti ottenuti precedentemente in base alla rinascita"""
        # prendi i parametri scelti dall'utente
        rinascita = update.callback_query.data.split()[1]

        # print(self.maggioreDi, self.minoreDi, self.rarita, self.rinascita)
        # filtra
        user_data['risultati'] = [elem for elem in user_data['risultati'] if elem['reborn'] <= int(rinascita)]

        # stessa storia
        if len(user_data['risultati']) == 0: return self.no_results(bot, update)

        # genera e invia risposta
        to_send = "Ho trovato <b>" + str(
            len(user_data['risultati'])) + "</b> oggetti.\nOra puoi scegliere scondo quale valore ordinarli oppure" \
                                           " annullare la ricerca"

        inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("Punti craft", callback_data="/ordina puntiCraft"),
             InlineKeyboardButton("Rarità", callback_data="/ordina rarita")],
            [InlineKeyboardButton("Rinascita", callback_data="/ordina rinascita"),
             InlineKeyboardButton("Annulla", callback_data="/ordina annulla")]

        ])
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_send,
            message_id=update.callback_query.message.message_id,
            reply_markup=inline,
            parse_mode="HTML"
        )

    @catch_exception
    def ordina(self, bot, update, user_data):
        """Ordina i risultati trovati in base alla scelta dell'utente"""
        param = update.callback_query.data.split()[1]
        to_send = ""
        sorted_res = []
        to_send = []

        if "annulla" in param:
            to_send.append("Ok annullo")

        # ordina lista in base a parametro
        elif "puntiCraft" in param:
            sorted_res = sorted(user_data['risultati'], key=lambda key: key["craft_pnt"])
        elif "rarita" in param:
            sorted_res = sorted(user_data['risultati'], key=lambda key: key["rarity"])
        elif "rinascita" in param:
            sorted_res = sorted(user_data['risultati'], key=lambda key: key["reborn"])

        # prendi l'id del messaggio
        message_id = update._effective_chat.id

        # inizzializza titolo
        if sorted_res:
            bot.sendMessage(message_id, "<b>Nome   Punti Craft    Rarità     Rinascita</b>\n", parse_mode="HTML")

        # aggiungi elemeenti
        for elem in sorted_res:
            to_send.append(
                "<b>" + elem['name'] + "</b>   " + str(elem['craft_pnt']) + "   " + elem['rarity'] + "   " + str(
                    elem["reborn"]) + "\n")

        # elimina messaggio di scelta
        bot.delete_message(
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id
        )

        # manda i messaggi ogni 30 elementi
        while to_send:
            bot.sendMessage(message_id, "".join(to_send[:30]), parse_mode="HTML")
            to_send = to_send[30:]

        # azzera lo user_data
        self.inizzializza_user_data(user_data)


class Compra:

    def __init__(self, updater, db):
        self.db = db
        self.scrigni = OrderedDict(
            [('Legno', 1200), ('Ferro', 2400), ('Prezioso', 4800), ('Diamante', 7200), ('Leggendario', 14000),
             ('Epico', 30000)])  # dizionario ordinato per mantenere la relazione quantità-tipo scrigno

        disp = updater.dispatcher

        if not DEBUG:
            eleg = self.db.elegible_loot_user(self.sconti)
            disp.add_handler(CommandHandler("compra", eleg, pass_user_data=True))

        else:
            disp.add_handler(CommandHandler("compra", self.sconti, pass_user_data=True))

        # crea conversazione
        conversation = ConversationHandler(
            [CallbackQueryHandler(self.budget_ask, pattern="/sconti", pass_user_data=True)],
            states={
                1: [MessageHandler(Filters.text, self.budget_save, pass_user_data=True)],
                2: [MessageHandler(Filters.text, self.scrigni_func, pass_user_data=True)]

            },
            fallbacks=[CommandHandler('Fine', self.inizzializza)]
        )

        disp.add_handler(conversation)

    def inizzializza(self, bot, updates, user_data):
        """Inizzializza user data
        @:param user_data: dizionario dei dati utente
        @:type: dict
        @:return: ritorna la fine della conversazione"""
        user_data['sconto'] = 0
        user_data['budget'] = 0
        return ConversationHandler.END

    def sconti(self, bot, update, user_data):
        """Chiedi allo user se sono presenti sconti all'emporio"""
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return
        self.inizzializza(bot, update, user_data)
        text = "Ci sono sconti all'emporio?"

        inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("Nessuno", callback_data="/sconti 0"),
             InlineKeyboardButton("10 %", callback_data="/sconti 0.1"),
             InlineKeyboardButton("20 %", callback_data="/sconti 0.2"),
             InlineKeyboardButton("30 %", callback_data="/sconti 0.3")]

        ])

        update.message.reply_text(text, reply_markup=inline)

    def budget_ask(self, bot, update, user_data):
        """Salva sconti e chiedi il budget
        @:return: ritorna lo state del prossimo handler (guarda ConversationHandler)"""
        user_data['sconto'] = update.callback_query.data.split()[1]

        text = "Qual'è il tuo budget? (inviami un numero)"

        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=text,
            message_id=update.callback_query.message.message_id,

        )

        return 1

    def budget_save(self, bot, update, user_data):
        """Salva budget e chiedi quantita di scrigni
        @:return: ritorna lo state del prossimo handler (guarda ConversationHandler)"""

        budget = update.message.text.strip()
        if not is_numeric(budget):
            update.message.reply_text("Non mi hai inviato un nuemro valido, annullo...")
            return self.inizzializza(bot, update, user_data)
        if not user_data['budget']: user_data['budget'] = int(budget)  # salvo soo se è la prima volta che mi trovo qui
        text = "Perfetto, adesso madami una serie di numeri separati da spazio, ad ogni numero corrisponde la relativa percentuale" \
               " del tuo budget che vuoi spendere sullo scrigno. La posizione dei numeri è associata alla posizione degli scrigni per esempio:\n" \
               "se mandi '0 0 20 30 25 25' vuol dire:\n" \
               "0 Lengo [C], 0 Ferro [NC], 20% Prezioso [R], 30% Diamante [UR], 25% Leggendario [L] e 25% Epico [E].\nNota bene la somma dei numeri deve fare 100!\n" \
               "Mayo consiglia <code> 5 10 20 25 30 10 </code>\n" \
               "Osho consiglia <code> 4 8 20 25 33 10 </code>"
        update.message.reply_text(text, parse_mode="HTML")
        return 2

    def scrigni_func(self, bot, update, user_data):
        """Salva gli scrigni e calcola la quantità da comprare """
        param = update.message.text.split(" ")
        # check se l'user ha impostato correttamente gli scrigni
        if len(param) != 6:  # check sul numero dei parametri
            update.message.reply_text(
                "Non hai inserito il numero per tutti gli scrigni! Ne ho ricevuti " + str(len(param)) + "/6")
            return self.inizzializza(bot, update, user_data)
        numbers = []
        for num in param:  # check sul tipo dei parametri
            if not is_numeric(num):
                update.message.reply_text(str(num) + " non è un numero!")
                return self.inizzializza(bot, update, user_data)
            else:
                numbers.append(int(num))

        if sum(numbers) != 100:
            update.message.reply_text("La somma è errata " + str(sum(numbers)) + "/100")
            return self.inizzializza(bot, update, user_data)

        # usa dizionario ordinato per non perdere la relazione quantita scrignio-tipo
        scontato = OrderedDict()
        res = {}
        # salvo i valori scontati
        for elem in self.scrigni.keys():
            scontato[elem] = self.scrigni[elem] - (self.scrigni[elem] * float(user_data['sconto']))
            res[elem] = 0

        budget = user_data['budget']

        for perc, cost in zip(numbers, scontato.keys()):
            res[cost] = math.floor(budget * (perc / 100) / scontato[cost])

        text = ""
        # genera il messaggio da inviare e invia
        for elem in res.keys():

            if res[elem]: text += "Compra <b>" + str(res[elem]) + "</b> di Scrigno " + elem + "\n"

        if not text: text = "Non hai mai usato la funzione da inoltro!\nConsulta l'help sezione 'inoltro' e cerca 'Loot'"

        update.message.reply_text(text, parse_mode="HTML")
        # rinizzializza lo user_data
        return self.inizzializza(bot, update, user_data)


class EasterEggs:

    def __init__(self, updater):
        self.updater = updater
        self.photos = {'rip': "AgADBAAD8KsxG0LECFEjH-KrMEdbaS2KIBoABLOSJLrQ2GR6oV0AAgI"}
        self.prob = 0.1

        disp = updater.dispatcher

        disp.add_handler(MessageHandler(Filters.text, self.rip))

    @catch_exception
    def rip(self, bot, update):
        if "private" in update.message.chat.type: return
        if "rip" != update.message.text.lower(): return
        if not self.probability(): return
        bot.sendPhoto(update.message.chat.id, self.photos['rip'], reply_to_message_id=update.message.message_id)

    def probability(self):
        num = random.uniform(0, 1)
        return num < self.prob


class Contest:

    def __init__(self, updater, db):
        self.updater = updater
        self.db = db

        self.contest_flag = False
        self.contest_creator = False

        self.contest_regole = ""
        self.contest_ricompensa = ""
        self.contest_partecipanti = []
        self.contest_min_partecipanti = 2
        self.contest_max_partecipanti = 100
        self.contest_risposte = []

        disp = updater.dispatcher

        converstion = ConversationHandler(
            [CommandHandler("iniziacontest", self.init_contest)],
            states={
                1: [MessageHandler(Filters.text, self.regole_init)],
                2: [MessageHandler(Filters.text, self.ricompensa_init)],
                3: [MessageHandler(Filters.text, self.min_max_partecipanti)],
                4: [MessageHandler(Filters.text, self.conferma_contest)],

            }, fallbacks=[CommandHandler('Fine', self.init_params, pass_user_data=True)])

        disp.add_handler(converstion)
        disp.add_handler(CommandHandler("contest", self.visualizza_contest))
        disp.add_handler(CommandHandler("rispondicontest", self.visualizza_contest))
        disp.add_handler(CommandHandler("annullacontest", self.annulla_contest))
        disp.add_handler(CallbackQueryHandler(self.conferma_partecipazione, pattern="/contest_partecipa"))

    # ==================CONTEST CREATION =================================

    def init_contest(self, bot, update):

        # se c'è gia un contest informa
        if self.contest_flag:
            update.message.reply_text(
                "Un contest è gia in progresso!\nIl creatore è " + self.contest_creator['username'])
            return

        # salva il creatore e
        self.contest_flag = True
        self.contest_creator = update.message.from_user

        update.message.reply_text(
            "Perfetto " + self.contest_creator['username'] + ", ora inviami le regole del contest")
        return 1

    def regole_init(self, bot, update):

        # se il messaggio è vuoto chiedi di rinviarlo
        if not update.message.text:
            update.message.reply_text("Non hai inviato delle regole valide! Riprova")
            return 1
        # salva le regole
        self.contest_regole = update.message.text

        # chiedi la ricompensa
        update.message.reply_text("Regole salvate! Ora mandami le ricompense (deve essere minimo una)")
        return 2

    def ricompensa_init(self, bot, update):
        # se il messaggio è vuoto chiedi di rinviarlo
        if not update.message.text:
            update.message.reply_text("Non hai inviato una ricompensa valida! Riprova")
            return 2
        # salva le regole
        self.contest_ricompensa = update.message.text

        # chiedi la ricompensa
        to_send = """
Ricompensa salvata!
Un contest ha bisogno di partecipanti per essere divertente
Inviami il numero minimo e massimo di persone che possono partecipare, con due numeri separati da spazio (o uno solo se non vuoi specificare il massimo)
Il minimo deve essere compreso tra 2 e 10, mentre il massimo tra 20 e 100
Di default il minimo è 3 e non c'è massimo
Se non raggiungerai il minimo dei partecipanti entro le 24 ore dalla creazione del contest questo sarà automaticamente annullato
Quindi fai in modo di scegliere un numero adeguato
"""
        update.message.reply_text(to_send)

        # update.message.reply_text(self.get_contest(), parse_mode="HTML")
        return 3

    def min_max_partecipanti(self, bot, update):
        partecipanti = update.message.text
        min = 2
        max = 0

        # se l'utente ha specificato solo un minimo
        if len(partecipanti.split()) == 1:
            # controlla che sia un numero
            try:
                min = int(partecipanti)
            except ValueError:
                update.message.reply_text("Non hai inserito un numero corretto per il minimo")
                return self.init_params(bot, update)
        # se l'utente ha specificato due parametri
        elif len(partecipanti.split()) == 2:
            try:
                min = int(partecipanti.split()[0])
                max = int(partecipanti.split()[1])
            except ValueError:
                update.message.reply_text("Non hai inserito dei numeri corretti!")
                return self.init_params(bot, update)

        # se siamo arrivati qua l'utente ha inserito dei valori corretti
        # salvali
        self.contest_min_partecipanti = min
        if max: self.contest_max_partecipanti = max

        to_send = "Perfetto!Confermi il seguente contest?"
        update.message.reply_text(to_send)
        reply_markup = ReplyKeyboardMarkup([["Si", "No"]], one_time_keyboard=True)
        update.message.reply_text(self.get_contest(), reply_markup=reply_markup, parse_mode="HTML")
        return 4

    def conferma_contest(self, bot, update):
        choice = update.message.text

        if choice.lower() == "si":
            update.message.reply_text("Contest salvato!")
            self.insert_into_db()
            self.ask_partecipazione(bot)

        elif choice.lower() == "no":
            # todo: chiedi cosa vuole modificare
            update.message.reply_text("Contest annullato! Usa il comando per crearne un altro")
            self.init_params(bot, update)

        else:
            update.message.reply_text("Non ho capito...annullo")
            self.init_params(bot, update)

        return ConversationHandler.END

    def annulla_contest(self, bot, update):

        # se non ci sono contest
        if not self.contest_flag:
            update.message.reply_text("Non ci sono contest in corso al momento... creane uno con /iniziacontest")
            return

        if not update.message.from_user['id'] == self.contest_creator['id']:
            update.message.reply_text(
                self.contest_creator['username'] + " è il creatore del contest, chiedi a lui di annullarlo")
            return

        # todo: avverti i partecipanti
        self.sent_to_partecipanti(bot, "Il contest è stato annullato!")
        self.init_params(bot, update)
        self.db.delete_contest_creator()
        update.message.reply_text("Contest eliminato!")

    def ask_partecipazione(self, bot):

        # users=self.db.get_users()
        users = [24978334, 89675136]

        inline = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Si", callback_data="/contest_partecipa si"),
                InlineKeyboardButton("No️", callback_data="/contest_partecipa no")]])

        to_send = "Vuoi partecipare a questo contest?\n" + self.get_contest()

        for user in users:
            # if user['id']==self.contest_creator['id']:continue
            # bot.sendMessage(user['id'],to_send,parse_mode="HTML",reply_markup=inline)
            bot.sendMessage(user, to_send, parse_mode="HTML", reply_markup=inline)

    def conferma_partecipazione(self, bot, update):
        param = update.callback_query.data.split()[1]
        to_send = ""
        if param == "si":
            self.contest_partecipanti.append(update.callback_query.from_user)
            to_send = "Sei stato aggiunto al contest"
        else:
            to_send = "Non sei stato aggiunto al contest"

        bot.delete_message(
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id
        )

        bot.sendMessage(update.callback_query.from_user['id'], to_send)

    # ==================DB =================================

    def insert_into_db(self):
        self.db.insert_creator(self.contest_creator['id'], self.contest_creator['username'],
                               self.contest_regole, self.contest_ricompensa, self.contest_min_partecipanti,
                               self.contest_max_partecipanti)

    def get_creator_db(self, all=True, keys=[]):

        if all:
            res = self.db.get_key_contest_creator(["creator", "rules", "rewards", "min_max"])
            creator = {'id': res[0][0], 'username': res[0][1]}
            self.contest_creator = creator
            self.contest_regole = res[1]
            self.contest_ricompensa = res[2]
            self.contest_min_partecipanti = res[3][0]
            self.contest_max_partecipanti = res[3][1]

    # ==================UTILS =================================

    def init_params(self, bot, update):

        self.contest_flag = False
        self.contest_creator = False

        self.contest_regole = ""
        self.contest_ricompensa = ""
        self.contest_partecipanti = []
        self.contest_min_partecipanti = 2
        self.contest_max_partecipanti = 100
        self.contest_risposte = []

    def get_contest(self):

        # se non ci sono questi elementi non è possibile creare la stringa
        if not self.contest_regole or not self.contest_creator or not self.contest_ricompensa:
            return ""

        res = "<b>===Contest===</b>\n\n<b>Regole</b>\n"
        res += self.contest_regole
        res += "\n\n<b>Ricompensa</b>\n"
        res += self.contest_ricompensa
        res += "\n\nIl minimo numero di partecipanti è <b>" + str(self.contest_min_partecipanti) + \
               "</b> mentre il massimo è <b>" + str(self.contest_max_partecipanti) + "</b>\n"
        res += "\n\n<b>Creatore</b>\n@" + self.contest_creator['username']

        return res

    def is_contest(self, bot, update):
        contest = self.get_contest()
        if not contest:
            update.message.reply_text(
                "Non ci sono contest al momento :(\nPuoi crearne uno utilizzando il comando /iniziacontest")
            return

        update.message.reply_text(contest)

    # ==================FOR USERS =================================

    def visualizza_contest(self, bot, update):

        # se c'è un contest gia creato
        if self.contest_flag:
            update.message.reply_text(self.get_contest(), parse_mode="HTML")
        else:
            update.message.reply_text("Non ci sono contest al momento, creane uno con /iniziacontest")

    def sent_to_partecipanti(self, bot, to_send):

        for user in self.contest_partecipanti:
            bot.sendMessage(user['id'], to_send)

    def rispondi_contest(self, bot, update):
        # prendi tutto quello dopo il comando
        param = update.split()[1:]

        # controlla che ci sia un contesrt
        if not self.contest_flag:
            update.message.reply_text("Non ci sono contest in progresso al momento")
            return
            # controlla che la risposta sia valida
        if len(param) == 0:
            update.message.reply_text("Non è una risposta valida")
            return
        # controlla che l'user sia iscritto al contest
        if update.message.from_user.id not in [elem['id'] for elem in self.contest_partecipanti]:
            update.message.reply_text("Non sei iscritto a questo contest!")
            return

        # rimuovi la vecchia risposta se presente
        self.contest_risposte = [elem for elem in self.contest_risposte if elem[0]['id'] != update.message.from_user.id]

        # salva la risposta
        self.contest_risposte.append((update.message.from_user, param))
        update.message.reply_text("Risposta salvata!Puoi sempre modificarla usando lo stesso comando")


class Top:

    def __init__(self, updater, db):
        self.updater = updater
        self.db = db
        self.inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("Craft Totali", callback_data="/top pc_tot"),
             InlineKeyboardButton("Craft Settimanali", callback_data="/top pc_set")],
            [InlineKeyboardButton("EdoSoldi", callback_data="/top money"),
             InlineKeyboardButton("Abilità", callback_data="/top ability")],
            [InlineKeyboardButton("Rango", callback_data="/top rango"),
             InlineKeyboardButton("Esci", callback_data="/top esci")]

        ])  # inline per il messaggio

        disp = updater.dispatcher
        if DEBUG:
            disp.add_handler(RegexHandler("^Giocat", self.add_player))
            disp.add_handler(CommandHandler("top", self.top_command))
        else:
            add_player_decor = self.db.elegible_loot_user(self.add_player)
            top_command_decor = self.db.elegible_loot_user(self.top_command)
            disp.add_handler(RegexHandler("^Giocat", add_player_decor))
            disp.add_handler(CommandHandler("top", top_command_decor))

        disp.add_handler(CallbackQueryHandler(self.get_top, pattern="/top", pass_job_queue=True))

    @catch_exception
    def add_player(self, bot, update):
        """Aggiunge user nel db e visualizza top player"""

        # controlla che il messaggio sia mandato in privato
        if "private" not in update.message.chat.type:
            return
        # getting demojized message
        msg = update.message.text
        msg = emoji.demojize(msg)

        # compaling regex
        pc_regex = re.compile(r":package: ([0-9.]+) \(([0-9.]+)")
        money_regex = re.compile(r":money_bag: ([0-9.]+)")
        abilita_regex = re.compile(r"Abilità: ([0-9]+)")
        rango_regex = re.compile(r"Rango: [A-z ]+ \(([0-9]+)")

        # getting values
        pc_tot = re.findall(pc_regex, msg)[0][0].replace(".", "")
        pc_set = re.findall(pc_regex, msg)[0][1].replace(".", "")
        money = re.findall(money_regex, msg)[0].replace(".", "")
        ability = re.findall(abilita_regex, msg)[0].replace(".", "")
        rango = re.findall(rango_regex, msg)[0].replace(".", "")

        # updating to db
        err = self.db.add_update_top_user(pc_tot, pc_set, money, ability, rango, update.message.from_user.id)
        to_send = ""
        if not err:

            to_send = "In base a cosa desideri visualizzare la classifica?"
            update.message.reply_text(to_send, reply_markup=self.inline)
        else:
            to_send = "Si è verificato un errore, contatta @brandimax e inoltragli il messaggio che hai inviato"
            update.message.reply_text(to_send)

    @catch_exception
    def top_command(self, bot, update):

        to_send = "In base a cosa desideri visualizzare la classifica?"
        update.message.reply_text(to_send, reply_markup=self.inline)

    def get_top(self, bot, update, job_queue):
        """Visualizza informazioni per il top player"""
        # getting list of players and sort_key
        top_ps = self.db.get_all_top()
        sort_key = update.callback_query.data.split()[1]

        # se l'user vuole uscire elimina il messaggio di scelta
        if sort_key == "esci":
            bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=update.callback_query.message.message_id
            )
            return

        # sono sfaticato
        prov_dict = {
            "pc_tot": "📦Punti Craft Totali📦",
            "pc_set": "📁Punti Craft Settimanali📁",
            "money": "💰EdoSoldi💰",
            "ability": "🎗Abilità🎗",
            "rango": "🛡Rango🛡"
        }

        # casting top to list if is dict
        if not isinstance(top_ps, list): top_ps = [top_ps]

        # sorting
        sorted_top = sorted(top_ps, key=lambda k: k[sort_key], reverse=True)
        to_send = "Classifica per <b>" + prov_dict[sort_key] + "</b>\n"
        idx = 1
        for pl in sorted_top:
            to_send += self.pretty_user(pl, idx, sort_key)
            idx += 1

        # modifica messaggio
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_send,
            message_id=update.callback_query.message.message_id,
            reply_markup=self.inline,
            parse_mode="HTML"

        )
        # starta un timer per eliminare il messaggio dopo un ora
        job_queue.run_once(self.delete_message, timedelta(hours=1),
                           context={'chat_id': update.callback_query.message.chat_id,
                                    'message_id': update.callback_query.message.message_id})

    def delete_message(self, bot, job):
        try:
            bot.delete_message(
                chat_id=job.context['chat_id'],
                message_id=job.context['message_id']
            )
        finally:
            return

    def pretty_user(self, user, idx, sort_key):
        """Formatta messaggio di user da inviare
        @:param user: dizionario dello user
        @:type: dict
        @:param idx: indice per la classifica
        @:type: int
        @:param sort_key: chiave secondo cui avviene il sort
        @:type: str
        @:return res: stringa dello user formattata
        """
        res = ""

        if idx == 1:
            res += "🥇 "
        elif idx == 2:
            res += "🥈 "
        elif idx == 3:
            res += "🥉 "
        else:
            res += str(idx) + ") "

        # heroku manda l'ora corrente indietro di uno, aggiungi un ora
        future_hour = user['agg'] + timedelta(hours=1)

        # crea messaggio formattato
        res += "<b>" + user['username'] + "</b> con <b>" + "{:,}".format(user[sort_key]).replace(",",
                                                                                                 ".") + "</b> (<i>" + \
               str(future_hour.time()).split(".")[0] + " del " + str(
            future_hour.date().strftime('%d-%m-%Y')) + "</i>)\n"

        return res


class PietreDrago:

    def __init__(self, updater, db):
        self.updater = updater
        self.db = db

        disp = updater.dispatcher

        if DEBUG:
            disp.add_handler(RegexHandler("^.* possiedi \(D\):", self.calc_val))
        else:
            calc_val_el = self.db.elegible_loot_user(self.calc_val)
            disp.add_handler(RegexHandler("^.* possiedi \(D\):", calc_val_el))

    def calc_val(self, bot, update):

        msg = update.message.text
        # compila il pattern
        regex_legno = re.compile(r"Pietra Anima di Legno \(([0-9]+\.?[0-9]*)")
        regex_ferro = re.compile(r"Pietra Anima di Ferro \(([0-9]+\.?[0-9]*)")
        regex_preziosa = re.compile(r"Pietra Anima Preziosa \(([0-9]+\.?[0-9]*)")
        regex_diamante = re.compile(r"Pietra Cuore di Diamante \(([0-9]+\.?[0-9]*)")
        regex_leggendario = re.compile(r"Pietra Cuore Leggendario \(([0-9]+\.?[0-9]*)")
        regex_epico = re.compile(r"Pietra Spirito Epico \(([0-9]+\.?[0-9]*)")

        # cerca dentro il messaggio
        legno = re.findall(regex_legno, msg)
        ferro = re.findall(regex_ferro, msg)
        preziosa = re.findall(regex_preziosa, msg)
        diamante = re.findall(regex_diamante, msg)
        leggendario = re.findall(regex_leggendario, msg)
        epico = re.findall(regex_epico, msg)

        # se è presente casta a int e moltiplica, altrimenti setta a zero
        if len(legno) > 0:
            legno = int(legno[0].replace('.', ''))
        else:
            legno = 0

        if len(ferro) > 0:
            ferro = int(ferro[0].replace('.', '')) * 2
        else:
            ferro = 0

        if len(preziosa) > 0:
            preziosa = int(preziosa[0].replace('.', '')) * 3
        else:
            preziosa = 0

        if len(diamante) > 0:
            diamante = int(diamante[0].replace('.', '')) * 4
        else:
            diamante = 0

        if len(leggendario) > 0:
            leggendario = int(leggendario[0].replace('.', '')) * 5
        else:
            leggendario = 0

        if len(epico) > 0:
            epico = int(epico[0].replace('.', '')) * 6
        else:
            epico = 0

        # calcola il totale
        tot = legno + ferro + preziosa + diamante + leggendario + epico

        # setta il messaggio da inviare
        to_send = "Valore delle Pietre 🐲:\n"
        if legno: to_send += "Pietra Anima di Legno 🌴 : <b>" + str(legno) + "</b>\n"
        if ferro: to_send += "Pietra Anima di Ferro ⚙️ : <b>" + str(ferro) + "</b>\n"
        if preziosa: to_send += "Pietra Anima Preziosa ✨ : <b>" + str(preziosa) + "</b>\n"
        if diamante: to_send += "Pietra Cuore di Diamante 💎 : <b>" + str(diamante) + "</b>\n"
        if leggendario: to_send += "Pietra Cuore Leggendario 💥 : <b>" + str(leggendario) + "</b>\n"
        if epico: to_send += "Pietra Spirito Epico 🌪 : <b>" + str(epico) + "</b>\n"
        to_send += "Totale : <b>" + str(tot) + "</b>\n"
        lv = tot / 70
        if lv < 1:
            to_send += "Puoi arrivare al <b>" + "{0:.2f}".format(lv * 100) + "%</b> di un livello"
        elif lv < 2:
            to_send += "Puoi far salire il drago di <b>" + str(
                math.floor(lv)) + "</b> livello e <b>" + "{0:.2f}".format(lv % 1 * 100) + "%</b>"
        else:
            to_send += "Puoi far salire il drago di <b>" + str(
                math.floor(lv)) + "</b> livelli e <b>" + "{0:.2f}".format(lv % 1 * 100) + "%</b>"

        update.message.reply_text(to_send, parse_mode="HTML")


class Help:

    def __init__(self, updater, db):
        self.updater = updater
        self.db = db
        self.inline_cat = InlineKeyboardMarkup([
            [InlineKeyboardButton("Admin", callback_data="/help admin"),
             InlineKeyboardButton("User", callback_data="/help user"),
             InlineKeyboardButton("Developer", callback_data="/help developer")],
            [InlineKeyboardButton("Inoltro", callback_data="/help inoltro"),
             InlineKeyboardButton("Crediti", callback_data="/help crediti"),
             InlineKeyboardButton("Esci", callback_data="/help esci")]

        ])
        self.inline_page = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⬅️", callback_data="/help page_indietro"),
                InlineKeyboardButton("➡️", callback_data="/help page_avanti")],
            [InlineKeyboardButton("Torna al help", callback_data="/help page_esci")]

        ])

        disp = updater.dispatcher
        if DEBUG:
            disp.add_handler(CommandHandler("help", self.help_init))
        if not DEBUG:
            help_init_elegible = self.db.elegible_loot_user(self.help_init)
            disp.add_handler(CommandHandler("help", help_init_elegible))

        disp.add_handler(CallbackQueryHandler(self.help_decision, pattern="/help", pass_user_data=True))

    def get_commands_help(self):
        """Prende le funzioni e relative doc dei metodi di Command
        @:return user, admin, developer: liste contenenti nome funzioni e doc"""
        funcs = inspect.getmembers(Command, predicate=inspect.isfunction)
        admin = []
        user = []
        developer = []

        # appende in tutte le liste nomeFunzione - doc
        for elem in funcs:
            if elem[0][0] == "A" and elem[1]:
                admin.append("/" + elem[0][1:] + "  " + elem[1].__doc__ + "\n")
            elif elem[0][0] == "U" and elem[1]:
                user.append("/" + elem[0][1:] + "  " + elem[1].__doc__ + "\n")

            elif elem[0][0] == "D" and elem[1]:
                developer.append("/" + elem[0][1:] + "  " + elem[1].__doc__ + "\n")

        # appende i comandi non prenseti in Command
        admin.append(
            "/resetboss - resetta i punteggi associati agli attacchi Boss di tutti, da usare con cautela poichè una volta cancellati, "
            "i punteggi non sono piu recuperabili")

        user.append("/attacchiBoss - Ti permette di visualizzare i punteggi di tutti i membri del team")
        user.append("/cercaCraft num1 num2 - Ti permette di cercare oggetti in base ai punti craft, rarità e "
                    "rinascita. Dato num1>num2 cerca oggetti craft con valore compreso tra num1 e num2 ")
        user.append("/compra - Ti permette di calcolare facilmente quanti scrigni comprare in base a sconti dell'"
                    "emporio e il tuo budget")
        user.append("/top - Ti permette di visualizzare la classifica dei top player in base a [pc totali, pc "
                    "settimanali, edosoldi, abilità, rango]")
        user.append("/teams - Visualizza i pc dei team presenti nella Hall of Fame e il relativo incremento")
        user.append(
            "/mancanti - Mostra tutti gli oggetti nel tuo zaino (non craftabili) che hanno una quantità inferiore a quella specificata")
        user.append("/diffschede - Visualizza la differenza in pc tra due schede 'Dettaglio Membri' in 'Team'")
        user.append(
            "/timerset hh:mm msg - setta un timer tra <b>hh</b> ore e <b>mm</b> minuti (si possono anche specificare solo le ore) e allo scadere del tempo invia il messaggio <b>msg</b>")
        user.append("/timerunset - Rimuove il timer precedentemente settato")
        user.append("/activity - Mostra varie informazioni del gruppo Fancazzisti")
        user.append(
            "/punteggioact - Visualizza il tuo punteggio, con punteggio maggiore sblocchi diverse funzionalità di activity")
        user.append("/classify - Permette di classificare i vari messaggi")
        user.append("/topunteggio - visualizza i punteggi della classifica di activity")
        user.append("/negozi - genera dei negozi a prezzo base a seconda del vostro zaino")

        return user, admin, developer

    def get_forward_commands(self):
        return """
<b>=====COMANDI DA INOLTRO=====</b>\n
I comandi da inoltro sono molteplici, verranno suddivisi in base al tipo di messaggio inoltrato.

<b>----Loot----</b>
Questo comando viene attivato quando inoltri il messaggio <b>/lista oggetto</b> da @craftlootbot.
Una volta inoltrato ti sarà chiesta quale informazione vuoi visualizzare tra le seguenti:
<b>Negozi</b>
Ti permette di ottenere una comoda stringa di negozi degli oggetti mancanti da poter inoltrare a @lootbotplus
<b>Ricerca</b>
Quando clicchi ricerca verranno automaticamente salvate le rarità che ti mancano per poter utilizzare il comando /compra
Questo comando prevede piu passi:
1) Una volta premuto il bottone ti saranno inviati dei messaggi "/ricerca oggetto1, oggetto2, oggetto3" per ogni oggetto che ti manca
2) Inoltra questi messaggi a @lootplusbot
3) Ri-inoltra i messaggi li @lootplusbot (quelli con i prezzi e i negozi) a @fancabot
4) Clicca stima per ottenere il costo tolate (comprendente acquisto degli oggetti e craft stesso), il tempo stimato per comprare gli oggetti, la top 10 degli oggetti piu costosi (solo se sono presenti 10 elementi o più)
5) Ti verrà chiesto se vuoi visualizzare i negozi, clicca <i>"Si"</i> per ottenere una lista di comandi <pre>@lootplusbot codiceNegozio</pre>, altrimenti <i>"No"</i> per annullare


<b>----Boss----</b>
Comando solo per <b>ADMIN</b>, per l'opzione user visualizzare il help del comando /attacchiboss
Questo comando viene attivato quando inoltri il messaggio <b>Team</b> di @lootgamebot
Potrete scegliere tra tre opzioni:
1) <i>Titan</i> : +1 punto per chi non ha attaccato
2) <i>Phoenix</i> : +2 punti per chi non ha attaccato
2) <i>Visualizza</i> : Permette di vedere le info senza salvare il punteggio
3) <i>Annulla</i> : se vi siete sbagliati
Scelto il tipo di boss verranno salvati i punti dei membri non attaccanti, ovviamente chi ha piu punti si trova in pericolo di kick dal team
<b>NB</b>: Se qualcuno dei membri NON ha inviato il comando /start al bot non saranno salvati i punti del suddetto, ma verrai notificato.
Successivamente potrete scegliere 4 opzioni:
1) <i>Completa</i> : Visualizza gli utenti divisi in due categorie, attaccanti (con danno, punteggio e attacchi), non attaccanti (con punteggio e occupazione corrente (cava, missione))
2) <i>Non Attaccanti</i> : Riceverai un messaggio con gli username di quelli che non hanno attaccato
3) <i>Punteggio</i> : Una lista ordinata di username con relativi punteggi
4) <i>Sveglia</i> : Manda un messaggio per incoraggare chi non ha attaccato a farlo
5) <i>Visualizza</i> : Permentte di vedere le informazioni senza salvare il punteggio
6) <i>Annulla</i> : Per completare la fase di visualizzazione
Per resettare i punteggi usa /resetboss, però fai attenzione poichè l'operazione non è reversibile

<b>----Top----</b>
Questo comando viene attivato inoltrando il messaggio <b>Giocatore</b> da @lootgamebot
Inviando il messaggio ggiornerai il database e potrai visualizzare la tuo posizione in classifica con gli altri membri.
La classifica mostra la data di aggiornamento e i punti realtivi a:
1) Punti craft totali
2) Punti craft settimanali
3) Edosoldi
4) Abilità
5) Rango 
La visualizzazione è anche disponibile tramite il comando /top, senza aggiornamento dei valori

<b>----Pietre del Drago----</b>
Questo comando viene attivato inoltrando il messagio <b>/zaino D</b> da @lootplusbot
Otterrai il valore (in exp drago) di tutte le pietre del drago che sono presenti nel tuo zaino nei seguenti formati:
1) Punti individuali per ogni pietra
2) Punti totali
3) Avanzamento in termini di livello del drago se decidi di nutrirlo con tutte le pietre

<b>----Teams----</b>
Questo comando viene attivato inoltrando il messaggio <b>Team->Hall of Fame</b> da @lootgamebot
Una volta inoltrato il messaggio ti verranno offerte varie scelte di visualizzazione:
1)<b>--Incremento--</b>
(<b>NB</b>: 'Inc' è un acronimo di incremento e fa riferimento alla variazione di pc):
1.1) <i>Inc Orario</i> : Mostra l'incremento orario medio di tutti i team presenti 
1.2) <i>Inc Giornaliero</i> : Mostra l'incremento giornaliero medio di tutti i team presenti 
1.3) <i>Inc Settimanale</i> : Mostra l'incremento settimanale medio di tutti i team presenti 
1.4) <i>Inc Mensile</i> : Mostra l'incremento mensile medio di tutti i team presenti 
1.5) <i>Inc Ultimo Aggiornamento </i> : Mostra l'incremento dall'ultimo aggiornamento 
1.6) <i>Inc Totale </i> : Mostra l'incremento totale dal primo messaggio ricevuto 
1.7) <i>Inc Totale Medio </i> : Mostra l'incremento totale medio dal primo messaggio ricevuto

2) <b>--Grafico--</b>
Invia una foto (in formato png) dell'andamento di tutti i team in termini ti pc totali. I pallini rappresentano un messaggio di inoltro ricevuto,  mentre le line compongono la curva di andamento

3) <b>--Stime--</b>
Le Stime rappresentano la classifica stimata in base all'unità di tempo, ovvero a quanti pc saranno arrivati i teams tra ore, giorni, settimane, mesi...
2.1) <i>Stima Orarie</i> : Mostra i pc stimati tra un ora 
2.2) <i>Stima Giornaliere</i> : Mostra i pc stimati tra un giorno 
2.3) <i>Stima Settimanali</i> : Mostra i pc stimati tra una settimana
2.4) <i>Stima Mensili</i> : Mostra i pc stimati tra un mese

4) <b>--Scalata--</b>
La scalata ti fornisce una sclassifica con i pc necessari per superare i team in testa a Fancazzisti. 
Come per gli altri comandi anche queste si dividono a seconda dell'unità di tempo, la sintassi è:
NomeTeam : pcNecessariPerSuperarlo (pcNecessariIndividuali)
4.1) <i>Scalata Oraria</i> : Mostra i pc necessari per superare il team in un ora
4.2) <i>Scalata Giornaliera</i> : Mostra i pc necessari per superare il team in un giorno
4.3) <i>Scalata Settimanale</i> : Mostra i pc necessari per superare il team in una settimana
4.4) <i>Scalata Mensile</i> : Mostra i pc necessari per superare il team in un mese

5) <b>--Classifica--</b>
Visualizza la classica calssifica della Hall of Fame

6) <b>--Esci--</b> 
Termina la visualizzazione

Per ora sarà possibile accedere a queste informaizoni solo tramite inoltro del messaggio <i>Hall of Fame</i>, poiche ad ogni ricezione vengono aggiungere dati su cui poter effettuare le stime.
Quando avremo raggiunto una sufficente quantita di dati salterà fuori un comando che non necesita di inoltro.
C'è anche da dire che alcune informazioni non sono ancora disponibili (Mensile e Giornaliero) per via della recente nascita del comando... tra un mese avremo a disposizione tutto
Prossimamente aggiungerò anche qualche tecnica di Inteligenza Artificiale al bot per fergli prevedere come sarà la classifica tra un tot di tempo (ore, giorni, settimane...), prorpio per questo vi invito a inoltrare piu messaggi possibili!

<b>----Crafter----</b>
Questo comando viene attivato inoltrando il messaggio <b>/craft->Messaggio</b> da @craftlootbot
Ti verranno inviati una serie di messaggi del tipo:
Crea oggetto1
si
Crea oggetto2
si
....
Da inoltrare a @lootgamebot per craftare velocemente (efficace specialmente con plus)

"""

    def get_credits(self):
        return """<b>=====CREDITI=====</b>\n
Crediti: @brandimax e @Odococo e un ringraziamento speciale a @DiabolicamenteMe per avermi aiutato ❤️.
Se hai idee o suggerimenti scrivici e non tarderemo a risponderti!
Votaci sullo <a href="https://telegram.me/storebot?start=fancazzisti_bot">Storebot</a>!
"""

    def help_init(self, bot, update):
        to_send = """Benvenuto nel FancaBot! Questo bot ha diverse funzionalità per semplificare il gioco @lootgamebot
Seleziona una categoria di comandi per imapararne l'utilizzo. Ricorda che ogni comando ha la seguente sintassi:
nomeComando parametri - spiegazione
Quindi ricorda di aggiungere i parametri giusti!"""
        update.message.reply_text(to_send, reply_markup=self.inline_cat)

    def help_decision(self, bot, update, user_data):
        """Visulauzza i vari help a seconda della scelta dell'user, supporta la creazione automati di piu pagine
        in caso di stringhe troppo lunghe"""
        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        if 'page' not in user_data.keys():
            print("page not found!")
            user_data['page'] = 0

        if 'pages' not in user_data.keys(): user_data['pages'] = []

        user, admin, developer = self.get_commands_help()

        to_send = ""

        if param == "page_avanti":
            user_data['page'] += 1
            to_send = user_data['pages'][user_data['page'] - 1]

        elif param == "page_indietro":
            user_data['page'] -= 1
            to_send = user_data['pages'][user_data['page'] - 1]

        elif param == "page_esci":
            user_data['page'] = 0
            to_send = """Benvenuto nel FancaBot! Questo bot ha diverse funzionalità per semplificare il gioco @lootgamebot
Seleziona una categoria di comandi per imapararne l'utilizzo. Ricorda che ogni comando ha la seguente sintassi:
nomeComando parametri - spiegazione
Quindi ricorda di aggiungere i parametri giusti!"""
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=to_send,
                message_id=update.callback_query.message.message_id,
                reply_markup=self.inline_cat,
                parse_mode="HTML"

            )
            return

        if param == "esci":
            # elimina messaggio di scelta
            bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=update.callback_query.message.message_id
            )
            bot.sendMessage(update.callback_query.message.chat.id, "Spero di esserti stato utile!")
            return
        elif param == "admin":

            to_send += "<b>=====COMANDI ADMIN=====</b>\n\n"
            # scrive tutti i comandi
            for elem in admin:
                to_send += elem + "\n\n"
            # dividi il messaggio a seconda della lunghezza in bytes
            to_send = text_splitter_bytes(to_send, splitter="\n\n")
            # se ci sono piu elementi manda solo il pirmo, vedi todo
            if len(to_send) > 1:
                user_data['pages'] = to_send

                if user_data['page'] == 0:
                    user_data['page'] = 1
                    to_send = to_send[0]
            # altrimenti usa il primo elemento
            else:
                to_send = to_send[0]


        elif param == "user":
            to_send += "<b>=====COMANDI USER=====</b>\n\n"

            for elem in user:
                to_send += elem + "\n\n"
            # dividi il messaggio a seconda della lunghezza in bytes
            to_send = text_splitter_bytes(to_send, splitter="\n\n")
            # se ci sono piu elementi manda solo il pirmo, vedi todo
            if len(to_send) > 1:
                user_data['pages'] = to_send

                if user_data['page'] == 0:
                    user_data['page'] = 1
                    to_send = to_send[0]
            # altrimenti usa il primo elemento
            else:
                to_send = to_send[0]


        elif param == "developer":
            to_send += "<b>=====COMANDI DEVELOPER=====</b>\n\n"

            for elem in developer:
                to_send += elem + "\n\n"
            # dividi il messaggio a seconda della lunghezza in bytes
            to_send = text_splitter_bytes(to_send, splitter="\n\n")
            # se ci sono piu elementi manda solo il pirmo, vedi todo
            if len(to_send) > 1:
                user_data['pages'] = to_send

                if user_data['page'] == 0:
                    user_data['page'] = 1
                    to_send = to_send[0]
            # altrimenti usa il primo elemento
            else:
                to_send = to_send[0]

        elif param == "inoltro":
            to_send += self.get_forward_commands()
            # print(to_send)
            # dividi il messaggio a seconda della lunghezza in bytes
            to_send = text_splitter_bytes(to_send, splitter="\n\n")
            # se ci sono piu elementi manda solo il pirmo, vedi todo
            if len(to_send) > 1:
                user_data['pages'] = to_send

                if user_data['page'] == 0:
                    user_data['page'] = 1
                    to_send = to_send[0]

            # altrimenti usa il primo elemento
            else:
                to_send = to_send[0]


        elif param == "crediti":
            to_send += self.get_credits()

        if user_data['page'] == 0:
            # modifica il messaggio con il to_send
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=to_send,
                message_id=update.callback_query.message.message_id,
                reply_markup=self.inline_cat,
                parse_mode="HTML"

            )
        else:
            # ultima pagina
            if user_data['page'] == len(user_data['pages']):
                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️", callback_data="/help page_indietro")],
                        [InlineKeyboardButton("Torna al help", callback_data="/help page_esci")]]),
                    parse_mode="HTML"

                )
            # prima pagina
            elif user_data['page'] == 1:
                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("➡️", callback_data="/help page_avanti")],
                        [InlineKeyboardButton("Torna al help", callback_data="/help page_esci")]

                    ]),
                    parse_mode="HTML"

                )
            # pagine in mezzo
            else:
                bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    text=to_send,
                    message_id=update.callback_query.message.message_id,
                    reply_markup=self.inline_page,
                    parse_mode="HTML"

                )


class Team:
    def __init__(self, updater, db):
        self.updater = updater
        self.db = db
        self.data_dict = {}
        self.last_update = None
        self.youngest_update = None
        self.inline_team = InlineKeyboardMarkup([
            [InlineKeyboardButton("Incrementi", callback_data="/team_main incrementi"),
             InlineKeyboardButton("Grafico", callback_data="/team_main grafico"),
             InlineKeyboardButton("Classifica", callback_data="/team_main classifica")],
            [InlineKeyboardButton("Stime", callback_data="/team_main stime"),
             InlineKeyboardButton("Scalata", callback_data="/team_main scalata"),
             InlineKeyboardButton("Esci", callback_data="/team_main esci")]

        ])

        self.inline_stime = InlineKeyboardMarkup([
            [InlineKeyboardButton("Stime orarie", callback_data="/team_stima orario"),
             InlineKeyboardButton("Stime giornaliere", callback_data="/team_stima giornaliero")],
            [InlineKeyboardButton("Stime settimanali", callback_data="/team_stima settimanale"),
             InlineKeyboardButton("Stime mensili", callback_data="/team_stima mensile")],
            [InlineKeyboardButton("Indietro", callback_data="/team_stima indietro")]

        ])

        self.inline_scalata = InlineKeyboardMarkup([
            [InlineKeyboardButton("Scalata oraria", callback_data="/team_scala orario"),
             InlineKeyboardButton("Scalata giornaliera", callback_data="/team_scala giornaliero")],
            [InlineKeyboardButton("Scalata settimanale", callback_data="/team_scala settimanale"),
             InlineKeyboardButton("Scalata mensile", callback_data="/team_scala mensile")],
            [InlineKeyboardButton("Giorni rimanenti", callback_data="/team_scala rimanenti"),
             InlineKeyboardButton("Indietro", callback_data="/team_scala indietro")]

        ])

        self.inline_inc = InlineKeyboardMarkup([
            [InlineKeyboardButton("Inc Orario", callback_data="/team_inc orario"),
             InlineKeyboardButton("Inc Giornaliero", callback_data="/team_inc giornaliero"),
             InlineKeyboardButton("Inc Settimanale", callback_data="/team_inc settimanale"),
             InlineKeyboardButton("Inc Mensile", callback_data="/team_inc mensile")],
            [InlineKeyboardButton("Inc ultimo aggiornamento", callback_data="/team_inc update"),
             InlineKeyboardButton("Inc totale", callback_data="/team_inc totale"),
             InlineKeyboardButton("Inc totale medio", callback_data="/team_inc totale_medio"),
             InlineKeyboardButton("Indietro", callback_data="/team_inc indietro")]

        ])

        self.team_init_msg = """
Ci sono varie categorie di informazioni che puoi visualizzare:
<b>Incrementi</b> : mostra di quanto aumentano i pc dei team in base a vari parametri temporali (ore, giorni settimane, mesi), alcuni di questi potrebbero essere vuoti per mancanza di dati, ma non disperare, con il tempo saranno disponibili
<b>Grafico</b> : mostra l'andamento dei pc totali dei team nel tempo
<b>Stime</b> : stima i pc totali che un team avrà tra una certa unità di tempo (ore, giorni, settimane, mesi)
<b>Scalata</b> : visualizza i pc che servono al team Fancazzisti per superare quelli in testa
<b>Classifica</b> : mostra la stessa classifica della Hall of Fame
<b>Esci</b> : per uscira dalla visualizzazione
Quindi quali informazioni vuoi?"""

        self.scalata_init_msg = """
<b>Scalata</b> : Qui puoi visualizzare i pc che servono al team Fancazzisti (in un'unità di tempo) per superare gli altri teams in classifica\n
La sintassi è questa: 
NomeTeamDaSuperare : pcTotali (pcIndividuali)
Quindi verranno visualizzati i teams con piu pc e ti sarà detto quanti ne servono al tuo team (in un ora, giorno, settimana, mese) complessivi e a testa
Inoltre è presente la voce <b>Giorni rimanenti</b> che specifica il numero di giorni rimanenti per raggiungere un determinato team"""

        self.inc_init_msg = """
<b>Incrementi</b>
'Inc' sta per incremento e si riferisce alla differenza di pc tra un messaggio e l'altro, ovvero di quanto aumentano i pc.
        """

        disp = updater.dispatcher

        if DEBUG:
            disp.add_handler(RegexHandler("^Classifica Team:", self.forward_team))
        else:
            forward_team_decor = self.db.elegible_loot_user(self.forward_team)
            disp.add_handler(RegexHandler("^Classifica Team:", forward_team_decor))

        disp.add_handler(CallbackQueryHandler(self.decision_team, pattern="/team_main"))
        disp.add_handler(CallbackQueryHandler(self.decision_inc, pattern="/team_inc"))
        disp.add_handler(CallbackQueryHandler(self.decision_stime, pattern="/team_stima"))
        disp.add_handler(CallbackQueryHandler(self.decision_scalata, pattern="/team_scala"))

    # ================Start and Decision==================
    def forward_team(self, bot, update):
        """Quando riceve un messaggio team, invia imessaggio con incremento di pc e aggiorna il db"""
        # controlla che il messaggio sia mandato in privato
        if "private" not in update.message.chat.type:
            return
        # prendi i team nel messaggio e nel db

        team_db = self.get_teams_db()
        team_msg = self.extract_teams_from_msg(update.message.text)
        # controlla se sono presenti team nel databes
        if not team_db:
            self.update_db(team_msg, 0)
            update.message.reply_text("Database aggiornato!")
            return

        # print(self.last_update)

        # unisci i dati nel db con quelli nel messaggio
        complete_team = team_db
        # uso un counter per vedere quanti elementi ho nella lista (per ogni team)
        count = Counter(elem[0] for elem in complete_team)
        # print(count)
        key = random.choice(list(count.keys()))
        # setto l'idx (usato per salvare numero)
        idx = count[key]

        # aggiungo l'ultimo update alla lista nel db
        for elem in team_msg:
            complete_team.append((elem[0], elem[1], idx, elem[2]))

        # print(complete_team)
        # salva il dizionario corrente
        self.data_dict = self.list2dict(complete_team)
        # print(self.data_dict)

        # esegue l'update del db
        self.update_db(team_msg, idx)

        update.message.reply_text(self.team_init_msg, reply_markup=self.inline_team, parse_mode="HTML")

    def decision_team(self, bot, update):
        """Serve per smistare le info a seconda della scelta dell'user"""

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        if param == "incrementi":
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.inc_init_msg,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_inc
            )
            return

        elif param == "stime":
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text="<b>Stime</b>\nStima i pc totali di un team in un lasso di tempo.",
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_stime
            )
            return

        elif param == "classifica":

            to_send = self.get_total_pc(self.data_dict)
            to_send = self.pretty_increment(to_send)
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=to_send,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_team
            )
            return

        elif param == "scalata":

            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.scalata_init_msg,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_scalata
            )
            return


        elif param == "grafico":
            msg = update.callback_query.message.reply_text("Attendi un secondo...")

            # crea immagine e inviala
            path2img = self.plot(self.data_dict)
            with open(path2img, "rb") as file:
                bot.sendPhoto(update.callback_query.message.chat_id, file)
            # rimuovi immagine
            os.remove(path2img)
            # rimuovi messaggio
            bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=update.callback_query.message.message_id
            )
            bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=msg.message_id
            )
            msg = update.callback_query.message.reply_text("Immagine inviata!")

            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text="Immagine inviata!",
                message_id=msg.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_team
            )
            return

        elif param == "esci":
            update.callback_query.message.reply_text("Ok")
            bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=update.callback_query.message.message_id
            )
            return

    def decision_stime(self, bot, update):
        """Serve per smistare le info a seconda della scelta dell'user"""

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        to_send = "Spiacente non ci sono abbastanza dati per questo...riprova piu tardi"

        if param == "orario":
            res_dict = self.get_stima(self.data_dict, 0)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Stima oraria</b>:\n")

        elif param == "giornaliero":
            res_dict = self.get_stima(self.data_dict, 1)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Stima giornaliera</b>:\n")

        elif param == "settimanale":
            res_dict = self.get_stima(self.data_dict, 2)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Stima settimanale</b>:\n")

        elif param == "mensile":
            res_dict = self.get_stima(self.data_dict, 3)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Stima mensile</b>:\n")


        elif param == "indietro":

            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.team_init_msg,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_team
            )
            return

        # modifica il messaggio in base ai parametri scelti dall'utente
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_send,
            message_id=update.callback_query.message.message_id,
            parse_mode="HTML",
            reply_markup=self.inline_stime
        )

    def decision_inc(self, bot, update):
        """Serve per smistare le info a seconda della scelta dell'user"""

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        to_send = "Spiacente non ci sono abbastanza dati per questo...riprova piu tardi"

        if param == "orario":
            res_dict = self.get_temporal_increment(self.data_dict, 0)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Incremento orario medio</b>:\n")

        elif param == "giornaliero":
            res_dict = self.get_temporal_increment(self.data_dict, 1)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Incremento giornaliero medio</b>:\n")

        elif param == "settimanale":
            res_dict = self.get_temporal_increment(self.data_dict, 2)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Incremento settimanale medio</b>:\n")

        elif param == "mensile":
            res_dict = self.get_temporal_increment(self.data_dict, 3)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Incremento mensile medio</b>:\n")

        elif param == "totale":
            res_dict = self.get_total_increment(self.data_dict, False)
            if res_dict:
                ora, data = pretty_time_date(self.youngest_update)
                to_send = self.pretty_increment(res_dict,
                                                "<b>Incremento totale</b> (dal <i>" + data + " alle " + ora + "</i>):\n")

        elif param == "totale_medio":
            res_dict = self.get_total_increment(self.data_dict, True)
            if res_dict:
                ora, data = pretty_time_date(self.youngest_update)
                to_send = self.pretty_increment(res_dict,
                                                "<b>Incremento totale medio</b> (dal <i>" + data + " alle " + ora + "</i>):\n")

        elif param == "update":
            res_dict = self.get_last_update_increment(self.data_dict)
            if res_dict:
                ora, data = pretty_time_date(self.last_update)
                to_send = self.pretty_increment(res_dict,
                                                "<b>Incremento dall'ultimo aggiornamento</b> (Il " + data + " alle " + ora + "):\n")


        elif param == "indietro":

            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.team_init_msg,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_team
            )
            return

        # modifica il messaggio in base ai parametri scelti dall'utente
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_send,
            message_id=update.callback_query.message.message_id,
            parse_mode="HTML",
            reply_markup=self.inline_inc
        )

    def decision_scalata(self, bot, update):
        """Serve per smistare le info a seconda della scelta dell'user"""

        # prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        to_send = "Spiacente non ci sono abbastanza dati per questo...riprova piu tardi"

        if param == "orario":
            res_dict = self.get_scalata(self.data_dict, "", 0)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Scalata oraria</b>:\n", scala=True)

        elif param == "giornaliero":
            res_dict = self.get_scalata(self.data_dict, "", 1)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Scalata giornaliera</b>:\n", scala=True)

        elif param == "settimanale":
            res_dict = self.get_scalata(self.data_dict, "", 2)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Scalata settimanale</b>:\n", scala=True)

        elif param == "mensile":
            res_dict = self.get_scalata(self.data_dict, "", 3)
            if res_dict:
                to_send = self.pretty_increment(res_dict, "<b>Scalata mensile</b>:\n", scala=True)

        elif param == "rimanenti":
            res_dict = self.get_temp_remaning(self.data_dict)
            if res_dict:
                sorted_x = sorted(res_dict.items(), key=operator.itemgetter(1), reverse=True)

                idx = 1
                to_send = ""
                for elem in sorted_x:
                    if elem[1] < 0:
                        to_send += str(idx) + ") <b>" + elem[0] + "</b> non superabile\n"

                    else:
                        to_send += str(idx) + ") <b>" + elem[0] + "</b> superabile in <b>" + str(
                            elem[1]) + "</b> giorni\n"
                    idx += 1


        elif param == "indietro":

            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text=self.team_init_msg,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=self.inline_team
            )
            return

        # modifica il messaggio in base ai parametri scelti dall'utente
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_send,
            message_id=update.callback_query.message.message_id,
            parse_mode="HTML",
            reply_markup=self.inline_scalata
        )

    # =====================DB=============================

    def update_db(self, teams, numero):
        """Esegue l'update del db dato un messagigo team
        @:param teams: lista di tuple (vedi extract_teams_from_msg)
        @:type: str"""

        # inserisci i nomi nel db
        for team in teams:
            self.db.update_teams(team[0], numero, team[1])

    def get_teams_db(self):
        """Ritorna la lista di teams del db
        @:return:
        res: list of elements (team_name, pnt, numero, last_update)
        least_update: laste update in the form (team_name, pnt, numero, last_update)"""
        # prende i dati dal db
        teams_db = self.db.get_team_all()
        # print(teams_db)

        if not teams_db:
            return False
        # casta il risultato in lista se è un solo dizionario
        if not isinstance(teams_db, list): teams_db = list(teams_db)

        res = []
        for elem in teams_db:
            res.append((elem['nome'], elem['pc'], elem['numero'], elem['update']))
            # print(elem['last_update'].isoweekday())

        # prendi l'aggiornamento piu recente e piu vecchio
        self.last_update = max(res, key=lambda x: x[3])[3]
        self.youngest_update = youngest_update = min(res, key=lambda x: x[3])[3]

        return res

    # ====================UTILS===========================

    def extract_teams_from_msg(self, msg):
        """Estrae i team da un messaggio teams
        @:param msg: messaggio team
        @:type: str
        @:return: list of triple (team_name, pnt, datetime.now)"""
        # compila il regex
        team_regex = re.compile(r"° ([A-z ]+)\(([0-9.]+)")
        # elimina la parte del tuo team
        msg = msg.split("Il tuo team")[0]

        # teams è una lista di tuple con elem[0]=nome_team, elem[1]=punti
        teams = re.findall(team_regex, msg)

        # rimuovi il punto dentro i pc e casta ad int
        teams = [(elem[0], int(elem[1].replace(".", "")), datetime.now()) for elem in teams]

        return teams

    def plot(self, data_dict):
        """Salva un grafico dove le x sono l'unita di tempo e le y i pc totali per ogni Team
        @:param data_dict: il dizionario ritornato da list2dict
        @:type: dict
        @:return: nome dell'immagine (str)
        """

        # definisco un font per la legenda
        fontP = FontProperties()
        fontP.set_size('medium')
        NUM_COLORS = 15

        cm = plt.get_cmap('gist_rainbow')
        fig = plt.figure()
        ax = fig.add_subplot(111)
        # ax.set_color_cycle([cm(1. * i / NUM_COLORS) for i in range(NUM_COLORS)])
        ax.set_color_cycle(['black', 'red', 'sienna', 'olivedrab', 'darkgreen', 'deepskyblue',
                            'navy', 'm', 'darkorchid', 'gold', 'coral', 'aqua', 'gray', 'brown', 'indigo'])
        lines = []
        for key, data_list in data_dict.items():
            dates = [elem[1] for elem in data_list]
            values = [elem[0] for elem in data_list]
            # plot tracccia le linee, scatter i punti
            a = plt.plot(dates, values, label=key)
            lines.append(a[0])
            # plt.scatter(dates, values)

        lgd = plt.legend(bbox_to_anchor=(1.12, 1.01))

        plt.ylabel('PC totali in kk')
        plt.xlabel('Messaggi Inoltrati')
        plt.ticklabel_format(axis='y', style='sci', scilimits=(0, 2))
        save_name = "team_data.png"
        plt.savefig(save_name, bbox_extra_artists=(lgd,), bbox_inches='tight')
        return save_name

    def list2dict(self, data_list):
        """Converte una lista di elementi data dal db in un dizionario
        @:param data: lista di elementi nel formato (vedi get_teams_db)
        @:type: list
        @:return: dizionario con chiavi = nome_team e valore lista di elementi (vedi get_teams_db senza nome team)"""
        res = {}
        # prendi tutti i nomi dei team
        count = Counter(elem[0] for elem in data_list)
        # print(count)

        # aggiugili al dizionario res
        for key in count.keys():
            res[key] = []

        # per ogni elemento nella lista appendi tutto tranne i nomi
        for elem in data_list:
            res[elem[0]].append(elem[1:])
        return res

    def filter_dict_by(self, data_dict, what):
        """Filtra il dizionario ritornato da list2dict a seconda del tempo:
        @:param data_dict: dizionario da filtrare nella forma ritornata da list2dict
        @:type: dict
        @:param what: =0 (hour), =1(day) =2(week), =3(month)
        @:type: int
        @:return: dizionario filtrato in base alla data
        """
        # prendi le chiavi dal dizionario
        filer_dict = {k: [] for k in data_dict.keys()}
        for key in data_dict.keys():
            # crea una lista in cui salvare le date
            dates = []
            # per ogni elemento della lista di valori (pc, numero ,data)
            for elem in data_dict[key]:
                # se il giorno non è gia presente nella lista dates
                if what == 0:
                    # se non sono presenti altre date dentro dates con le caratteristiche di elem[2] (guarda same_datetime)
                    if not any(list(map(lambda date: self.same_datetime(elem[2], date, what), dates))):
                        # aggiungilo sia alle date che al filter dict
                        dates.append(elem[2])
                        filer_dict[key].append(elem)
                elif what == 1:
                    if not any(list(map(lambda date: self.same_datetime(elem[2], date, what), dates))):
                        # aggiungilo sia alle date che al filter dict
                        dates.append(elem[2])
                        filer_dict[key].append(elem)
                elif what == 2:
                    weekday = elem[2].weekday()
                    if not any(list(map(lambda date: self.same_datetime(elem[2], date, what), dates))):
                        # aggiungilo sia alle date che al filter dict
                        dates.append(elem[2])
                        filer_dict[key].append(elem)
                elif what == 3:
                    if not any(list(map(lambda date: self.same_datetime(elem[2], date, what), dates))):
                        # aggiungilo sia alle date che al filter dict
                        dates.append(elem[2])
                        filer_dict[key].append(elem)

        return filer_dict

    def pretty_increment(self, data, initial="", scala=False):
        """Dato un dizionario ritorna lo stampabile
        @:param data: dizionario con key=nome_team, value=int
        @:type: dict
        @:param initial: stringa iniziale da stampare
        @:type: str
        @:param scala: bool per la scala
        @:type: bool
        @:return: stringa da mandare allo user"""

        if not scala:
            # sorto il dizionario, ottenendo una lista di tuple del tipo (nome, incr)
            sorted_x = sorted(data.items(), key=operator.itemgetter(1), reverse=True)

            idx = 1
            res = initial
            for elem in sorted_x:
                if idx == 1:
                    res += str(idx) + ")🥇 <b>" + elem[0] + "</b> con <b>" + "{:,}".format(math.floor(elem[1])).replace(
                        ",", ".") + "</b>\n"
                elif idx == 2:
                    res += str(idx) + ")🥈 <b>" + elem[0] + "</b> con <b>" + "{:,}".format(
                        (math.floor(elem[1]))).replace(",", ".") + "</b>\n"
                elif idx == 3:
                    res += str(idx) + ")🥉 <b>" + elem[0] + "</b> con <b>" + "{:,}".format(
                        (math.floor(elem[1]))).replace(",", ".") + "</b>\n"
                else:
                    res += str(idx) + ") <b>" + elem[0] + "</b> con <b>" + "{:,}".format((math.floor(elem[1]))).replace(
                        ",", ".") + "</b>\n"
                idx += 1
        else:
            # sorto il dizionario, ottenendo una lista di tuple del tipo (nome, incr)
            sorted_x = sorted(data.items(), key=operator.itemgetter(1), reverse=True)

            idx = 1
            res = initial
            for elem in sorted_x:
                res += str(idx) + ") <b>" + elem[0] + "</b> superabile con <b>" + "{:,}".format(
                    math.floor(elem[1][0])).replace(
                    ",", ".") \
                       + "</b> (<i>" + "{:,}".format(math.floor(elem[1][1])).replace(",", ".") + " a testa </i>)\n"
                idx += 1

        return res

    def same_datetime(self, datetime1, datetime2, what):
        """Funzione per controllare l'equivalenza tra datetime
        @:param datetime1/2: i due datetime
        @:type: datetime
        @:param what: dove fermarsi =0 (ora), =1 (giorno), =2(settimana), =3(mese)"""
        if datetime1.year == datetime2.year:
            if datetime1.month == datetime2.month:
                if what == 3: return True
                if datetime1.weekday() == datetime2.weekday():
                    if what == 2: return True
                    if datetime1.day == datetime2.day:
                        if what == 1: return True
                        if datetime1.hour == datetime2.hour:
                            if what == 0: return True

        return False

    def get_temporal_difference(self, initial_date, final_date, what):
        """Calcola la differenza tra due date
        @:param initial/final_date: la data iniziale e finale
        @:type: datetime
        @:param what: l'unità di tempo (0,1,2,3)->(ore,giorni,settimane,mesi)
        @:type:int
        @:return: numero di unità temporali passate tra la data iniziale e quella finale"""

        difference = final_date - initial_date
        res = -1
        if what == 0:
            res = divmod(difference.total_seconds(), 3600)[0]
        elif what == 1:
            res = difference.days
        elif what == 2:
            res = difference.days / 7
        elif what == 3:
            res = difference.days / 30

        return res

    # ===================Inc and Stima=====================

    def get_total_increment(self, data_dict, mean):
        """Ritorna un dizionario con key=nomeTeam e value=incremento totale (int)
          @:param data_dict: il dizionario ritornato da list2dict
          @:type: dict
          @:param mean: se vuoi la media o il totale
          @:type: bool
          @:return: ritorna un dizionario con coppia team-incrementoTotale"""

        res_dict = {}

        # per ogni team nel dizionario
        for key in data_dict.keys():
            # mi ricavo i tot_pc e inizzializzo due int
            tot_pc = [elem[0] for elem in data_dict[key]]
            incr = 0
            idx = 0
            # prendo i pc a coppie di 2 per farne la differenza
            for i in range(0, len(tot_pc), 2):
                to_calc = tot_pc[i:i + 2]
                # se sono arrivato all'ultimo passo
                if len(to_calc) != 2: continue
                # calcolo l'incremento
                incr += abs(to_calc[0] - to_calc[1])
                # print(incr)
                # aggiungo uno a idx
                idx += 1
            # calcolo l'incremento medio
            if mean: incr = incr / math.ceil(len(tot_pc) / idx)

            # e lo aggiungo al dizionario
            res_dict[key] = incr

        return res_dict

    def get_last_update_increment(self, data):
        """Ritorna un dizionario con key=nomeTeam e value=incremento dall'ultimo aggiornamento (int)
          @:param data_dict: il dizionario ritornato da list2dict
          @:type: dict
          @:return: ritorna un dizionario con coppia team-incremento"""

        # prendo solo gli ultimi due elementi del dizionario
        filtered_dict = {}
        for key in data.keys():
            filtered_dict[key] = data[key][-2:]

        # calcolo l'incremento
        res_dict = {}
        for key in filtered_dict.keys():
            # mi ricavo i tot_pc e inizzializzo due int
            tot_pc = [elem[0] for elem in filtered_dict[key]]
            incr = abs(tot_pc[0] - tot_pc[1])
            idx = 0
            res_dict[key] = incr

        return res_dict

    def get_total_pc(self, data_dict):
        """Ritorna il dizionario con key=nomeTeam, value=pcTotali
        @:param data_dict: il dizionario ritornato da list2dict
        @:type: dict
        @:return: ritorna un dizionario con coppia team-pcTotali"""

        filtered_dict = {}
        for key in data_dict.keys():
            filtered_dict[key] = data_dict[key][-1][0]

        return filtered_dict

    def get_stima(self, data_dict, what):
        """Ritorna i pc totali stimati secondo l'unita di tempo descritta da what
         @:param data: dizionario con key=nome_team, value=int
        @:type: dict
        @:param what: unita di tempo =0 (ora), =1 (giorno), =2 (settimana), =3 (mese)
        @:type:int
        @:return: ritorna un dizionario con coppia team-incrementoMedio"""

        incr = self.get_temporal_increment(data_dict, what)

        if not incr: return False
        tot_pc = self.get_total_pc(data_dict)

        h_stima = {}

        for key in tot_pc.keys():
            h_stima[key] = incr[key] + tot_pc[key]

        return h_stima

    def get_temporal_increment(self, data_dict, what):
        """Ritorna un dizionario con key=nomeTeam e value=incremento medio (int)
        @:param data_dict: il dizionario ritornato da list2dict
        @:type: dict
        @:param what: unita di tempo da considerare =0 (ora), =1 (giorno), =2 (settimana), =3(mese)
        @:type: int
        @:return: ritorna un dizionario con coppia team-incrementoMedio"""

        filter_dict = self.filter_dict_by(data_dict, what)

        iter_dict = {}

        for key in filter_dict.keys():
            # se la lista di incrementi contiene un solo elemento non posso fare la stima
            if len(filter_dict[key]) > 1: iter_dict[key] = filter_dict[key]

        if not iter_dict:
            return False

        res_dict = {}

        # per ogni team nel dizionario
        for key in iter_dict.keys():
            # mi ricavo i tot_pc e inizzializzo due int
            tot_pc = [elem[0] for elem in iter_dict[key]]
            incr = 0
            to_divide = self.get_temporal_difference(iter_dict[key][0][2], iter_dict[key][-1][2], what)
            # prendo i pc a coppie di 2 per farne la differenza
            for i in range(0, len(tot_pc)):
                to_calc = tot_pc[i:i + 2]
                # se sono arrivato all'ultimo passo
                if len(to_calc) != 2: continue
                # calcolo l'incremento
                incr += abs(to_calc[0] - to_calc[1])
                # print(incr)
                # aggiungo uno a idx
            # calcolo l'incremento medio
            incr = math.ceil(incr / to_divide)
            # incr = incr / math.ceil(idx)
            # e lo aggiungo al dizionario
            res_dict[key] = incr

        return res_dict

    def get_temp_remaning(self, data_dict):
        """Restituisce il tempo che serve per raggiungere un determinato team"""
        # guarda se il nome digitato è presente tra le chiavi (minuscole e maiuscole)
        found = False
        # todo: chiedi il nome del team all'utente
        team_name = "I Fancazzisti"
        for name in data_dict.keys():
            # print(name)
            # se hai trovato il nome cambialo con la chiave
            if team_name in name:
                found = True
                team_name = name
                break
            elif team_name in name.lower():
                found = True
                team_name = name
                break

        if not found:
            print("not found")
            return False

        # prendi l'incremento temporale
        temporal_inc = self.get_temporal_increment(data_dict, 1)

        if not temporal_inc:
            print("no temporal")
            return False

        # prendi l'ultimo toto_pc
        last_pc = {}
        for key in data_dict.keys():
            last_pc[key] = data_dict[key][-1:][0][0]

        # unisci i due dizionari
        union_dict = {}
        for key in temporal_inc.keys():
            union_dict[key] = (last_pc[key], temporal_inc[key])

        # prendi il team d'interesse in formato tupla
        team = union_dict[team_name]

        # rimuovi tutti quelli sotto
        filter_dict = {}
        for key in union_dict.keys():
            # salta la scelta dell'utente
            if key == team_name:
                continue
            elif union_dict[key][0] > team[0]:
                filter_dict[key] = union_dict[key]

        res_dict = {}

        for key in filter_dict.keys():
            val = filter_dict[key]
            tot_diff = val[0] - team[0]
            inc_diff = team[1] - val[1]
            restante = math.ceil(tot_diff / inc_diff)
            res_dict[key] = (restante)

        return res_dict

    # fixme
    def get_scalata(self, data_dict, team_name, what):
        """Crea un dizionario per effettuare la scalata dei teams
        @:param data_dict: dizionario (guarda list2dict)
        @:type: dict
        @:param team_name: nome del team digitato dall'utente
        @:type: str
        @:param what: unita di tempo =0(ore) =1 (giorni) =2 (settimane) =3 (mesi)
        @:type: int
        @:return"""

        # guarda se il nome digitato è presente tra le chiavi (minuscole e maiuscole)
        found = False
        # todo: chiedi il nome del team all'utente
        team_name = "I Fancazzisti"
        for name in data_dict.keys():
            # print(name)
            # se hai trovato il nome cambialo con la chiave
            if team_name in name:
                found = True
                team_name = name
                break
            elif team_name in name.lower():
                found = True
                team_name = name
                break

        if not found:
            print("not found")
            return False

        # prendi l'incremento temporale
        temporal_inc = self.get_temporal_increment(data_dict, what)

        if not temporal_inc:
            print("no temporal")
            return False

        # prendi l'ultimo toto_pc
        last_pc = {}
        for key in data_dict.keys():
            last_pc[key] = data_dict[key][-1:][0][0]

        # unisci i due dizionari
        union_dict = {}
        for key in temporal_inc.keys():
            union_dict[key] = (last_pc[key], temporal_inc[key])

        # prendi il team d'interesse in formato tupla
        team = union_dict[team_name]

        # rimuovi tutti quelli sotto
        filter_dict = {}
        for key in union_dict.keys():
            # salta la scelta dell'utente
            if key == team_name:
                continue
            elif union_dict[key][0] > team[0]:
                filter_dict[key] = union_dict[key]

        res_dict = {}

        for key in filter_dict.keys():
            val = filter_dict[key]
            new_incr = val[0] + val[1] - team[0]
            res_dict[key] = (new_incr, new_incr / 20)

        return res_dict


class Crafter:
    def __init__(self, updater, db):
        self.updater = updater
        self.db = db

        disp = updater.dispatcher

        disp.add_handler(RegexHandler("^Lista craft per.*:", self.ricerca))

    def ricerca(self, bot, update):
        """Dato un messaggio di craftlootbot , invia tutti i messaggi separatamente"""
        # controlla che il messaggio sia mandato in privato
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return
        to_send = ""
        for elem in update.message.text.split(":")[1].split("\n")[1:]:
            to_send += elem + "\n" + "Si\n"

        idx = 0
        for elem in to_send.split("\n"):
            if not elem: continue
            update.message.reply_text(elem)
            if idx == 10:
                time.sleep(1)
                idx = 0
            idx += 1


class Mancanti:
    def __init__(self, updater, db, base_items):
        self.db = db
        self.base_items = base_items

        disp = updater.dispatcher

        if not DEBUG:
            eleg = self.db.elegible_loot_user(self.init_mancanti)
            # crea conversazione
            conversation = ConversationHandler(
                [CommandHandler("mancanti", eleg)],
                states={
                    1: [MessageHandler(Filters.text, self.conferma_quantita, pass_user_data=True)],
                    2: [MessageHandler(Filters.text, self.ask_zaino, pass_user_data=True)]

                },
                fallbacks=[CommandHandler('Fine', self.annulla)]
            )

        else:
            # crea conversazione
            conversation = ConversationHandler(
                [CommandHandler("mancanti", self.init_mancanti)],
                states={
                    1: [MessageHandler(Filters.text, self.conferma_quantita, pass_user_data=True)],
                    2: [MessageHandler(Filters.text, self.ask_zaino, pass_user_data=True)]

                },
                fallbacks=[CommandHandler('Fine', self.annulla, pass_user_data=True)]
            )

        disp.add_handler(conversation)

    def init_mancanti(self, bot, update):
        """Funzione per inizzializzare la conversazione per sapere quali oggetti mancano nello zaino"""
        # controlla che il messaggio sia mandato in privato
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return

        update.message.reply_text("Prima di iniziare inviami le quantità minime.\n"
                                  "Se la quantità di un oggetto nel tuo zaino non raggiunge questo numero allora verrà mostrato nel risultato finale\n"
                                  "Usa il valore 0 se vuoi visualizzare gli oggetti che ti mancano\n"
                                  "Le quantità devono essere 6 numeri separati da spazio che andranno a ricorpire le rispettive 6 rarità:\n"
                                  "[C NC R UR L E]")

        return 1

    def conferma_quantita(self, bot, update, user_data):
        """Funzione per confermare la quantità scelta dall'utente e chiedere lo zaino"""
        # prendi cio che ha scritto l'utente
        quantita = update.message.text

        # controlla che non sia vuoto
        if not quantita:
            return self.annulla(bot, update, user_data, "Non hai inviato un numero corretto...annullo")

        # controllo che siano sei numeri
        if len(quantita.split()) != 6:
            return self.annulla(bot, update, user_data,
                                msg="Non hai inserito il numero corretto di parametri (devono essere sei numeri)...annullo")

        quantita_num = []
        # controlla che siano tutti numeri
        try:
            for elem in quantita.split():
                quantita_num.append(int(elem))
        except ValueError:
            return self.annulla(bot, update, user_data, "Non hai inviato un numero corretto...annullo")
        # salva la quantita e inizzializza la chiave zaino
        user_data['quantita'] = quantita_num
        user_data['zaino'] = ""
        user_data['rarita'] = []

        reply_markup = ReplyKeyboardMarkup([["Annulla", "Fine"]], one_time_keyboard=False)

        to_send = "Verrai notificato solo per gli oggetti di rarità [C NC R UR L E] con le rispettive quanità minime ["
        for elem in quantita_num:
            to_send += str(elem) + " "
        to_send += "]\nOra inviami il tuo zaino, quando hai finito clicca <b>Fine</b>, altrimenti <b>Annulla</b>"

        update.message.reply_text(to_send,
                                  parse_mode="HTML",
                                  reply_markup=reply_markup)
        return 2

    # @catch_exception
    def ask_zaino(self, bot, update, user_data):

        text = update.message.text

        # se il messaggio è quello dello zaino
        if ">" in text:
            user_data['zaino'] += text
            return 2

        # se l'utente vuole annullare
        elif "annulla" in text.lower():
            return self.annulla(bot, update, user_data, "Annullo")

        # se ha finito di mandare lo zaino
        elif "fine" in text.lower():
            update.message.reply_text("Calcolo oggetti mancanti...")
            # se lo zaino è vuoto annulla
            if not user_data['zaino']:
                return self.annulla(bot, update, user_data, "Non hai inviato mesaggi zaino")
            # altrimenti calcola cio che devi mandare
            to_send = self.mancanti(user_data)
            if not to_send:
                return self.annulla(bot, update, user_data,
                                    "Possiedi tutti gli oggetti nella quantità specificata...che riccone")
            to_send = text_splitter_bytes(to_send, splitter="\n\n", split_every=2048)
            update.message.reply_text("Oggetti con quantità inferiore a <b>" + str(user_data['quantita']) + "</b>\n",
                                      parse_mode="HTML")

            for elem in to_send:
                if not elem: continue
                update.message.reply_text(elem, parse_mode="HTML")

            # calcolo le percentuali di rarità mancanti
            # conto le occorrenze
            c = Counter(user_data['rarita'])
            # calcolo il totale
            tot = sum(c.values())
            # converto in percentuale
            perc = {}
            for key in c.keys():
                perc[key] = math.floor(c[key] * 100 / tot)

            # ordino
            sorted_x = sorted(perc.items(), key=operator.itemgetter(0), reverse=True)

            # creo la stringa da mandare
            to_send = "Percentuali di rarità mancanti:\n"

            for elem in sorted_x:
                to_send += "<b>" + elem[0] + "</b> - <b>" + str(elem[1]) + "</b>%\n"

            # invio il messaggio
            update.message.reply_text(to_send, parse_mode="HTML")

            return self.annulla(bot, update, user_data, "Fine")

        # non ho capito cosa ha mandato e quindi annullo
        else:
            return self.annulla(bot, update, user_data, "Non ho capito...annullo")

    def mancanti(self, user_data):
        """Funzione per calcolare gli oggetti mancanti
        @:param user_data: dizionario contentete le chiavi zaino e quantita
        @:type: dict
        @:return: stringa da mandare allo user"""

        # creo il regex
        regex = re.compile(r"> (.*) \(([0-9]+)")
        # cerco gli oggetti
        all = re.findall(regex, user_data['zaino'])

        # nomi dgli oggetti trovati nello zaino
        all_names = [elem[0] for elem in all]

        res_list = []

        for elem in self.base_items:
            if elem['name'] in all_names:
                # aggiungo la quantità che ha l'utente
                elem['quantita'] = int([item[1] for item in all if item[0] == elem['name']][0])
                res_list.append(elem)
            else:
                # aggiungo la quantità che non ha l'utente
                elem['quantita'] = 0
                res_list.append(elem)

        # filtro per quantita e rarità
        res_list_C = [elem for elem in res_list if
                      int(elem['quantita']) <= user_data['quantita'][0] and elem['rarity'] == "C"]
        res_list_NC = [elem for elem in res_list if
                       int(elem['quantita']) <= user_data['quantita'][1] and elem['rarity'] == "NC"]
        res_list_R = [elem for elem in res_list if
                      int(elem['quantita']) <= user_data['quantita'][2] and elem['rarity'] == "R"]
        res_list_UR = [elem for elem in res_list if
                       int(elem['quantita']) <= user_data['quantita'][3] and elem['rarity'] == "UR"]
        res_list_L = [elem for elem in res_list if
                      int(elem['quantita']) <= user_data['quantita'][4] and elem['rarity'] == "L"]
        res_list_E = [elem for elem in res_list if
                      int(elem['quantita']) <= user_data['quantita'][5] and elem['rarity'] == "E"]

        # unisco le liste
        res_list = res_list_C + res_list_E + res_list_L + res_list_NC + res_list_R + res_list_UR
        # ordino la lista
        res_list = sorted(res_list, key=lambda k: k['quantita'])

        idx = 0
        step = 0
        counter = 1
        if user_data['quantita'][0] > 10:
            step = math.floor(user_data['quantita'][0] / 10)
        # creo la stringa da mandare
        to_send = "<b>---Quantita minore uguale a " + str(step) + "---</b>\n"

        for elem in res_list:

            if elem['quantita'] > step * counter and idx != elem['quantita']:
                idx = elem['quantita']
                counter += 1

                if step > 0:
                    to_send += "\n<b>---Quantita minore uguale a " + str(step * counter) + "---</b>\n"
                else:
                    to_send += "\n<b>---Quantita minore uguale a " + str(step * counter + idx + 1) + "---</b>\n"

            if elem['quantita'] > 0:
                to_send += "<b>" + elem['name'] + "</b>, ne hai solo <b>" + str(elem['quantita']) + "</b>, rarità <b>" + \
                           elem['rarity'] + "</b>\n"
            else:
                to_send += "Non possidi l'oggetto <b>" + elem['name'] + "</b>, rarità <b>" + elem['rarity'] + "</b>\n"

            user_data['rarita'].append(elem['rarity'])

        return to_send

    def annulla(self, bot, update, user_data, msg=""):
        """Annulla la conversazione e inizzializza lo user data"""
        if msg:
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

        if "quantita" in user_data.keys():
            user_data['quantita'] = []

        if "zaino" in user_data.keys():
            user_data['zaino'] = ""

        if 'rarita' in user_data:
            user_data['rarita'] = []

        return ConversationHandler.END


class Negozi:
    def __init__(self, updater, db):
        self.db = db

        disp = updater.dispatcher

        if not DEBUG:
            eleg = self.db.elegible_loot_user(self.init_negozi)
            # crea conversazione
            conversation = ConversationHandler(
                [CommandHandler("negozi", eleg)],
                states={
                    1: [MessageHandler(Filters.text, self.conferma_quantita, pass_user_data=True)],
                    2: [MessageHandler(Filters.text, self.ask_perc, pass_user_data=True)],
                    3: [MessageHandler(Filters.text, self.ask_zaino, pass_user_data=True)]

                },
                fallbacks=[CommandHandler('Fine', self.annulla)]
            )

        else:
            # crea conversazione
            conversation = ConversationHandler(
                [CommandHandler("negozi", self.init_negozi)],
                states={
                    1: [MessageHandler(Filters.text, self.conferma_quantita, pass_user_data=True)],
                    2: [MessageHandler(Filters.text, self.ask_perc, pass_user_data=True)],
                    3: [MessageHandler(Filters.text, self.ask_zaino, pass_user_data=True)]

                },
                fallbacks=[CommandHandler('Fine', self.annulla, pass_user_data=True)]
            )

        disp.add_handler(conversation)

    def init_negozi(self, bot, update):
        """Funzione per inizzializzare la conversazione per sapere quali oggetti mancano nello zaino"""
        # controlla che il messaggio sia mandato in privato
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return

        update.message.reply_text("Prima di iniziare inviami le quantità minime.\n"
                                  "Se la quantità di un oggetto nel tuo zaino non raggiunge questo numero allora verrà mostrato nel risultato finale\n"
                                  "Usa il valore 0 se non vuoi usare una specifica rarità\n"
                                  "Le quantità devono essere 6 numeri separati da spazio che andranno a ricorpire le rispettive 6 rarità:\n"
                                  "[C NC R UR L E]")

        return 1

    def conferma_quantita(self, bot, update, user_data):
        """Funzione per confermare la quantità scelta dall'utente e chiedere lo zaino"""
        # prendi cio che ha scritto l'utente
        quantita = update.message.text

        # controlla che non sia vuoto
        if not quantita:
            return self.annulla(bot, update, user_data, "Non hai inviato un numero corretto...annullo")

        # controllo che siano sei numeri
        if len(quantita.split()) != 6:
            return self.annulla(bot, update, user_data,
                                msg="Non hai inserito il numero corretto di parametri (devono essere sei numeri)...annullo")

        quantita_num = []
        # controlla che siano tutti numeri
        try:
            for elem in quantita.split():
                quantita_num.append(int(elem))
        except ValueError:
            return self.annulla(bot, update, user_data, "Non hai inviato un numero corretto...annullo")
        # salva la quantita e inizzializza la chiave zaino
        self.init_userdata(user_data)
        user_data['quantita'] = quantita_num

        to_send = "Verranno usate le rarità [C NC R UR L E] con le rispettive quanità minime ["
        for elem in quantita_num:
            to_send += str(elem) + " "
        to_send += "]\nOra inviami la percentuale di oggetti che vuoi usare.\nPer esempio scegliendo 10 userai il " \
                   "10% degli oggetti (per ogni rarità) del tuo zaino.\n" \
                   "Ricorda di inviare un numero compreso da 0 a 100"

        update.message.reply_text(to_send, parse_mode="HTML")

        return 2

    def ask_perc(self, bot, update, user_data):
        perc = update.message.text

        try:
            perc = int(perc)
        except ValueError:
            return self.annulla(bot, update, user_data, "Non hai inviato un numero corretto...annullo")

        except TypeError:
            return self.annulla(bot, update, user_data, "Non hai inviato un numero corretto...annullo")

        user_data['perc'] = perc

        to_send = "Ora inviami il tuo zaino, quando hai finito clicca <b>Fine</b>, altrimenti <b>Annulla</b>"
        reply_markup = ReplyKeyboardMarkup([["Annulla", "Fine"]], one_time_keyboard=False)

        update.message.reply_text(to_send,
                                  parse_mode="HTML",
                                  reply_markup=reply_markup)
        return 3

    # @catch_exception
    def ask_zaino(self, bot, update, user_data):

        text = update.message.text

        # se il messaggio è quello dello zaino
        if ">" in text:
            user_data['zaino'] += text
            return 3

        # se l'utente vuole annullare
        elif "annulla" in text.lower():
            return self.annulla(bot, update, user_data, "Annullo")

        # se ha finito di mandare lo zaino
        elif "fine" in text.lower():
            update.message.reply_text("Calcolo oggetti negozi...")
            # se lo zaino è vuoto annulla
            if not user_data['zaino']:
                return self.annulla(bot, update, user_data, "Non hai inviato mesaggi zaino")

            # altrimenti calcola cio che devi mandare
            to_send_list = self.negozi(user_data)
            if len(to_send_list) == 0:
                return self.annulla(bot, update, user_data,
                                    "Non hai tutti questi oggetti")

            for elem in to_send_list:
                bot.sendMessage(update.message.chat.id, elem)

            return self.annulla(bot, update, user_data, "Fine")

        # non ho capito cosa ha mandato e quindi annullo
        else:
            return self.annulla(bot, update, user_data, "Non ho capito...annullo")

    def negozi(self, user_data):
        """Funzione per calcolare gli oggetti mancanti
        @:param user_data: dizionario contentete le chiavi zaino e quantita
        @:type: dict
        @:return: stringa da mandare allo user"""

        # creo il regex
        regex = re.compile(r"> (.*) \(([0-9]+)")
        # cerco gli oggetti

        all_c = re.findall(regex, user_data['zaino'].split("Comuni:")[-1])
        all_nc = re.findall(regex, user_data['zaino'].split("Non Comuni:")[-1].split("\n\n")[0])
        all_r = re.findall(regex, user_data['zaino'].split("Rari:")[-1].split("\n\n")[0])
        all_ur = re.findall(regex, user_data['zaino'].split("Ultra Rari:")[-1].split("\n\n")[0])
        all_l = re.findall(regex, user_data['zaino'].split("Leggendari:")[-1].split("\n\n")[0])
        all_e = re.findall(regex, user_data['zaino'].split("Epici:")[-1].split("\n\n")[0])

        # filtro per quantita e rarità
        filter_list_C = [elem for elem in all_c if
                         int(elem[1]) >= user_data['quantita'][0] and  user_data['quantita'][0]]
        filter_list_NC = [elem for elem in all_nc if
                          int(elem[1]) >= user_data['quantita'][1] and  user_data['quantita'][1]]
        filter_list_R = [elem for elem in all_r if
                         int(elem[1]) >= user_data['quantita'][2] and  user_data['quantita'][2]]
        filter_list_UR = [elem for elem in all_ur if
                          int(elem[1]) >= user_data['quantita'][3] and  user_data['quantita'][3]]
        filter_list_L = [elem for elem in all_l if
                         int(elem[1]) >= user_data['quantita'][4] and  user_data['quantita'][4]]
        filter_list_E = [elem for elem in all_e if
                         int(elem[1]) >= user_data['quantita'][5] and  user_data['quantita'][5]]

        all_list = filter_list_C + filter_list_NC + filter_list_R + filter_list_UR + filter_list_L + filter_list_E

        # nomi dgli oggetti trovati nello zaino
        perc_all = [(elem[0], math.floor(int(elem[1]) / user_data['perc'])) for elem in all_list]

        to_send_list = []
        to_send = "/negozio "
        idx = 0
        for elem in perc_all:
            if not elem[1]: continue
            to_send += f"{elem[0]}::{int(elem[1])},"
            idx += 1
            if idx == 9:
                to_send_list.append(to_send.rstrip(","))
                to_send = "/negozio "
                idx = 0

        to_send = to_send.rstrip(",")
        to_send_list.append(to_send)

        return to_send_list

    def annulla(self, bot, update, user_data, msg=""):
        """Annulla la conversazione e inizzializza lo user data"""
        if msg:
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

        if "quantita" in user_data.keys():
            user_data['quantita'] = []

        if "zaino" in user_data.keys():
            user_data['zaino'] = ""

        if 'rarita' in user_data:
            user_data['rarita'] = []

        if 'perc' in user_data:
            user_data['perc'] = 0

        return ConversationHandler.END

    def init_userdata(self, user_data):
        user_data['quantita'] = 0
        user_data['zaino'] = ""
        user_data['rarita'] = []
        user_data['perc'] = 0


class NegoziPlus:
    """

    all_list : lista di elemnti (nome_oggetto,quantità,id_oggetto)
    """

    def __init__(self, updater, db,base_item):
        self.db = db
        self.base_items=base_item

        disp = updater.dispatcher

        # crea conversazione
        conversation = ConversationHandler(
            [CommandHandler("negozip", self.init_negozi)],
            states={
                1: [MessageHandler(Filters.text, self.conferma_quantita, pass_user_data=True)],
                2: [MessageHandler(Filters.text, self.ask_perc, pass_user_data=True)],
                3: [MessageHandler(Filters.text, self.ask_zaino, pass_user_data=True)],
                4: [MessageHandler(Filters.text, self.ask_ricerca, pass_user_data=True)],
                5: [MessageHandler(Filters.text, self.get_perc, pass_user_data=True)],

            },
            fallbacks=[CommandHandler('Fine', self.annulla)]
        )

        disp.add_handler(conversation)

    def init_negozi(self, bot, update):
        """Funzione per inizzializzare la conversazione per sapere quali oggetti mancano nello zaino"""

        if update.message.from_user.id!=24978334:return


        # controlla che il messaggio sia mandato in privato
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return

        update.message.reply_text("Prima di iniziare inviami le quantità minime.\n"
                                  "Se la quantità di un oggetto nel tuo zaino non raggiunge questo numero allora verrà mostrato nel risultato finale\n"
                                  "Usa il valore 0 se non vuoi usare una specifica rarità\n"
                                  "Le quantità devono essere 6 numeri separati da spazio che andranno a ricorpire le rispettive 6 rarità:\n"
                                  "[C NC R UR L E]")

        return 1

    def conferma_quantita(self, bot, update, user_data):
        """Funzione per confermare la quantità scelta dall'utente e chiedere lo zaino"""
        # prendi cio che ha scritto l'utente
        quantita = update.message.text

        # controlla che non sia vuoto
        if not quantita:
            return self.annulla(bot, update, user_data, "Non hai inviato un numero corretto...annullo")

        # controllo che siano sei numeri
        if len(quantita.split()) != 6:
            return self.annulla(bot, update, user_data,
                                msg="Non hai inserito il numero corretto di parametri (devono essere sei numeri)...annullo")

        quantita_num = []
        # controlla che siano tutti numeri
        try:
            for elem in quantita.split():
                quantita_num.append(int(elem))
        except ValueError:
            return self.annulla(bot, update, user_data, "Non hai inviato un numero corretto...annullo")
        # salva la quantita e inizzializza la chiave zaino
        self.init_userdata(user_data)
        user_data['quantita'] = quantita_num

        to_send = "Verranno usate le rarità [C NC R UR L E] con le rispettive quanità minime ["
        for elem in quantita_num:
            to_send += str(elem) + " "
        to_send += "]\nOra inviami la percentuale di oggetti che vuoi usare.\nPer esempio scegliendo 10 userai il " \
                   "10% degli oggetti (per ogni rarità) del tuo zaino.\n" \
                   "Ricorda di inviare un numero compreso da 0 a 100"

        update.message.reply_text(to_send, parse_mode="HTML")

        return 2

    def ask_perc(self, bot, update, user_data):
        perc = update.message.text

        try:
            perc = int(perc)
        except ValueError:
            return self.annulla(bot, update, user_data, "Non hai inviato un numero corretto...annullo")

        except TypeError:
            return self.annulla(bot, update, user_data, "Non hai inviato un numero corretto...annullo")

        user_data['perc'] = perc

        to_send = "Ora inviami il tuo zaino, quando hai finito clicca <b>Fine</b>, altrimenti <b>Annulla</b>"
        reply_markup = ReplyKeyboardMarkup([["Annulla", "Fine"]], one_time_keyboard=False)

        update.message.reply_text(to_send,
                                  parse_mode="HTML",
                                  reply_markup=reply_markup)
        return 3

    # @catch_exception
    def ask_zaino(self, bot, update, user_data):

        text = update.message.text

        # se il messaggio è quello dello zaino
        if ">" in text:
            user_data['zaino'] += text
            return 3

        # se l'utente vuole annullare
        elif "annulla" in text.lower():
            return self.annulla(bot, update, user_data, "Annullo")

        # se ha finito di mandare lo zaino
        elif "fine" in text.lower():
            update.message.reply_text("Calcolo oggetti negozi...")
            # se lo zaino è vuoto annulla
            if not user_data['zaino']:
                return self.annulla(bot, update, user_data, "Non hai inviato mesaggi zaino")

            # altrimenti calcola cio che devi mandare
            to_send_list = self.negozi(user_data)
            if len(to_send_list) == 0:
                return self.annulla(bot, update, user_data,
                                    "Non hai tutti questi oggetti")

            for elem in to_send_list:
                bot.sendMessage(update.message.chat.id, elem)

            reply_markup = ReplyKeyboardMarkup([["Annulla", "Fine"]], one_time_keyboard=False)
            update.message.reply_text("Ora inoltrami tutti i risulati di riceca", reply_markup=reply_markup)

            return 4

        # non ho capito cosa ha mandato e quindi annullo
        else:
            return self.annulla(bot, update, user_data, "Non ho capito...annullo")

    def negozi(self, user_data):
        """Funzione per calcolare gli oggetti mancanti
        @:param user_data: dizionario contentete le chiavi zaino e quantita
        @:type: dict
        @:return: stringa da mandare allo user"""

        # creo il regex
        regex = re.compile(r"> (.*) \(([0-9]+)")
        # cerco gli oggetti

        all_c = re.findall(regex, user_data['zaino'].split("Comuni:")[-1])
        all_nc = re.findall(regex, user_data['zaino'].split("Non Comuni:")[-1].split("\n\n")[0])
        all_r = re.findall(regex, user_data['zaino'].split("Rari:")[-1].split("\n\n")[0])
        all_ur = re.findall(regex, user_data['zaino'].split("Ultra Rari:")[-1].split("\n\n")[0])
        all_l = re.findall(regex, user_data['zaino'].split("Leggendari:")[-1].split("\n\n")[0])
        all_e = re.findall(regex, user_data['zaino'].split("Epici:")[-1].split("\n\n")[0])

        # filtro per quantita e rarità
        filter_list_C = [elem for elem in all_c if
                         int(elem[1]) >= user_data['quantita'][0] and  user_data['quantita'][0]]
        filter_list_NC = [elem for elem in all_nc if
                          int(elem[1]) >= user_data['quantita'][1] and  user_data['quantita'][1]]
        filter_list_R = [elem for elem in all_r if
                         int(elem[1]) >= user_data['quantita'][2] and  user_data['quantita'][2]]
        filter_list_UR = [elem for elem in all_ur if
                          int(elem[1]) >= user_data['quantita'][3] and  user_data['quantita'][3]]
        filter_list_L = [elem for elem in all_l if
                         int(elem[1]) >= user_data['quantita'][4] and  user_data['quantita'][4]]
        filter_list_E = [elem for elem in all_e if
                         int(elem[1]) >= user_data['quantita'][5] and  user_data['quantita'][5]]

        all_list = filter_list_C + filter_list_NC + filter_list_R + filter_list_UR + filter_list_L + filter_list_E

        new_all_list=[]

        for item in all_list:
            try:
                if not next((elem["craftable"] for elem in self.base_items if elem['name'] == item[0])):
                    new_all_list.append(item)
            except StopIteration:
                pass
        # nomi dgli oggetti trovati nello zaino
        perc_all = [(elem[0], math.floor(int(elem[1]) / user_data['perc'])) for elem in new_all_list]

        user_data['all_list'] = perc_all

        to_send_list = []
        to_send = "/ricerca "
        idx = 0
        for elem in perc_all:
            if not elem[1]: continue
            to_send += f"{elem[0]},"
            idx += 1
            if idx == 3:
                to_send_list.append(to_send.rstrip(","))
                to_send = "/ricerca "
                idx = 0

        to_send = to_send.rstrip(",")
        to_send_list.append(to_send)

        return to_send_list

    def ask_ricerca(self, bot, update, user_data):
        text = update.message.text

        # se il messaggio è quello dello zaino
        if "Risultati ricerca" in text:
            user_data['ricerca'] += text
            return 4

        # se l'utente vuole annullare
        elif "annulla" in text.lower():
            return self.annulla(bot, update, user_data, "Annullo")

        # se ha finito di mandare lo zaino
        elif "fine" in text.lower():
            update.message.reply_text("Calcolo oggetti negozi...")
            # se lo zaino è vuoto annulla
            if not user_data['ricerca']:
                return self.annulla(bot, update, user_data, "Non hai inviato mesaggi zaino")

            # altrimenti calcola cio che devi mandare
            user_data['all_list'] = self.merge_list(user_data)

            update.message.reply_text(
                "Ora inviami la percentuale di prezzo in piu o in meno da adottare (-100 -> +100)")

            return 5

        # non ho capito cosa ha mandato e quindi annullo
        else:
            return self.annulla(bot, update, user_data, "Non ho capito...annullo")

    def merge_list(self, user_data):

        negozi_re = re.compile(r"Negozi per ([A-z ]+):\n> .*\(([0-9 .]+)")

        finds = re.findall(negozi_re, user_data['ricerca'])

        new_list = []

        for (oggetto, quantita) in user_data['all_list']:
            try:
                prezzo = next((item[1] for item in finds if item[0] == oggetto))
                prezzo = prezzo.replace(".", "")
                prezzo = int(prezzo)
                new_list.append((oggetto, quantita, prezzo))
            except StopIteration:pass

        return new_list

    def get_perc(self, bot, update, user_data):
        text = update.message.text

        try:
            perc = int(text)

        except ValueError:
            return self.annulla(bot, update, user_data, msg="Non hai inviato un numero corretto!")

        res_list = [(oggetto, quantita, math.ceil((prezzo - prezzo * perc/100)/10)*10) for
                    (oggetto, quantita, prezzo) in user_data['all_list']]

        to_send_list = []
        to_send = "/negozio "
        idx = 0
        for elem in res_list:
            to_send += f"{elem[0]}:{elem[2]}:{int(elem[1])},"
            idx += 1
            if idx == 9:
                to_send_list.append(to_send+" #")
                to_send = "/negozio "
                idx = 0

        to_send = to_send+ " #"
        to_send_list.append(to_send)

        for msg in to_send_list:
            update.message.reply_text(msg)

        return self.annulla(bot, update, user_data, msg="Fine")

    def annulla(self, bot, update, user_data, msg=""):
        """Annulla la conversazione e inizzializza lo user data"""
        if msg:
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

        if "quantita" in user_data.keys():
            user_data['quantita'] = []

        if "zaino" in user_data.keys():
            user_data['zaino'] = ""

        if 'rarita' in user_data:
            user_data['rarita'] = []

        if 'perc' in user_data:
            user_data['perc'] = 0

        if 'all_list' in user_data:
            user_data['all_list'] = []

        if 'ricerca' in user_data:
            user_data['ricerca'] = ""

        return ConversationHandler.END

    def init_userdata(self, user_data):
        user_data['quantita'] = 0
        user_data['zaino'] = ""
        user_data['rarita'] = []
        user_data['perc'] = 0
        user_data['all_list'] = []
        user_data['ricerca'] = ""


class DiffSchede:
    def __init__(self, updater, db):
        self.db = db

        disp = updater.dispatcher

        if not DEBUG:
            eleg = self.db.elegible_loot_user(self.init_diff)
            # crea conversazione
            conversation = ConversationHandler(
                [CommandHandler("diffschede", eleg, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.diff_loop, pass_user_data=True)]

                },
                fallbacks=[CommandHandler('Fine', self.annulla, pass_user_data=True)]
            )

        else:
            # crea conversazione
            conversation = ConversationHandler(
                [CommandHandler("diffschede", self.init_diff, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.diff_loop, pass_user_data=True)]

                },
                fallbacks=[CommandHandler('Fine', self.annulla, pass_user_data=True)]
            )

        disp.add_handler(conversation)

    def init_diff(self, bot, update, user_data):

        reply_markup = ReplyKeyboardMarkup([["Annulla", "Fine"]], one_time_keyboard=False)

        to_send = "Perfetto ora mandami tutte le schede dettaglio membri una alla volta\n" \
                  "Clicca fine quando le hai inviate tutte altrimenti annulla."
        update.message.reply_text(to_send, reply_markup=reply_markup)

        user_data['text'] = []
        return 1

    def diff_loop(self, bot, update, user_data):

        choice = update.message.text

        if "Fine" in choice:
            # esegui un check su ogni messaggio

            for msg in user_data['text']:
                if "pnt creazione" not in msg:
                    return self.annulla(bot, update, user_data, msg + "\n\nNon è valido")

            res = self.diff("\n".join(user_data['text']))
            update.message.reply_text(self.pretty_diff(res), reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
            return self.annulla(bot, update, user_data)
        elif "Annulla" in choice:
            print("annulla")
            return self.annulla(bot, update, user_data, "Ok annullo")

        else:
            user_data['text'].append(choice)
            return 1

    def annulla(self, bot, update, user_data, msg=""):
        """Annulla la conversazione e inizzializza lo user data"""
        if msg:
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

        if "text" in user_data.keys():
            user_data['text'] = []

        return ConversationHandler.END

    def pretty_diff(self, data):
        """Dato un dizionario ritorna lo stampabile
        @:param data: dizionario con key=nome_team, value=pc
        @:type: dict
        @:return: stringa da mandare allo user"""

        data_number = {k: v for k, v in data.items() if not isinstance(v, str)}
        none_number = {k: v for k, v in data.items() if isinstance(v, str)}

        # sorto il dizionario, ottenendo una lista di tuple del tipo (nome, incr)
        sorted_x = sorted(data_number.items(), key=operator.itemgetter(1), reverse=True)
        if not any([elem[1] for elem in sorted_x]):
            return "Hai mandato due volte la stessa scheda...babbo"
        idx = 1
        res = ""
        for elem in sorted_x:
            if idx == 1:
                res += str(idx) + ")🥇 <b>" + elem[0] + "</b> con <b>" + "{:,}".format(math.floor(elem[1])).replace(
                    ",", ".") + "</b>\n"
            elif idx == 2:
                res += str(idx) + ")🥈 <b>" + elem[0] + "</b> con <b>" + "{:,}".format(
                    (math.floor(elem[1]))).replace(",", ".") + "</b>\n"
            elif idx == 3:
                res += str(idx) + ")🥉 <b>" + elem[0] + "</b> con <b>" + "{:,}".format(
                    (math.floor(elem[1]))).replace(",", ".") + "</b>\n"
            else:
                res += str(idx) + ") <b>" + elem[0] + "</b> con <b>" + "{:,}".format((math.floor(elem[1]))).replace(
                    ",", ".") + "</b>\n"
            idx += 1

        for key in none_number.keys():
            res += str(idx) + ") <b>" + key + "</b>, " + none_number[key] + "\n"
            idx += 1

        return res

    def diff(self, text):
        """Prende in ingresso i messaggi contentei due dettagli memerbi e ritorna il dizionario con gli incrementi
        @:param text: l'unione di due schede messaggio
        @:type: str
        @:return: dizionario con key=username value=pc"""

        regex_name = re.compile(r"^(.*) :")
        regex_pc = re.compile(r"package: ([0-9]+)")
        text = emoji.demojize(text)

        res = []
        for elem in text.split("\n\n"):
            nome = re.findall(regex_name, elem)
            pc = re.findall(regex_pc, elem)
            if not nome or not pc: continue
            nome = nome[0]
            pc = pc[0]
            res.append((nome, pc))

        names = set([elem[0] for elem in res])

        res_dict = {}
        for name in names:
            res_dict[name] = []

        for elem in res:
            res_dict[elem[0]].append(elem[1])

        for key in res_dict.keys():
            try:
                res_dict[key] = abs(int(res_dict[key][0]) - int(res_dict[key][1]))
            except IndexError:
                res_dict[key] = "Questo user compare solo una volta"

        return res_dict


class Alarm:
    def __init__(self, updater, db):
        self.db = db

        disp = updater.dispatcher

        if DEBUG:
            disp.add_handler(CommandHandler("timerset", self.set_timer,
                                            pass_args=True,
                                            pass_job_queue=True,
                                            pass_chat_data=True))
            disp.add_handler(CommandHandler("timerunset", self.unset, pass_chat_data=True))
        else:
            # crea conversazione
            set_el = db.elegible_loot_user(self.set_timer)
            unset_el = db.elegible_loot_user(self.unset)
            disp.add_handler(CommandHandler("timerset", set_el,
                                            pass_args=True,
                                            pass_job_queue=True,
                                            pass_chat_data=True))
            disp.add_handler(CommandHandler("timerunset", unset_el, pass_chat_data=True))

    def alarm(self, bot, job):
        """Send the alarm message."""
        bot.send_message(job.context['chat_id'], text="<b>TIMER SCADUTO</b>\n" + job.context['msg'], parse_mode="HTML")

    @catch_exception
    def set_timer(self, bot, update, args, job_queue, chat_data):
        """Add a job to the queue."""
        chat_id = update.message.chat_id
        if len(args) != 2:
            update.message.reply_text("Non hai inviato i parametri corretti!\n"
                                      "/timerset hh:mm msg")
            return
        try:
            # args[0] should contain the time for the timer in seconds
            print(args)
            if ":" in args[0]:
                ore = int(args[0].split(":")[0])
                minuti = int(args[0].split(":")[1])
            else:
                ore = int(args[0])
                minuti = 0
            when = datetime.now() + timedelta(hours=ore, minutes=minuti)
            chat_data['when'] = when

            msg = args[1]
            context_dict = {'chat_id': chat_id, 'msg': msg}
            # Add job to queue
            job = job_queue.run_once(self.alarm, when, context=context_dict)
            chat_data['job'] = job
            ora, data = pretty_time_date(when)
            to_send = "Hai settato il timer correttamente!\nIl timer scadrà alle <b>" + ora + "</b> del <i>" + data + "</i>"
            update.message.reply_text(to_send, parse_mode="HTML")

        except (IndexError, ValueError) as e:
            update.message.reply_text(str(e))
            update.message.reply_text("Non hai inviato i parametri corretti!\n"

                                      "/timerset hh:mm msg")

    @catch_exception
    def unset(self, bot, update, chat_data):
        """Remove the job if the user changed their mind."""
        if 'job' not in chat_data:
            update.message.reply_text('Non ci sono timer attivi')
            return

        job = chat_data['job']
        job.schedule_removal()
        del chat_data['job']

        rimanente = chat_data['when'] - datetime.now()
        del chat_data['when']
        giorni = rimanente.days
        ore = abs(giorni * 24 - divmod(rimanente.days * 86400 + rimanente.seconds, 3600)[0])
        minuti = abs(ore * 60 - divmod(rimanente.seconds, 60)[0])

        to_send = "Hai eliminato il timer a "
        if giorni: to_send += str(giorni) + " giorni, "
        if ore: to_send += str(ore) + " ore , "
        if minuti: to_send += str(minuti) + " minuti, "
        if minuti or ore or giorni:
            to_send += " dalla fine"
        else:
            to_send += " qualche secondo dalla fine"

        update.message.reply_text(to_send)


class Most_convinient_pc:

    def __init__(self, updater, db, dipenzende):
        self.db = db
        self.dipendenze = dipenzende

        self.item_perc_to_consume = 0.2  # 20%
        self.max_missing_items = 2

        disp = updater.dispatcher

        if not DEBUG:
            eleg = self.db.elegible_loot_user(self.init_most_convenient)
            # crea conversazione
            conversation = ConversationHandler(
                [CommandHandler("checrafto", eleg, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.get_zaino, pass_user_data=True)],

                },
                fallbacks=[CommandHandler('Fine', self.annulla, pass_user_data=True)]
            )

        else:
            # crea conversazione
            conversation = ConversationHandler(
                [CommandHandler("checrafto", self.init_most_convenient, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.get_zaino, pass_user_data=True)],

                },
                fallbacks=[CommandHandler('Fine', self.annulla, pass_user_data=True)]
            )

        disp.add_handler(conversation)

    def init_most_convenient(self, bot, update, user_data):
        reply_markup = ReplyKeyboardMarkup([["Annulla", "Fine"]], one_time_keyboard=False)

        update.message.reply_text("Mandami il tuo zaino, un messaggio alla votla (fai passare un secondo tra"
                                  " i messaggi).\nClicca Fine quando hai finito altrimenti annulla",
                                  reply_markup=reply_markup)
        user_data['zaino'] = ""
        return 1

    def get_zaino(self, bot, update, user_data):

        text = update.message.text

        # se il messaggio è quello dello zaino
        if ">" in text:
            user_data['zaino'] += text
            return 1

        # se l'utente vuole annullare
        elif "annulla" in text.lower():
            return self.annulla(bot, update, user_data, "Annullo")

        # se ha finito di mandare lo zaino
        elif "fine" in text.lower():
            update.message.reply_text("Calcolo oggetti mancanti...")
            # se lo zaino è vuoto annulla
            if not user_data['zaino']:
                return self.annulla(bot, update, user_data, "Non hai inviato mesaggi zaino")

            res = self.get_res(user_data['zaino'])

            return self.annulla(bot, update, user_data, "Fine")

        # non ho capito cosa ha mandato e quindi annullo
        else:
            return self.annulla(bot, update, user_data, "Non ho capito...annullo")

    def annulla(self, bot, update, user_data, msg=""):
        """Annulla la conversazione e inizzializza lo user data"""
        if msg:
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

        if "quantita" in user_data.keys():
            user_data['quantita'] = []

        if "zaino" in user_data.keys():
            user_data['zaino'] = ""

        if 'rarita' in user_data.keys():
            user_data['rarita'] = []

        return ConversationHandler.END

    # crea la lista di craft  totale (quella con le dipendenze dagli altri oggetti)
    # converti lo zaino in id
    # prendi tutti gli oggetti che puo craftare (lasciando un margine di massimo 2 oggetti mancanti)
    # rimuovi gli X, e quelli che usano i materiali finali
    # ordinali per pc
    # inizzializza una lista di oggetti (dove salvi quelli che hai scelto di craftare)
    # prendi un oggetto random nel 40% di quelli con piu pc e aggiugilo alla lista
    # esegui un loop per consumare il 20% dello zaino, partendo dagli oggetti con piu pc
    # dal secondo in poi verifica che non ci siano piu di tot ripetizioni dello stesso id
    # decidi il tot in base alla minima ripetizione degli oggetti C NC R
    # termina il loop se ci sono piu di tot ripetizioni dello stesso id oppure se ho consumato il 20% dello zaino
    # invia la lista all'utente

    def get_res(self, zaino):
        print("zaino")

        # creo il regex
        regex = re.compile(r"> (.*) \(([0-9]+)")
        # cerco gli oggetti
        all = re.findall(regex, zaino)

        # una lista contenente tutti gli id degli oggetti ripetutti per la quantità trovata
        zaino_id = []

        # converto gli oggetti in id
        for elem in all:
            oggetto = next((item for item in self.dipendenze if item["name"] == elem[0]))
            zaino_id += [oggetto['id']] * int(elem[1])

        print(zaino_id)

        # copia la lista dei craft
        possible_crafts = copy.deepcopy(self.dipendenze)
        print("Possible craft len 1 " + str(len(possible_crafts)))

        # rimuovi gli eleemnti che non sono craftabili
        possible_crafts = [elem for elem in possible_crafts if elem['craftable']]
        print("Possible craft len 2 " + str(len(possible_crafts)))

        # rimuovi le rarità X
        possible_crafts = [elem for elem in possible_crafts if elem['rarity'] != 'X']
        print("Possible craft len 3 " + str(len(possible_crafts)))

        # rimuovi i craft dipendenti dai materiali finali
        possible_crafts = [elem for elem in possible_crafts if [635, 636, 637] not in elem['dipendenze']]
        print("Possible craft len 4 " + str(len(possible_crafts)))

        # rimuovi i craft che non possono essere fatti dall'user
        c1 = Counter(zaino_id)
        for elem in possible_crafts:
            c2 = Counter(elem['dipendenze'])
            diff = c2 - c1
            if len(list(diff.elements())) > self.max_missing_items:
                possible_crafts.pop(elem)

        print("Possible craft len 5 " + str(len(possible_crafts)))

        # ordina la lista per pc
        # possible_crafts = sorted(possible_crafts, key=operator.itemgetter('craft_pnt'), reverse=True)

        craft_vector = [(elem['id'], elem['dipendenze'], elem['craft_points']) for elem in possible_crafts]
        cons = {

        }
        max_item_to_consume = math.floor(len(zaino_id) * self.item_perc_to_consume)

        res = minimize(self.cost_function, craft_vector, args=(max_item_to_consume,),
                       constraints=cons, options={'disp': True})

        print(res)

    def cost_function(self, craft_vector, max_item_to_consume, sign=-1.0):
        print(2)


class Stats:
    def __init__(self, updater, db,all_obj,dipendenze):
        self.db = db

        disp = updater.dispatcher
        self.all_obj=all_obj
        self.dipendenze=dipendenze

        if not DEBUG:
            eleg = self.db.elegible_loot_user(self.init_negozi)
            # crea conversazione
            conversation = ConversationHandler(
                [CommandHandler("stats", eleg, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.ask_zaino, pass_user_data=True)],


                },
                fallbacks=[CommandHandler('Fine', self.annulla)]
            )


        else:
            # crea conversazione
            conversation = ConversationHandler(
                [CommandHandler("stats", self.init_negozi, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.ask_zaino, pass_user_data=True)],


                },
                fallbacks=[CommandHandler('Fine', self.annulla, pass_user_data=True)]
            )

        disp.add_handler(conversation)
        disp.add_handler(CallbackQueryHandler(self.callback,pattern="/stats",pass_user_data=True))


        self.inline = InlineKeyboardMarkup([
                [InlineKeyboardButton("Mancanti", callback_data="/stats mancanti")],
                [InlineKeyboardButton("Possibili", callback_data="/stats possibili")],
                [InlineKeyboardButton("Annulla", callback_data="/stats annulla")]

            ])

    def init_negozi(self, bot, update,user_data):
        """Funzione per inizzializzare la conversazione per sapere quali oggetti mancano nello zaino"""
        # controlla che il messaggio sia mandato in privato
        if "private" not in update.message.chat.type:
            update.message.reply_text("Questo comando è disponibile solo in privata")
            return



        reply_markup = ReplyKeyboardMarkup([["Annulla", "Fine"]], one_time_keyboard=False)

        update.message.reply_text("Inviami il tuo zaino un messaggio alla volta. Fai passare un secondo tra un messaggio e l'altro. Quando "
                                  "hai finito clicca FINE altrimenti ANNULLA\nRicorda anche di mandare i messaggi IN ORDINE"
                                  , reply_markup=reply_markup)

        self.init_userdata(user_data)

        return 1

    # @catch_exception
    def ask_zaino(self, bot, update, user_data):



        text = update.message.text

        # se il messaggio è quello dello zaino
        if ">" in text:
            user_data['zaino'] += text+"\n"
            return 1

        # se l'utente vuole annullare
        elif "annulla" in text.lower():
            return self.annulla(bot, update, user_data, "Annullo")

        # se ha finito di mandare lo zaino
        elif "fine" in text.lower():

            try:
                zaino=user_data['zaino']
            except KeyError:
                return self.annulla(bot,update,user_data,"Non hai inviato uno zaino")


            rarities = self.stats(zaino)

            if rarities is None:
                return self.annulla(bot, update,user_data,"Si è verificato un problema...sicuro di aver inviato lo zaino nell'ordine giusto?")

            pretty_rts = self.pretty_rarity_stats(rarities)
            pretty_gen = self.pretty_general_stats(rarities)

            for elem in pretty_rts:
                update.message.reply_text(elem,parse_mode="HTML")


            update.message.reply_text(pretty_gen,parse_mode="HTML")

            to_send="Puoi anche visualizzare gli oggetti mancanti e i craft possibili cliccando sui bottoni"



            user_data['mancanti']=rarities['general']['mancanti']
            user_data['possibili']=rarities['general']['craftables']

            update.message.reply_text(to_send,reply_markup=self.inline)

            return self.annulla(bot, update, user_data)

        # non ho capito cosa ha mandato e quindi annullo
        else:
            return self.annulla(bot, update, user_data, "Non ho capito...annullo")


    def callback(self,bot,update,user_data):

        param = update.callback_query.data.split()[1]
        to_send = "Puoi anche visualizzare gli oggetti mancanti e i craft possibili cliccando sui bottoni"

        if param=="mancanti":

            mancanti=user_data['mancanti']

            if len(mancanti) == 0:
                update.callback_query.message.reply_text("Non ti manca niente...sbucione")
                return


            file_name=f"mancanti_{update.callback_query.from_user.id}.txt"

            with open(file_name,"w+") as file:
                for elem in mancanti:
                    file.write(elem+'\n')

            with open(file_name,"rb") as file:
                bot.sendDocument(update.callback_query.message.chat_id,file,caption="Oggetti mancanti")


            os.remove(file_name)



        elif param=="possibili":

            craftables=user_data['possibili']

            if len(craftables)==0:
                update.callback_query.message.reply_text("Non puoi fare nulla...sfigato")
                return

            file_name=f"possibili_{update.callback_query.from_user.id}.txt"


            with open(file_name, "w+") as file:

                file.write("Oggetto, Punti craft, Quantità Possibili, Punti craft totali\n")
                for elem in craftables:
                    for item in elem:
                        file.write(str(item) + ",")
                    file.write("\n")

            with open(file_name, "rb") as file:
                bot.sendDocument(update.callback_query.message.chat_id, file, caption="Oggetti mancanti")

            os.remove(file_name)



        else:
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
            reply_markup=self.inline
        )

    def stats(self,zaino):

        regex = re.compile(r"> (.*) \(([0-9]+)")
        # cerco gli oggetti

        all_c = re.findall(regex, zaino.split("Comuni:")[-1])
        all_nc = re.findall(regex, zaino.split("Non Comuni:")[-1].split("\n\n")[0])
        all_r = re.findall(regex, zaino.split("Rari:")[-1].split("\n\n")[0])
        all_ur = re.findall(regex, zaino.split("Ultra Rari:")[-1].split("\n\n")[0])
        all_l = re.findall(regex, zaino.split("Leggendari:")[-1].split("\n\n")[0])
        all_e = re.findall(regex, zaino.split("Epici:")[-1].split("\n\n")[0])
        all_ue = re.findall(regex, zaino.split("Ultra Epici:")[-1].split("\n\n")[0])
        all_s = re.findall(regex, zaino.split("Speciali:")[-1].split("\n\n")[0])
        all_un = re.findall(regex, zaino.split("Unici:")[-1].split("\n\n")[0])
        all_mt = re.findall(regex, zaino.split("Mutaforma:")[-1].split("\n\n")[0])
        all_d = re.findall(regex, zaino.split("Draconici:")[-1].split("\n\n")[0])

        # unisco gli oggetti in un dizionario
        rarities = {'c': all_c, 'nc': all_nc, 'r': all_r, 'ur': all_ur, 'l': all_l, 'e': all_e,
                    'ue': all_ue, 's': all_s, 'un': all_un, 'mt': all_mt, 'd': all_d}

        # per ogni rarità crea un dizzionario
        tot_elem = 0
        all_rarity = []
        for rarity in rarities.keys():
            list_ = [(name, int(quantity)) for (name, quantity) in rarities[rarity]]
            tot_elem += sum(quantity[1] for quantity in list_)
            all_rarity += list_
            rarities[rarity] = {"list": list_}

        rarities = self.rarity_stats(rarities, tot_elem)

        rarities['general'] = {'tot_elem': tot_elem, 'list': all_rarity}

        rarities = self.generl_stats(rarities)

        return rarities

    def rarity_stats(self,rarities, tot_elem):
        # prendo il numero degli oggetti nello zaino

        for rarity in rarities.keys():
            rar_list = rarities[rarity]['list']

            num = sum(item[1] for item in rar_list)
            perc_zaino = round(num / tot_elem * 100, 2)
            mean = math.ceil(num / len(rar_list))
            min_v = min([elem[1] for elem in rar_list])
            max_v = max([elem[1] for elem in rar_list])
            min_v = next(elem for elem in rar_list if elem[1] == min_v)
            max_v = next(elem for elem in rar_list if elem[1] == max_v)
            base = sum([elem[1] for elem in rar_list if
                        not next((item['craftable'] for item in self.all_obj if elem[0] in item['name']))])
            non_base = num - base
            base = round(base / num * 100, 2)
            non_base = round(non_base / num * 100, 2)

            rarities[rarity]['num'] = num
            rarities[rarity]['perc_zaino'] = perc_zaino
            rarities[rarity]['mean'] = mean
            rarities[rarity]['min_v'] = min_v
            rarities[rarity]['max_v'] = max_v
            rarities[rarity]['base'] = base
            rarities[rarity]['non_base'] = non_base

        return rarities

    def look_in_obj(self,name,what, condition=""):

        for item in self.all_obj:
            if condition:
                if item[condition] and item['name']==name: return item[what]
                else: return 0
            else:
                if item['name'] == name: return item[what]
                else: return 0

    def generl_stats(self,rarities):

        tot_elem = rarities['general']["tot_elem"]
        all_rarity = rarities['general']['list']
        base = sum([elem[1] for elem in all_rarity if
                    not next((item['craftable'] for item in self.all_obj if elem[0] in item['name']))])
        non_base = tot_elem - base
        base = round(base / tot_elem * 100, 2)
        non_base = round(non_base / tot_elem * 100, 2)

        estimate_val = sum(
            next((item['estimate'] for item in self.all_obj if elem[0] in item['name'])) * elem[1] for elem in all_rarity)
        value_val = sum(
            next((item['value'] for item in self.all_obj if elem[0] in item['name'])) * elem[1] for elem in all_rarity)
        tot_crft_pnt = sum(
            next((item['craft_pnt'] for item in self.all_obj if elem[0] in item['name'])) * elem[1] for elem in all_rarity)

        id_list = [[next((item['id'] for item in self.dipendenze if elem[0] in item['name']))] * elem[1] for elem in
                   all_rarity]
        id_list = [item for sublist in id_list for item in sublist]
        id_list = Counter(id_list)
        craftables = []
        for item in self.dipendenze:
            if item['craftable'] and item['craft_pnt']:
                prov = id_list.copy()
                item_dip = Counter(item['dipendenze'])
                min_craft = sys.maxsize

                for elem in item_dip.items():

                    min_prov = math.floor(prov[elem[0]] / elem[1])
                    if min_prov < min_craft: min_craft = min_prov

                if min_craft != sys.maxsize and min_craft: craftables.append(
                    (item['name'], item['craft_pnt'], min_craft, item['craft_pnt'] * min_craft))

        base_obj = [elem for elem in self.all_obj if not elem['craftable']]

        mancanti = [elem['name'] for elem in base_obj if
                    elem['name'] not in [item[0] for item in all_rarity] and not elem['craftable'] and elem[
                        'rarity'] in ['C', 'NC', 'R', 'UR', 'L', 'E']]

        rarities['general']['base'] = base
        rarities['general']['non_base'] = non_base
        rarities['general']['estimate_val'] = estimate_val
        rarities['general']['value_val'] = value_val
        rarities['general']['tot_crft_pnt'] = tot_crft_pnt
        rarities['general']['craftables'] = craftables
        rarities['general']['mancanti'] = mancanti

        return rarities

    def pretty_general_stats(self,rarities):

        to_send = f"""
Possiedi in totale <b>{rarities['general']['tot_elem']:,}</b> oggetti di cui il <i>{rarities['general']['base']}%</i> base e il restante <i>{rarities['general']['non_base']}%</i> craftati.
Il valore <b>stimato</b> del tuo zaino è di <i>{rarities['general']['estimate_val']:,}</i>, mentre quello <b>reale</b> è di <i>{rarities['general']['value_val']:,}</i>.
Inoltre il tuo zaino è composto da un totale di <b>{rarities['general']['tot_crft_pnt']:,}</b> punti craft.
    """
        return to_send

    def pretty_rarity_stats(self, rarities):

        to_send_list = []

        for key in rarities.keys():
            if key == "general": continue

            to_send = f"""
Statistiche per rarità <b>{key.upper()}</b>:
Possiedi <i>{rarities[key]['num']:,}</i> oggetti di questo tipo, equivalenti al <b>{rarities[key]['perc_zaino']}%</b> del tuo zaino.
Di questi oggetti il <b>{rarities[key]['base']}%</b> sono base mentre i restanti <b>{rarities[key]['non_base']}%</b> sono craftati.
In media hai <i>{rarities[key]['mean']:,}</i> oggetti con un massimo di <b>{rarities[key]["max_v"][1]:,}</b> per <i>{rarities[key]['max_v'][0]}</i>, e un minimo di <b>{rarities[key]["min_v"][1]:,}</b> per <i>{rarities[key]['min_v'][0]}</i>.
    """

            to_send_list.append(to_send)

        return to_send_list

    def annulla(self, bot, update, user_data, msg=""):
        """Annulla la conversazione e inizzializza lo user data"""
        if msg:
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())


        if "zaino" in user_data.keys():
            user_data['zaino'] = ""

        return ConversationHandler.END

    def init_userdata(self, user_data):
        user_data['zaino'] = ""



