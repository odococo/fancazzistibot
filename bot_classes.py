import re

import emoji
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, RegexHandler, MessageHandler, Filters, CommandHandler, \
    CallbackQueryHandler

import db_call
from utils import is_numeric


class Loot:
    def __init__(self, updater, db):
        self.bot = updater.bot
        self.db = db

        dispatcher = updater.dispatcher

        DEBUG = True

        # adding dispatchers
        if not DEBUG:
            ricerca_decor = db.elegible_loot_user(self.ricerca)
            coversation = ConversationHandler(
                [RegexHandler("^Lista oggetti necessari per", ricerca_decor, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.stima, pass_user_data=True)]
                },
                fallbacks=[CommandHandler('Annulla', self.annulla, pass_user_data=True)])
            dispatcher.add_handler(coversation)

        else:
            coversation = ConversationHandler(
                [RegexHandler("^Lista oggetti necessari per", self.ricerca, pass_user_data=True)],
                states={
                    1: [MessageHandler(Filters.text, self.stima, pass_user_data=True)]
                },
                fallbacks=[CommandHandler('Annulla', self.annulla, pass_user_data=True)])
            dispatcher.add_handler(coversation)

        dispatcher.add_handler(CallbackQueryHandler(self.send_negozi, pattern="^/mostraNegozi", pass_user_data=True))

    def ricerca(self, bot, update, user_data):
        """Condensa la lista di oggetti di @craftlootbot in comodi gruppi da 3,basta inoltrare la lista di @craftlootbot"""

        # inizzializza i campi di user data
        user_data['costo_craft'] = 0
        user_data['stima_flag'] = False
        user_data['quantita'] = []
        user_data['costo'] = []
        user_data['to_send_negozi'] = []

        text = update.message.text.lower()
        to_send = self.estrai_oggetti(text, user_data)
        try:
            # self.costo_craft = text.split("per eseguire i craft spenderai: ")[1].split("§")[0].replace("'", "")
            user_data['costo_craft'] = text.split("per eseguire i craft spenderai: ")[1].split("§")[0].replace("'", "")
        except IndexError:
            # self.costo_craft=0
            user_data['costo_craft'] = 0

        for elem in to_send:
            update.message.reply_text(elem)
        reply_markup = ReplyKeyboardMarkup([["Annulla", "Stima"]], one_time_keyboard=True)
        update.message.reply_text("Adesso puoi inoltrarmi tutti i risultati di ricerca di @lootplusbot per "
                                  "avere il totale dei soldi da spendere. Quando hai finito premi Stima, altrimenti annulla.",
                                  reply_markup=reply_markup)
        # self.stima_flag = True
        user_data['stima_flag'] = True
        return 1

    def stima(self, bot, update, user_data):
        """ Inoltra tutte i messaggi /ricerca di @lootbotplus e digita /stima. Così otterrai il costo totale degli oggetti, la
               top 10 di quelli piu costosi e una stima del tempo che impiegherai a comprarli tutti."""

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


            if (len(user_data['costo']) > 10):
                user_data['costo'].sort(key=lambda tup: int(tup[1]), reverse=True)

                to_print = "I 10 oggetti piu costosi sono:\n"
                for i in range(0, 9):
                    to_print += user_data['costo'][i][0] + " : " + user_data['costo'][i][1] + " §\n"

                update.message.reply_text(to_print)

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

    def annulla(self, bot, update, user_data, msg=""):
        """Finisce la conversazione azzerando tutto
         msg: è il messaggio inviato all'utente
         return : fine conversazione"""

        if not msg: msg = "Ok ho annullato tutto"
        self.stima_flag = False
        self.costo_craft = 0
        self.quantita = []
        self.to_send_negozi = []

        user_data['stima_flag'] = False
        user_data['costo_craft'] = 0
        user_data['quantita'] = []

        update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def send_negozi(self, bot, update, user_data):
        addon = ""

        if "Si" in update.callback_query.data:
            # print(self.to_send_negozi)



            # if len(self.to_send_negozi) > 0 and len(self.to_send_negozi) < 31:
            #     to_change = "".join(self.to_send_negozi)
            # elif len(self.to_send_negozi) > 0:
            #     to_change = "".join(self.to_send_negozi[:29])
            #     addon = "".join(self.to_send_negozi[29:])

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

    def estrai_oggetti(self, msg, user_data):
        """Estrae gli ogetti piu quantità dal messaggio /lista dicraftlootbot:
                msg: messaggio.lower()
                return string: rappresentante una lista di /ricerca oggetto\n"""
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

                    new_line = line.replace(num[0], str(new_num))  # rimpiazzo il primo
                    new_line = new_line.replace(num[1], str(new_num))  # e il secondo
                    aggiornato += new_line + "\n"  # aggiungo la riga aggiornata
                else:
                    aggiornato += line + "\n"

            except IndexError:
                aggiornato += line + "\n"

        regex_comandi = re.compile(r"di (.*)?\(")
        regex_zaino_completo = re.compile(r"su ([0-9]) di (.*)?\(")
        regex_zaino_vuoto = re.compile(r"> ([0-9]+) di ([A-z ]+)")
        lst = re.findall(regex_comandi, aggiornato)  # per i comandi
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

    def boss_admin(self, bot, update, user_data):
        """Inoltra il messaggio del boss, solo per admin"""
        # print("Admin boss")


        # prendi il dizionario, lista  e id
        self.inizzializza_user_data(user_data)
        boss = self.db.execute(db_call.TABELLE['punteggio']['select']['all_and_users'])
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

        if self.same_message(boss, user_data['lista_boss'] ):
            update.message.reply_text("Hai gia mandato questo messaggio... il database non verrà aggiornato")
            return 1

        #print(user_data['lista_boss'], boss)

        reply_markup = ReplyKeyboardMarkup([["Phoenix", "Titan"]], one_time_keyboard=True)
        update.message.reply_text("Di quale boss stiamo parlando?",
                                  reply_markup=reply_markup)
        return 1

    def boss_user(self, bot, update, user_data):
        """Se un user vuole visualizzare le stesse info degli admin non ha diritto alle modifiche"""

        self.inizzializza_user_data(user_data)
        user_data['punteggi'] = self.db.execute(db_call.TABELLE['punteggio']['select']['all_and_users'])

        reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Completa", "Fine"]],
                                           one_time_keyboard=False)
        update.message.reply_text("Quali info vuoi visualizzare?", reply_markup=reply_markup)
        return 1

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

    def boss_reset_ask(self, bot, update):

        update.message.reply_text("Sei sicuro di voler resettare i punteggi?\nNon potrai piu recuperarli",
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton("Si", callback_data="/resetBossSi"),
                                      InlineKeyboardButton("No", callback_data="/resetBossNo")
                                  ]]))

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
                if username[0] in users_name and not bool(user_data['punteggi'].pop(
                        0)):  # se lo username è presente nella tabella users del db ma la tabella dei punteggi è vuota
                    user_data['punteggi'].append({'username': username[0],
                                                  'id': [elem[1] for elem in users_name_id if
                                                         elem[0] == username[0]].pop(0),
                                                  # aggiungo l'id associato
                                                  'valutazione': 0,
                                                  'attacchi': 0})  # aggiungo l'user alla lista
                elif username[0] in users_name and \
                        not username[0] in [elem['username'] for elem in
                                            user_data[
                                                'punteggi']]:  # se lo username è presente nella tabella users del db ma non nel dizionario (quindi non nella tabella punteggi del db)
                    user_data['punteggi'].append({'username': username[0],
                                                  'id': [elem[1] for elem in users_name_id if
                                                         elem[0] == username[0]].pop(0),
                                                  # aggiungo l'id associato
                                                  'valutazione': 0,
                                                  'attacchi': 0})  # aggiungo l'user alla lista


            else:  # altrimenti ho una lista di dizionari
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
                self.db.salva_punteggi_in_db(user_data['punteggi'])

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

        else:
            # print(choice)
            update.message.reply_text("Non ho capito")
            return self.fine(bot, update, user_data, msg="Non ho capito, annullo tuttto")

    def punteggio(self, bot, update, user_data):
        """Visualizza la sita di tutti con punteggio annesso"""

        if not user_data['punteggi']:
            return self.fine(bot, update, user_data, "La lista è vuota! Chiedi agli admin di aggiornarla")

        # sortedD = sorted([(elem['username'], elem['valutazione']) for elem in self.punteggi], reverse=True)
        sortedD = sorted([(elem['username'], elem['valutazione']) for elem in user_data['punteggi']], reverse=True)

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

    def fine(self, bot, update, user_data, msg=""):
        if not msg: msg="Fine"
        update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        user_data['lista_boss'] = []
        return ConversationHandler.END

    def non_attaccanti(self, bot, update, user_data):
        """Visualizza solo la lista di chi non ha ancora attaccato"""

        if not len(user_data['punteggi']) > 0:
            return self.fine(bot, update, user_data, "La lista è vuota! Chiedi agli admin di aggiornarla")

        to_send = ""

        for elem in [(elem['attacchi'], elem['username']) for elem in user_data['punteggi']]:
            if (elem[0] == 0): to_send += str(elem[1]) + "\n"

        if not to_send: to_send = "Hanno attaccato tutti!"

        update.message.reply_text(to_send)
        return 1

    def same_message(self, boss_db, boss_admin):
        if isinstance(boss_db, list):
            for db in boss_db:
                for admin in boss_admin:
                    if db['username'] == admin[0]:
                        if isinstance(admin[2], tuple) and not admin[2][1] == db['attacchi']:
                            return True
                        elif admin[2] == 0 and db['attacchi'] == 0:
                            return True

        else:
            for admin in boss_admin:
                if admin[0] == boss_db['username']:
                    if isinstance(admin[2], tuple) and not admin[2][1] == boss_db['attacchi']:
                        return True
                    elif admin[2] == 0 and boss_db['attacchi'] == 0:
                        return True

        return False


class Cerca:
    def __init__(self, updater, db, oggetti):
        self.bot = updater.bot
        self.db = db
        self.oggetti = oggetti
        self.craftabili = [elem for elem in oggetti if not elem['craft_pnt'] == 0]
        self.maggioreDi = -1
        self.minoreDi = 3000
        self.rarita = ""
        self.rinascita = ""
        self.risultati = []

        dispatcher = updater.dispatcher

        cerca_craft_el = db.elegible_loot_user(self.cerca_craft)

        dispatcher.add_handler(CommandHandler("cercacraft", cerca_craft_el, pass_user_data=True))
        dispatcher.add_handler(CallbackQueryHandler(self.filtra_rarita, pattern="/rarita", pass_user_data=True))
        dispatcher.add_handler(CallbackQueryHandler(self.filtra_rinascita, pattern="/rinascita", pass_user_data=True))
        dispatcher.add_handler(CallbackQueryHandler(self.ordina, pattern="/ordina", pass_user_data=True))

    def inizzializza_user_data(self, user_data):
        user_data['maggioreDi'] = -1
        user_data['minoreDi'] = 3000
        user_data['rarita'] = ""
        user_data['risultati'] = []

    def cerca_craft(self, bot, update, user_data):
        """/cercaCraft num1 num2 - Ti permette di cercare oggetti in base ai punti craft, rarità e rinascita. Dato
        num1>num2 cerca oggetti craft con valore compreso tra num1 e num2."""
        param = update.message.text.split()[1:]
        self.inizzializza_user_data(user_data)

        magg = 0
        min = 0

        if len(param) == 0 or len(param) > 2:
            update.message.reply_text("Il comando deve essere usato in due modi:\n"
                                      "/cercaCraft maggioreDi minoreDi\n"
                                      "/cercaCraft maggioreDi\nIn cui maggioreDi e minoreDi sono due numeri rappresentanti"
                                      " l'intervallo di punti craft in cui vuoi cercare.")
            return


        elif len(param) == 1 and is_numeric(param[0]):
            user_data['maggioreDi'] = int(param[0])
        elif len(param) == 2 and is_numeric(param[0]) and is_numeric(param[1]):
            magg = int(param[0])
            min = int(param[1])
        else:
            update.message.reply_text("Non hai inviato dei numeri corretti")
            return

        if magg > min:
            update.message.reply_text("Il numero maggioreDi non può essere minore del numero minoreDi")
            return
        user_data['maggioreDi'] = magg
        user_data['minoreDi'] = min

        inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("X", callback_data="/rarita X"),
             InlineKeyboardButton("UE", callback_data="/rarita UE"),
             InlineKeyboardButton("E", callback_data="/rarita E")],
            [InlineKeyboardButton("L", callback_data="/rarita L"), InlineKeyboardButton("U", callback_data="/rarita U"),
             InlineKeyboardButton("UR", callback_data="/rarita UR")],
            [InlineKeyboardButton("Tutti", callback_data="/rarita tutti")]
        ])

        update.message.reply_text("Secondo quale rarità vuoi filtrare il risultato?", reply_markup=inline)

    def filtra_rarita(self, bot, update, user_data):
        user_data['rarita'] = update.callback_query.data.split()[1]

        inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("r0", callback_data="/rinascita 1"),
             InlineKeyboardButton("r1", callback_data="/rinascita 2"),
             InlineKeyboardButton("r2", callback_data="/rinascita 3")]

        ])

        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text="Perfetto, ora dimmi a quale rinascita sei interessato, ricorda che i risultati mostrati saranno quelli"
                 " per tutte le rinascite minori uguali a quella che hai selzionato.\nEsempio scegli r2, ti verranno mostrati i "
                 "risultati per r0, r1 e r2\n",
            message_id=update.callback_query.message.message_id,
            reply_markup=inline
        )

    def filtra_rinascita(self, bot, update, user_data):
        rinascita = update.callback_query.data.split()[1]

        # print(self.maggioreDi, self.minoreDi, self.rarita, self.rinascita)
        if not "tutti" in user_data['rarita']:
            user_data['risultati'] = [elem for elem in self.craftabili if
                                      elem['craft_pnt'] > user_data['maggioreDi'] and
                                      elem['craft_pnt'] < user_data['minoreDi'] and elem['reborn'] <= int(rinascita)
                                      and elem['rarity'] == user_data['rarita']]
        else:

            user_data['risultati'] = [elem for elem in self.craftabili if
                                      elem['craft_pnt'] > user_data['maggioreDi'] and
                                      elem['craft_pnt'] < user_data['minoreDi'] and elem['reborn'] <= int(rinascita)]

        if len(user_data['risultati']) == 0:
            bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                text="Non ho trovato risultati per i tuoi criteri di ricerca",
                message_id=update.callback_query.message.message_id,
            )
            return

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

    def ordina(self, bot, update, user_data):
        param = update.callback_query.data.split()[1]
        to_send = ""
        sorted_res = []
        to_send=[]

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
            to_send.append( "<b>" + elem['name'] + "</b>   " + str(elem['craft_pnt']) + "   " + elem['rarity'] + "   " + str(
                elem["reborn"]) + "\n")

        bot.delete_message(
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id
        )

        while to_send:
            bot.sendMessage(message_id, "".join(to_send[:30]), parse_mode="HTML")
            to_send = to_send[30:]

        self.inizzializza_user_data(user_data)
