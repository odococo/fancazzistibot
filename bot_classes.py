import inspect
import math
import random
import re
from collections import OrderedDict, Counter
from datetime import timedelta

import emoji
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, RegexHandler, MessageHandler, Filters, CommandHandler, \
    CallbackQueryHandler

from comandi import Command
from utils import is_numeric, catch_exception, text_splitter_bytes

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
            to_send = "/negozio "
            for elem in user_data['quantita']:
                to_send += elem[1] + "::" + elem[0] + ","

            to_send = to_send.rstrip(",")
            bot.sendMessage(update.callback_query.message.chat.id, to_send)
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

            if (len(top_ten) > 10):
                top_ten = top_ten[:9]
                to_print = "I 10 oggetti piu costosi sono:\n"
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
                    new_num = int(num[1]) - int(num[0])  # calcolo la differenza

                    new_line = line.replace(num[0], str(new_num), 1)  # rimpiazzo il primo
                    new_line = new_line.replace(num[1], str(new_num), 1)  # e il secondo
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

        self.attacca_boss_frasi=["Attacca il boss dannazzione!",
        "Lo hai attaccato il boss?","Se non attacchi il boss ti prendo a sberle","Attacca il boss ORA"]


        dispatcher = updater.dispatcher

        if not DEBUG:
            boss_user_decor = db.elegible_loot_user(self.boss_user)
            boss_admin_decor = db.elegible_loot_admin(self.boss_admin)
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
                 RegexHandler("^🏆", self.boss_admin, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.boss_loop, pass_user_data=True)]
                },
                fallbacks=[CommandHandler('Fine', self.fine, pass_user_data=True)]
            )
            dispatcher.add_handler(coversation_boss)

            dispatcher.add_handler(CommandHandler("resetboss", self.boss_reset_ask))

        dispatcher.add_handler( CallbackQueryHandler(self.boss_reset_confirm, pattern="^/resetBoss", pass_user_data=True))

    def cerca_boss(self, msg):
        """Dato il messaggio di attacco ai boss ritorna una lista di liste con elementi nel seguente ordine:\n
        lista[0]: nome \n
        lista[1]: Missione/cava + tempo se in missione o cava, 1 altrimenti\n
        lista[2]: 0 se non c'è stato attacco al boss, tupla altrimenti: tupla[0] danno, tupla[1] numero di boss"""

        #prendi il messaggio
        prova = msg.split("Attività membri:\n")[1]
        #trasforma le omoji in testo
        prova = emoji.demojize(prova)
        #compila i pattern
        name_reg1 = re.compile(r"([0-z_]+) :")
        name_reg2 = re.compile(r"^([0-z_]+) .*")
        obl_reg = re.compile(r":per.*: ([0-z /(/)]+)")
        boss_reg = re.compile(r":boar: ([0-9]+) .*/([0-9])")

        res = []

        #cerca tutto con i vari regex
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
    def boss_admin(self, bot, update, user_data):
        """Inoltra il messaggio del boss, solo per admin
        @:return: ritorna lo state del prossimo handler"""

        # prendi il dizionario, lista  e id
        self.inizzializza_user_data(user_data)
        #prendi i dati dal databse
        boss = self.db.get_punteggi_username()
        #se è vuoto inizzializza
        if not boss:
            boss = {}
            id = 0
        else:
            #differenza tra dizionario e lista
            try:
                id = boss[0]["msg_id"]
                user_data['single_dict'] = False
            except KeyError:
                id = boss["msg_id"]

        #salva i dati
        user_data['punteggi'] = boss
        user_data['last_update_id'] = id

        user_data['lista_boss'] = self.cerca_boss(update.message.text)

        #se il messaggio presenta le stesse info avverti l'user
        if self.same_message(boss, user_data['lista_boss']):
            update.message.reply_text("Hai gia mandato questo messaggio... il database non verrà aggiornato")
            return 1

        # print(user_data['lista_boss'], boss)

        #genera e invia risposta
        reply_markup = ReplyKeyboardMarkup([["Phoenix", "Titan"],["Sveglia", "Annulla"],["Visualizza"]], one_time_keyboard=True)
        update.message.reply_text("Scegli un boss per salvare il punteggio, clicca sveglia per mandare un messaggio a chi non ha attaccato, Visualizza per vedere le info senza salvare i punteggi, oppure annulla.",
                                  reply_markup=reply_markup)
        return 1

    @catch_exception
    def boss_user(self, bot, update, user_data):
        """Se un user vuole visualizzare le stesse info degli admin non ha diritto alle modifiche
                @:return: ritorna lo state del prossimo handler"""


        #prendi le info dal db
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
                                                  'id': [elem[1] for elem in users_name_id if elem[0] == username[0]].pop(0),
                                                  'valutazione': 0,
                                                  'attacchi': 0})  # aggiungo l'user alla lista

                # se lo username è presente nella tabella users del db ma non nel dizionario (quindi non nella tabella punteggi del db)
                elif username[0] in users_name and not username[0] in [elem['username'] for elem in user_data[ 'punteggi']]:
                    user_data['punteggi'].append({'username': username[0],
                                                  'id': [elem[1] for elem in users_name_id if
                                                         elem[0] == username[0]].pop(0),
                                                  # aggiungo l'id associato
                                                  'valutazione': 0,
                                                  'attacchi': 0})  # aggiungo l'user alla lista

            #print(user_data)
            found = False
            #rimuovi dizionari vuoti
            user_data['punteggi']=list(filter(None, user_data['punteggi']))
            print(user_data)

            #per ogni elemento nel messaggio inviato
            for username in user_data['lista_boss']:

                #per ogni username in punteggi
                for single_dict in user_data['punteggi']:

                    # se è gia presente nel db
                    if single_dict['username'] == username[0]:
                        found = True

                        single_dict['msg_id'] = user_data['last_update_id']

                        # non ha attaccato ed è phoenix
                        if user_data['phoenix'] and isinstance(username[2], int):
                            single_dict['valutazione'] += 2

                        # non ha attaccato ed è titan
                        elif not user_data['phoenix'] and isinstance(username[2], int):
                            single_dict['valutazione'] += 1

                        elif isinstance(username[2], tuple):  # ha attaccato
                            #aggiungo gli attacchi
                            single_dict['attacchi'] = username[2][1]


                if not found:
                    skipped.append(username)
                found = False


            # se non ho saltato tutti gli username
            if not len(skipped) == len(user_data['lista_boss']):
                print("all skipped")
                self.db.update_punteggi(user_data['punteggi'])



            #notifica gli users che il punteggio è stato aggiornato
            # for elem in user_data['punteggi']:
            #     bot.sendMessage(elem['id'],"Le valutazioni sono state aggiornate!\n"
            #                                "Sei arrivato al punteggio <b>"+str(elem['valutazione'])+"</b>\n"
            #                                 "Per consultare le regole usa il comando /regoleboss")

            if len(skipped) > 0:
                to_send = "I seguenti users non sono salvati nel bot :\n"
                for users in skipped:
                    to_send += "@" + users[0] + "\n"
                to_send += "Chiedigli di inviare /start a @" + bot.username
                update.message.reply_text(to_send)


            reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Completa", "Fine"]],
                                               one_time_keyboard=False)
            update.message.reply_text("Dati salvati!\nAdesso fammi sapere in che formato vuoi ricevere le info",
                                      reply_markup=reply_markup)

            return 1

        elif choice == "Annulla":
            return self.fine(bot, update, user_data, "Ok")
        elif choice=="Sveglia":
            #prendo gli users in punteggi e nel messaggio
            punteggi_users=self.db.get_punteggi_username()
            attacchi_users= user_data['lista_boss']


            #prendo solo gli username di chi non ha attaccato
            attacchi_users=[elem[0] for elem in attacchi_users if elem[2]==0]
            #faccio lo stesso con i punteggi
            punteggi_users=[elem for elem in punteggi_users if elem['username'] in attacchi_users]

            if not punteggi_users:
                update.message.reply_text("Tutti gli users presenti nel bot hanno attaccato il boss")
                return self.fine(bot, update, user_data)


            #mando il messaggio a tutti i non attaccanti e creo la risposta
            to_send="Ho mandato un messaggio ai seguenti users:\n"
            for elem in punteggi_users:
                bot.sendMessage(elem['id'],random.choice(self.attacca_boss_frasi))
                to_send+="@"+elem['username']+"\n"

            update.message.reply_text(to_send)

        elif choice=="Visualizza":
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
            if elem[1] == 0: to_send += "@" + str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

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

        #print(boss_db)
        users_db = self.db.get_users()
        if not users_db: return False
        users_id = [(elem['username'], elem['id']) for elem in users_db]  # contiene la tupla username,id
        users_punteggio = [elem for elem in users_id if elem[1] in [punteggio['id'] for punteggio in boss_db]]  # ha solo gli elementi (username,id) che sono prenseti nel db punteggio
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

        #prendi l'intervallo
        param = update.message.text.split()[1:]
        self.inizzializza_user_data(user_data)

        #controlla che ci siano 1 o due parametri
        if len(param) == 0 or len(param) > 2:
            update.message.reply_text("Il comando deve essere usato in due modi:\n"
                                      "/cercaCcraft maggioreDi minoreDi\n"
                                      "/cercaCraft maggioreDi\nIn cui maggioreDi e minoreDi sono due numeri rappresentanti"
                                      " l'intervallo di punti craft in cui vuoi cercare.")
            return

        #controlla che siano numerici
        elif len(param) == 1 and is_numeric(param[0]):
            user_data['risultati'] = [elem for elem in self.craftabili if elem['craft_pnt'] >= int(param[0])]
        elif len(param) == 2 and is_numeric(param[0]) and is_numeric(param[1]):
            magg = int(param[0])
            min = int(param[1])
            #print(magg, min)
            if magg > min:
                update.message.reply_text("Il numero maggioreDi non può essere minore del numero minoreDi")
                return
            user_data['risultati'] = [elem for elem in self.craftabili if elem['craft_pnt'] >= magg and
                                      elem['craft_pnt'] <= min]

        else:
            update.message.reply_text("Non hai inviato dei numeri corretti")
            return

        #cerca quanti oggetti sono stati trovati
        num_ris = len(user_data['risultati'])
        if num_ris == 0: return self.no_results(bot, update)

        #inline per la selezione della rarità
        inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("X", callback_data="/rarita X"),
             InlineKeyboardButton("UE", callback_data="/rarita UE"),
             InlineKeyboardButton("E", callback_data="/rarita E")],
            [InlineKeyboardButton("L", callback_data="/rarita L"), InlineKeyboardButton("U", callback_data="/rarita U"),
             InlineKeyboardButton("UR", callback_data="/rarita UR")],
            [InlineKeyboardButton("Tutti", callback_data="/rarita tutti")]
        ])
        #generazione e invio del messaggio
        text = "Ho trovato <b>" + str(num_ris) + "</b> oggetti che rispettano i tuoi parametri\n"

        update.message.reply_text(text +
                                  "Secondo quale rarità vuoi filtrare?", reply_markup=inline, parse_mode="HTML"
                                  )

    @catch_exception
    def filtra_rarita(self, bot, update, user_data):
        """Filtra i risultati trovati precedentemente a seconda della rarità"""
        # todo: prova a far scegliere piu rarità
        #prendi la rarità scelte dall'utente
        #user_data['rarita'] = update.callback_query.data.split()[1]
        rarita = update.callback_query.data.split()[1]
        #filtra se non sono state scelte tutte
        if not "tutti" in rarita:
            user_data['risultati'] = [elem for elem in user_data['risultati'] if elem['rarity'] == rarita]

        #conta i risultati
        num_ris = len(user_data['risultati'])
        if num_ris == 0: return self.no_results(bot, update)

        #genera e invia risposta
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
        #prendi i parametri scelti dall'utente
        rinascita = update.callback_query.data.split()[1]

        # print(self.maggioreDi, self.minoreDi, self.rarita, self.rinascita)
        #filtra
        user_data['risultati'] = [elem for elem in user_data['risultati'] if elem['reborn'] <= int(rinascita)]

        #stessa storia
        if len(user_data['risultati']) == 0: return self.no_results(bot, update)

        #genera e invia risposta
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

        #ordina lista in base a parametro
        elif "puntiCraft" in param:
            sorted_res = sorted(user_data['risultati'], key=lambda key: key["craft_pnt"])
        elif "rarita" in param:
            sorted_res = sorted(user_data['risultati'], key=lambda key: key["rarity"])
        elif "rinascita" in param:
            sorted_res = sorted(user_data['risultati'], key=lambda key: key["reborn"])

        #prendi l'id del messaggio
        message_id = update._effective_chat.id

        #inizzializza titolo
        if sorted_res:
            bot.sendMessage(message_id, "<b>Nome   Punti Craft    Rarità     Rinascita</b>\n", parse_mode="HTML")

        #aggiungi elemeenti
        for elem in sorted_res:
            to_send.append(
                "<b>" + elem['name'] + "</b>   " + str(elem['craft_pnt']) + "   " + elem['rarity'] + "   " + str(
                    elem["reborn"]) + "\n")

        #elimina messaggio di scelta
        bot.delete_message(
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id
        )

        #manda i messaggi ogni 30 elementi
        while to_send:
            bot.sendMessage(message_id, "".join(to_send[:30]), parse_mode="HTML")
            to_send = to_send[30:]

        #azzera lo user_data
        self.inizzializza_user_data(user_data)


class Compra:

    def __init__(self, updater, db):
        self.db = db
        self.scrigni = OrderedDict(
            [('Legno', 600), ('Ferro', 1200), ('Prezioso', 2400), ('Diamante', 3600), ('Leggendario', 7000),
             ('Epico', 15000)]) #dizionario ordinato per mantenere la relazione quantità-tipo scrigno

        disp = updater.dispatcher

        if not DEBUG:
            eleg = self.db.elegible_loot_user(self.sconti)
            disp.add_handler(CommandHandler("compra", eleg, pass_user_data=True))

        else:
            disp.add_handler(CommandHandler("compra", self.sconti, pass_user_data=True))

        #crea conversazione
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
               "0 Lengo [C], 0 Ferro [NC], 20% Prezioso [R], 30% Diamante [UR], 25% Leggendario [L] e 25% Epico [E].\nNota bene la somma dei numeri deve fare 100!"
        update.message.reply_text(text)
        return 2

    def scrigni_func(self, bot, update, user_data):
        """Salva gli scrigni e calcola la quantità da comprare """
        param = update.message.text.split(" ")
        #check se l'user ha impostato correttamente gli scrigni
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

        #usa dizionario ordinato per non perdere la relazione quantita scrignio-tipo
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
        #genera il messaggio da inviare e invia
        for elem in res.keys():

            if res[elem]: text += "Compra <b>" + str(res[elem]) + "</b> di Scrigno " + elem + "\n"

        if not text: text = "Si è verificato un errore...contatta @brandimax"

        update.message.reply_text(text, parse_mode="HTML")
        #rinizzializza lo user_data
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

#todo
class Constes:

    def __init__(self, updater):
        self.updater = updater
        self.contest_flag = False
        self.contest_creator = False

        disp = updater.dispatcher


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

        ])#inline per il messaggio

        disp = updater.dispatcher
        if DEBUG:
            disp.add_handler(RegexHandler("^Giocatore 👤", self.add_player))
            disp.add_handler(CommandHandler("top", self.top_command))
        else:
            add_player_decor = self.db.elegible_loot_user(self.add_player)
            top_command_decor = self.db.elegible_loot_user(self.top_command)
            disp.add_handler(RegexHandler("^Giocatore 👤", add_player_decor))
            disp.add_handler(CommandHandler("top", top_command_decor))

        disp.add_handler(CallbackQueryHandler(self.get_top, pattern="/top"))

    def add_player(self, bot, update):
        """Aggiunge user nel db e visualizza top player"""

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

    def top_command(self, bot, update):

        to_send = "In base a cosa desideri visualizzare la classifica?"
        update.message.reply_text(to_send, reply_markup=self.inline)

    def get_top(self, bot, update):
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

        #sono sfaticato
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

        #modifica messaggio
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_send,
            message_id=update.callback_query.message.message_id,
            reply_markup=self.inline,
            parse_mode="HTML"

        )

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

        #heroku manda l'ora corrente indietro di uno, aggiungi un ora
        future_hour = user['agg'] + timedelta(hours=1)

        #crea messaggio formattato
        res += "<b>" + user['username'] + "</b> con <b>" + "{:,}".format(user[sort_key]).replace(",",
                                                                                                 ".") + "</b> (<i>" + \
               str(future_hour.time()).split(".")[0] + " del " + str(
            future_hour.date().strftime('%d-%m-%Y')) + "</i>)\n"

        return res


class PietreDrago:

    def __init__(self, updater, db):
        self.updater = updater
        self.db=db

        disp = updater.dispatcher

        if DEBUG:
            disp.add_handler(RegexHandler("^.* possiedi \(D\):", self.calc_val))
        else:
            calc_val_el=self.db.elegible_loot_user(self.calc_val)
            disp.add_handler(RegexHandler("^.* possiedi \(D\):", calc_val_el))


    def calc_val(self, bot, update):

        msg = update.message.text
        #compila il pattern
        regex_legno = re.compile(r"Pietra Anima di Legno \(([0-9]+)")
        regex_ferro = re.compile(r"Pietra Anima di Ferro \(([0-9]+)")
        regex_preziosa = re.compile(r"Pietra Anima Preziosa \(([0-9]+)")
        regex_diamante = re.compile(r"Pietra Cuore di Diamante \(([0-9]+)")
        regex_leggendario = re.compile(r"Pietra Cuore Leggendario \(([0-9]+)")
        regex_epico = re.compile(r"Pietra Spirito Epico \(([0-9]+)")

        #cerca dentro il messaggio
        legno = re.findall(regex_legno, msg)
        ferro = re.findall(regex_ferro, msg)
        preziosa = re.findall(regex_preziosa, msg)
        diamante = re.findall(regex_diamante, msg)
        leggendario = re.findall(regex_leggendario, msg)
        epico = re.findall(regex_epico, msg)

        #se è presente casta a int e moltiplica, altrimenti setta a zero
        if len(legno) > 0:
            legno = int(legno[0])
        else:
            legno = 0

        if len(ferro) > 0:
            ferro = int(ferro[0]) * 2
        else:
            ferro = 0

        if len(preziosa) > 0:
            preziosa = int(preziosa[0]) * 3
        else:
            preziosa = 0

        if len(diamante) > 0:
            diamante = int(diamante[0]) * 4
        else:
            diamante = 0

        if len(leggendario) > 0:
            leggendario = int(leggendario[0]) * 5
        else:
            leggendario = 0

        if len(epico) > 0:
            epico = int(epico[0]) * 6
        else:
            epico = 0

        #calcola il totale
        tot = legno + ferro + preziosa + diamante + leggendario + epico

        #setta il messaggio da inviare
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
        self.db=db
        self.inline_cat= InlineKeyboardMarkup([
            [InlineKeyboardButton("Admin", callback_data="/help admin"),
             InlineKeyboardButton("User", callback_data="/help user"),
             InlineKeyboardButton("Developer", callback_data="/help developer")],
            [InlineKeyboardButton("Inoltro", callback_data="/help inoltro"),
             InlineKeyboardButton("Crediti", callback_data="/help crediti"),
             InlineKeyboardButton("Esci", callback_data="/help esci")]

        ])

        disp = updater.dispatcher
        if DEBUG:
            disp.add_handler(CommandHandler("help", self.help_init))
        if not DEBUG:
            help_init_elegible=self.db.elegible_loot_user(self.help_init)
            disp.add_handler(CommandHandler("help", help_init_elegible))


        disp.add_handler(CallbackQueryHandler(self.help_decision, pattern="/help"))

    def get_commands_help(self):
        """Prende le funzioni e relative doc dei metodi di Command
        @:return user, admin, developer: liste contenenti nome funzioni e doc"""
        funcs = inspect.getmembers(Command, predicate=inspect.isfunction)
        admin = []
        user = []
        developer = []

        #appende in tutte le liste nomeFunzione - doc
        for elem in funcs:
            if elem[0][0] == "A":
                admin.append("/"+elem[0][1:] + "  " + elem[1].__doc__ + "\n")
            elif elem[0][0] == "U":
                user.append("/"+elem[0][1:] + "  " + elem[1].__doc__ + "\n")

            elif elem[0][0] == "D":
                developer.append("/"+elem[0][1:] + "  " + elem[1].__doc__ + "\n")

        #appende i comandi non prenseti in Command
        admin.append("/resetboss - resetta i punteggi associati agli attacchi Boss di tutti, da usare con cautela poichè una volta cancellati, "
                     "i punteggi non sono piu recuperabili")

        user.append("/attacchiBoss - Ti permette di visualizzare i punteggi di tutti i membri del team")
        user.append("/cercaCraft num1 num2 - Ti permette di cercare oggetti in base ai punti craft, rarità e "
                    "rinascita. Dato num1>num2 cerca oggetti craft con valore compreso tra num1 e num2 ")
        user.append("/compra - Ti permette di calcolare facilmente quanti scrigni comprare in base a sconti dell'"
                    "emporio e il tuo budget")
        user.append("/top - Ti permette di visualizzare la classifica dei top player in base a [pc totali, pc "
                    "settimanali, edosoldi, abilità, rango]")

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
1)<i>Titan</i> : +1 punto per chi non ha attaccato
2)<i>Phoenix</i> : +2 punti per chi non ha attaccato
3)<i>Annulla</i> : se vi siete sbagliati
Scelto il tipo di boss verranno salvati i punti dei membri non attaccanti, ovviamente chi ha piu punti si trova in pericolo di kick dal team
<b>NB</b>: Se qualcuno dei membri NON ha inviato il comando /start al bot non saranno salvati i punti del suddetto, ma verrai notificato.
Successivamente potrete scegliere 4 opzioni:
1)<i>Completa</i> : Visualizza gli utenti divisi in due categorie, attaccanti (con danno, punteggio e attacchi), non attaccanti (con punteggio e occupazione corrente (cava, missione))
2)<i>Non Attaccanti</i> : Riceverai un messaggio con gli username di quelli che non hanno attaccato
3)<i>Punteggio</i> : Una lista ordinata di username con relativi punteggi
4)<i>Sveglia</i> : Manda un messaggio per incoraggare chi non ha attaccato a farlo
5)<i>Visualizza</i> : Permentte di vedere le informazioni senza salvare il punteggio
6)<i>Annulla</i> : Per completare la fase di visualizzazione
Per resettare i punteggi usa /resetboss, però fai attenzione poichè l'operazione non è reversibile

<b>----Top----</b>
Questo comando viene attivato inoltrando il messaggio <b>Giocatore</b> da @lootgamebot
Inviando il messaggio ggiornerai il database e potrai visualizzare la tuo posizione in classifica con gli altri membri.
La classifica mostra la data di aggiornamento e i punti realtivi a:
1)Punti craft totali
2)Punti craft settimanali
3)Edosoldi
4)Abilità
5)Rango 
La visualizzazione è anche disponibile tramite il comando /top, senza aggiornamento dei valori

<b>----Pietre del Drago----</b>
Questo comando viene attivato inoltrando il messagio <b>/zaino D</b> da @lootplusbot
Otterrai il valore (in exp drago) di tutte le pietre del drago che sono presenti nel tuo zaino nei seguenti formati:
1)Punti individuali per ogni pietra
2)Punti totali
3)Avanzamento in termini di livello del drago se decidi di nutrirlo con tutte le pietre
"""

    def get_credits(self):
        return """<b>=====CREDITI=====</b>\n
Crediti: @brandimax e @Odococo e un ringraziamento speciale a @DiabolicamenteMe per avermi aiutato ❤️.
Se hai idee o suggerimenti scrivici e non tarderemo a risponderti!
Votaci sullo <a href="https://telegram.me/storebot?start=fancazzisti_bot">Storebot</a>!
"""

    def help_init(self, bot, update):
        to_send="""Benvenuto nel FancaBot! Questo bot ha diverse funzionalità per semplificare il gioco @lootgamebot
        Seleziona una categoria di comandi per imapararne l'utilizzo. Ricorda che ogni comando ha la seguente sintassi:
        nome_comando parametri - spiegazione
        Quindi ricorda di aggiungere i parametri giusti!"""
        update.message.reply_text(to_send, reply_markup=self.inline_cat)

    #todo: create multiple page help
    def help_decision(self, bot, update):
        """Visulauzza i vari help a seconda della scelta dell'user"""
        #prendi la scelta dell'user (guarda CallbackQueryHandler)
        param = update.callback_query.data.split()[1]

        user,admin,developer=self.get_commands_help()

        to_send=""
        if param=="esci":
            #elimina messaggio di scelta
            bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=update.callback_query.message.message_id
            )
            bot.sendMessage(update.callback_query.message.chat.id, "Spero di esserti stato utile!")
            return
        elif param=="admin":

            to_send+="<b>=====COMANDI ADMIN=====</b>\n\n"
            #scrive tutti i comandi
            for elem in admin:
                to_send+=elem+"\n\n"
            #dividi il messaggio a seconda della lunghezza in bytes
            to_send=text_splitter_bytes(to_send, splitter="\n\n")
            #se ci sono piu elementi manda solo il pirmo, vedi todo
            if len(to_send) > 1:
                to_send = to_send[0]
            #altrimenti usa il primo elemento
            else: to_send=to_send[0]


        elif param=="user":
            to_send+="<b>=====COMANDI USER=====</b>\n\n"

            for elem in admin:
                to_send+=elem+"\n\n"
            #dividi il messaggio a seconda della lunghezza in bytes
            to_send=text_splitter_bytes(to_send, splitter="\n\n")
            #se ci sono piu elementi manda solo il pirmo, vedi todo
            if len(to_send) > 1:
                to_send = to_send[0]
            #altrimenti usa il primo elemento
            else: to_send=to_send[0]


        elif param == "developer":
            to_send+="<b>=====COMANDI DEVELOPER=====</b>\n\n"

            for elem in admin:
                to_send+=elem+"\n\n"
            #dividi il messaggio a seconda della lunghezza in bytes
            to_send=text_splitter_bytes(to_send, splitter="\n\n")
            #se ci sono piu elementi manda solo il pirmo, vedi todo
            if len(to_send) > 1:
                to_send = to_send[0]
            #altrimenti usa il primo elemento
            else: to_send=to_send[0]

        elif param == "inoltro":
            to_send+=self.get_forward_commands()

        elif param=="crediti":
            to_send+=self.get_credits()

        #modifica il messaggio con il to_send
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=to_send,
            message_id=update.callback_query.message.message_id,
            reply_markup=self.inline_cat,
            parse_mode="HTML"

        )

