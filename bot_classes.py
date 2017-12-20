import math
import random
import re
from collections import OrderedDict, Counter

import emoji
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, RegexHandler, MessageHandler, Filters, CommandHandler, \
    CallbackQueryHandler
from utils import is_numeric, catch_exception

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
            to_send = "/negozi "
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

        try :
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
            print("Non ho trovato rarità")
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

        dispatcher = updater.dispatcher

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
        dispatcher.add_handler(
            CallbackQueryHandler(self.boss_reset_confirm, pattern="^/resetBoss", pass_user_data=True))

    def cerca_boss(self, msg):
        """Dato il messaggio di attacco ai boss ritorna una lista di liste con elementi nel seguente ordine:\n
        lista[0]: nome \n
        lista[1]: Missione/cava + tempo se in missione o cava, 1 altrimenti\n
        lista[2]: 0 se non c'è stato attacco al boss, tupla altrimenti: tupla[0] danno, tupla[1] numero di boss"""
        prova = msg.split("Attività membri:\n")[1]
        prova = emoji.demojize(prova)
        name_reg1 = re.compile(r"([0-z_]+) :")
        name_reg2 = re.compile(r"^([0-z_]+) .*")
        obl_reg = re.compile(r":per.*: ([0-z /(/)]+)")
        boss_reg = re.compile(r":boar: ([0-9]+) .*/([0-9])")

        res = []

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
        """Inoltra il messaggio del boss, solo per admin"""
        # print("Admin boss")

        # prendi il dizionario, lista  e id
        self.inizzializza_user_data(user_data)
        boss = self.db.get_punteggi_username()
        if not boss:
            boss = {}
            id = 0
        else:
            try:
                id = boss[0]["msg_id"]
                user_data['single_dict'] = False
            except KeyError:
                id = boss["msg_id"]

        user_data['punteggi'] = boss
        user_data['last_update_id'] = id

        user_data['lista_boss'] = self.cerca_boss(update.message.text)

        if self.same_message(boss, user_data['lista_boss']):
            update.message.reply_text("Hai gia mandato questo messaggio... il database non verrà aggiornato")
            return 1

        # print(user_data['lista_boss'], boss)

        reply_markup = ReplyKeyboardMarkup([["Phoenix", "Titan","Annulla"]], one_time_keyboard=True)
        update.message.reply_text("Di quale boss stiamo parlando?",
                                  reply_markup=reply_markup)
        return 1

    @catch_exception
    def boss_user(self, bot, update, user_data):
        """Se un user vuole visualizzare le stesse info degli admin non ha diritto alle modifiche"""

        self.inizzializza_user_data(user_data)
        user_data['punteggi'] = self.db.get_punteggi_username()

        reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Completa", "Fine"]],
                                           one_time_keyboard=False)
        update.message.reply_text("Quali info vuoi visualizzare?", reply_markup=reply_markup)
        return 1

    @catch_exception
    def boss_reset_confirm(self, bot, update, user_data):
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

            if user_data['single_dict']: user_data['punteggi'] = [user_data[
                                                                      'punteggi']]  # se ho un solo dizionario ne creo una lista per far funzionare il cilo successivo

            for username in user_data['lista_boss']:
                if username[0] in users_name and not bool(user_data['punteggi'][
                                                              0]):  # se lo username è presente nella tabella users del db ma la tabella dei punteggi è vuota
                    user_data['punteggi'].append({'username': username[0],
                                                  'id': [elem[1] for elem in users_name_id if
                                                         elem[0] == username[0]].pop(0),
                                                  # aggiungo l'id associato
                                                  'valutazione': 0,
                                                  'attacchi': 0})  # aggiungo l'user alla lista
                elif username[0] in users_name and \
                        not username[0] in [elem['username'] for elem in user_data[
                            'punteggi']]:  # se lo username è presente nella tabella users del db ma non nel dizionario (quindi non nella tabella punteggi del db)
                    user_data['punteggi'].append({'username': username[0],
                                                  'id': [elem[1] for elem in users_name_id if
                                                         elem[0] == username[0]].pop(0),
                                                  # aggiungo l'id associato
                                                  'valutazione': 0,
                                                  'attacchi': 0})  # aggiungo l'user alla lista

            print(user_data)
            found = False

            for username in user_data['lista_boss']:
                for single_dict in user_data['punteggi']:
                    if single_dict['username'] == username[0]:  # se è gia presente nel db
                        found = True
                        single_dict['msg_id'] = user_data['last_update_id']
                        if user_data['phoenix'] and isinstance(username[2], int):  # non ha attaccato ed è phoenix
                            single_dict['valutazione'] += 2
                        elif not user_data['phoenix'] and isinstance(username[2],
                                                                     int):  # non ha attaccato ed è titan
                            single_dict['valutazione'] += 1
                        elif isinstance(username[2], tuple):  # ha attaccato
                            single_dict['attacchi'] = username[2][1]
                if not found:
                    skipped.append(username)
                found = False

            if not len(skipped) == len(user_data['lista_boss']):  # se non ho saltato tutti gli username
                self.db.update_punteggi(user_data['punteggi'])

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

        elif choice =="Annulla": return self.fine(bot, update, user_data, "Ok")

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
            to_send += "@" + str(elem[0]) + " : facendo <b>" + '{:,}'.format(int(elem[2][0])).replace(',',
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
        if not isinstance(boss_db, list):
            boss_db = [boss_db]  # rende boss_db una lista
        elif not boss_db:
            return False
        users_db = self.db.get_users()
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
        """/cercaCraft num1 num2 - Ti permette di cercare oggetti in base ai punti craft, rarità e rinascita. Dato
        num1>num2 cerca oggetti craft con valore compreso tra num1 e num2."""
        param = update.message.text.split()[1:]
        self.inizzializza_user_data(user_data)

        if len(param) == 0 or len(param) > 2:
            update.message.reply_text("Il comando deve essere usato in due modi:\n"
                                      "/cercaCcraft maggioreDi minoreDi\n"
                                      "/cercaCraft maggioreDi\nIn cui maggioreDi e minoreDi sono due numeri rappresentanti"
                                      " l'intervallo di punti craft in cui vuoi cercare.")
            return


        elif len(param) == 1 and is_numeric(param[0]):
            user_data['risultati'] = [elem for elem in self.craftabili if elem['craft_pnt'] >= int(param[0])]
        elif len(param) == 2 and is_numeric(param[0]) and is_numeric(param[1]):
            magg = int(param[0])
            min = int(param[1])
            print(magg, min)
            if magg > min:
                update.message.reply_text("Il numero maggioreDi non può essere minore del numero minoreDi")
                return
            user_data['risultati'] = [elem for elem in self.craftabili if elem['craft_pnt'] >= magg and
                                      elem['craft_pnt'] <= min]

        else:
            update.message.reply_text("Non hai inviato dei numeri corretti")
            return

        num_ris = len(user_data['risultati'])
        if num_ris == 0: return self.no_results(bot, update)

        inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("X", callback_data="/rarita X"),
             InlineKeyboardButton("UE", callback_data="/rarita UE"),
             InlineKeyboardButton("E", callback_data="/rarita E")],
            [InlineKeyboardButton("L", callback_data="/rarita L"), InlineKeyboardButton("U", callback_data="/rarita U"),
             InlineKeyboardButton("UR", callback_data="/rarita UR")],
            [InlineKeyboardButton("Tutti", callback_data="/rarita tutti")]
        ])

        text = "Ho trovato <b>" + str(num_ris) + "</b> oggetti che rispettano i tuoi parametri\n"

        update.message.reply_text(text +
                                  "Secondo quale rarità vuoi filtrare?", reply_markup=inline, parse_mode="HTML"
                                  )

    @catch_exception
    def filtra_rarita(self, bot, update, user_data):
        # todo: prova a far scegliere piu rarità
        user_data['rarita'] = update.callback_query.data.split()[1]
        rarita = update.callback_query.data.split()[1]
        if not "tutti" in rarita:
            user_data['risultati'] = [elem for elem in user_data['risultati'] if elem['rarity'] == rarita]

        num_ris = len(user_data['risultati'])
        if num_ris == 0: return self.no_results(bot, update)

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
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text="Non ho trovato risultati per i tuoi criteri di ricerca",
            message_id=update.callback_query.message.message_id,
        )
        return

    @catch_exception
    def filtra_rinascita(self, bot, update, user_data):
        rinascita = update.callback_query.data.split()[1]

        # print(self.maggioreDi, self.minoreDi, self.rarita, self.rinascita)
        user_data['risultati'] = [elem for elem in user_data['risultati'] if elem['reborn'] <= int(rinascita)]

        if len(user_data['risultati']) == 0: return self.no_results(bot, update)

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
        param = update.callback_query.data.split()[1]
        to_send = ""
        sorted_res = []
        to_send = []

        if "annulla" in param:
            to_send.append("Ok annullo")

        elif "puntiCraft" in param:
            sorted_res = sorted(user_data['risultati'], key=lambda key: key["craft_pnt"])
        elif "rarita" in param:
            sorted_res = sorted(user_data['risultati'], key=lambda key: key["rarity"])
        elif "rinascita" in param:
            sorted_res = sorted(user_data['risultati'], key=lambda key: key["reborn"])

        message_id = update._effective_chat.id

        if sorted_res:
            bot.sendMessage(message_id, "<b>Nome   Punti Craft    Rarità     Rinascita</b>\n", parse_mode="HTML")

        for elem in sorted_res:
            to_send.append(
                "<b>" + elem['name'] + "</b>   " + str(elem['craft_pnt']) + "   " + elem['rarity'] + "   " + str(
                    elem["reborn"]) + "\n")

        bot.delete_message(
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id
        )

        while to_send:
            bot.sendMessage(message_id, "".join(to_send[:30]), parse_mode="HTML")
            to_send = to_send[30:]

        self.inizzializza_user_data(user_data)


class Compra:

    def __init__(self, updater, db):
        self.db = db
        self.scrigni = OrderedDict(
            [('Legno', 600), ('Ferro', 1200), ('Prezioso', 2400), ('Diamante', 3600), ('Leggendario', 7000),
             ('Epico', 15000)])

        disp = updater.dispatcher

        if not DEBUG:
            eleg = self.db.elegible_loot_user(self.sconti)
            disp.add_handler(CommandHandler("compra", eleg, pass_user_data=True))

        else:
            disp.add_handler(CommandHandler("compra", self.sconti, pass_user_data=True))

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
        user_data['sconto'] = 0
        user_data['budget'] = 0
        return ConversationHandler.END

    def sconti(self, bot, update, user_data):

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
        user_data['sconto'] = update.callback_query.data.split()[1]

        text = "Qual'è il tuo budget? (inviami un numero)"

        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=text,
            message_id=update.callback_query.message.message_id,

        )

        return 1

    def budget_save(self, bot, update, user_data):

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
        param = update.message.text.split(" ")

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

        for elem in res.keys():

            if res[elem]: text += "Compra <b>" + str(res[elem]) + "</b> di Scrigno " + elem + "\n"

        if not text: text="Si è verificato un errore...contatta @brandimax"

        update.message.reply_text(text, parse_mode="HTML")
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


class Constes:

    def __init__(self, updater):
        self.updater = updater
        self.contest_flag=False
        self.contest_creator=False


        disp = updater.dispatcher

class Top:

    def __init__(self, updater, db):
        self.updater = updater
        self.db=db

        disp = updater.dispatcher
        #todo: add permission decor
        disp.add_handler(RegexHandler("^Giocatore", self.add_player))
        disp.add_handler(CommandHandler("top",self.get_player))


    def add_player(self, bot,update):

        #getting demojized message
        msg=update.message.text
        msg=emoji.demojize(msg)

        #compaling regex
        pc_regex = re.compile(r":package: ([0-9.]+) \(([0-9.]+)")
        money_regex = re.compile(r":money_bag: ([0-9.]+)")
        abilita_regex = re.compile(r"Abilità: ([0-9]+)")
        rango_regex = re.compile(r"Rango: [A-z ]+ \(([0-9]+)")

        #getting values
        pc_tot=re.findall(pc_regex,msg)[0][0].replace(".","")
        pc_set=re.findall(pc_regex,msg)[0][1].replace(".","")
        money=re.findall(money_regex,msg)[0].replace(".","")
        ability=re.findall(abilita_regex,msg)[0].replace(".","")
        rango=re.findall(rango_regex,msg)[0].replace(".","")

        #updating to db
        self.db.add_update_top_user( pc_tot , pc_set,  money,  ability,  rango,  update.message.from_user.id)

        update.message.reply_text("Sei stato aggiunto correttamente, utilizza il comando /top per vedere la classifica")




    def get_player(self, bot, update):
        players=self.db.get_all_top()
        print(players)