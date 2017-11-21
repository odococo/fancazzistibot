import re

import emoji
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, RegexHandler, MessageHandler, Filters, CommandHandler, \
    CallbackQueryHandler

import db_call
from utils import is_numeric


class Loot:
    def __init__(self, bot, dispatcher, db):
        self.bot = bot
        self.db = db
        self.costo_craft = 0
        self.stima_flag = False
        self.quantita = []
        self.costo = []
        self.to_send_negozi = []

        DEBUG=False

        # adding dispatchers
        if not DEBUG:
            ricerca_decor = db.elegible_user(self.ricerca)
            coversation = ConversationHandler(
            [RegexHandler("^Lista oggetti necessari per", ricerca_decor)],
            states={
                1: [MessageHandler(Filters.text, self.stima)]
            },
            fallbacks=[CommandHandler('Annulla', self.annulla)])
            dispatcher.add_handler(coversation)

        else:
            coversation = ConversationHandler(
            [RegexHandler("^Lista oggetti necessari per", self.ricerca)],
            states={
                1: [MessageHandler(Filters.text, self.stima)]
            },
            fallbacks=[CommandHandler('Annulla', self.annulla)])
            dispatcher.add_handler(coversation)

        dispatcher.add_handler(CallbackQueryHandler(self.send_negozi, pattern="^/mostraNegozi"))

    def ricerca(self, bot, update):
        """Condensa la lista di oggetti di @craftlootbot in comodi gruppi da 3,basta inoltrare la lista di @craftlootbot"""

        text = update.message.text.lower()
        to_send = self.estrai_oggetti(text)
        self.costo_craft = text.split("per eseguire i craft spenderai: ")[1].split("§")[0].replace("'", "")

        for elem in to_send:
            update.message.reply_text(elem)
        reply_markup = ReplyKeyboardMarkup([["Annulla", "Stima"]], one_time_keyboard=True)
        update.message.reply_text("Adesso puoi inoltrarmi tutti i risultati di ricerca di @lootplusbot per "
                                  "avere il totale dei soldi da spendere. Quando hai finito premi Stima, altrimenti annulla.",
                                  reply_markup=reply_markup)
        self.stima_flag = True
        return 1

    def stima(self, bot, update):
        """ Inoltra tutte i messaggi /ricerca di @lootbotplus e digita /stima. Così otterrai il costo totale degli oggetti, la
               top 10 di quelli piu costosi e una stima del tempo che impiegherai a comprarli tutti."""

        if update.message.text == "Annulla":
            return self.annulla(bot, update)
        elif update.message.text == "Stima":
            if not self.stima_flag:
                update.message.reply_text(
                    "Per usare questo comando devi aver prima inoltrato la lista di @craftlootbot!")
                return 1

            if len(self.costo) == 0:
                update.message.reply_text("Non hai inoltrato nessun messaggio da @lootbotplus")
                return self.annulla(bot, update)

            """"merged è una lista di quadruple con i seguenti elementi:
            elem[0]= quantità oggetto
            elem[1]= nome oggetto
            elem[2]= costo oggetto
            elem[3]= numero negozio per oggetto"""
            merged = []
            for q in self.quantita:
                c = [item for item in self.costo if item[0] == q[1]]
                if (len(c) > 0):
                    c = c[0]
                    merged.append((q[0], q[1], c[1], c[2]))

        #    print(merged, self.quantita, self.costo)

            tot = 0
            tempo=0
            for elem in merged:
                if is_numeric(elem[0]):
                    tot += int(elem[0]) * int(elem[2])
                    tempo+=10+3*int(elem[0])

            tot += int(self.costo_craft)

            update.message.reply_text("Secondo le stime di mercato pagherai " +
                                      "{:,}".format(tot).replace(",", "'") + "§ (costo craft incluso)",reply_markup=ReplyKeyboardRemove())

            if (len(self.costo) > 10):
                self.costo.sort(key=lambda tup: int(tup[1]), reverse=True)

                to_print = "I 10 oggetti piu costosi sono:\n"
                for i in range(0, 9):
                    to_print += self.costo[i][0] + " : " + self.costo[i][1] + " §\n"

                update.message.reply_text(to_print)

            m, s = divmod(tempo, 60)

            update.message.reply_text("Comprando gli oggetti dal negozio impiegherai un tempo di circa :\n "
                                      + str(m) + " minuti e " + str(s) + " secondi\n")

            for elem in merged:

                if int(elem[0]) > 1:
                    self.to_send_negozi.append("Compra l'oggetto <b>" + elem[1] + "</b> (<b>" + str(
                        elem[0]) + "</b>) al negozio:\n<pre>@lootplusbot " + str(elem[3]) + "</pre>\n")
                else:
                    self.to_send_negozi.append("Compra l'oggetto <b>" + elem[
                        1] + "</b> al negozio:\n<pre>@lootplusbot " + str(elem[3]) + "</pre>\n")

            update.message.reply_text("Vuoi visualizzare i negozi?", reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Si", callback_data="/mostraNegoziSi"),
                InlineKeyboardButton("No", callback_data="/mostraNegoziNo")
            ]]))
            #print(self.to_send_negozi)

            self.costo.clear()
            self.quantita.clear()
            self.stima_flag = False
            return ConversationHandler.END
        else:
            self.stima_parziale(update.message.text.lower())
            return 1

    def stima_parziale(self, msg):
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

            self.costo.append((e[0][0], e[0][1].replace(".", "").replace(" ", ""), neg[0]))

    def annulla(self, bot, update):
        """Annulla la stima"""

        self.stima_flag = False
        self.costo_craft = 0
        self.quantita = []
        self.to_send_negozi = []
        update.message.reply_text("Ok ho annullato tutto", reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def send_negozi(self, bot, update):
        addon = ""

        if "Si" in update.callback_query.data:
            print(self.to_send_negozi)

            if len(self.to_send_negozi) > 0 and len(self.to_send_negozi) < 31:
                to_change = "".join(self.to_send_negozi)
            elif len(self.to_send_negozi) > 0:
                to_change = "".join(self.to_send_negozi[:29])
                addon = "".join(self.to_send_negozi[29:])

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

        self.to_send_negozi = []

    def estrai_oggetti(self, msg):

        restante = msg.split("già possiedi")[0].split(":")[1]
        aggiornato = ""

        regex = re.compile(r"> ([0-9]+) su ([0-9]+)")
        to_loop = restante.split("\n")
        to_loop.pop(0)
        to_loop=list(filter(None, to_loop))
        for line in to_loop:
            find = re.findall(regex, line)[0]
            try:
                if find[0] != find[1]:
                    new_num = int(find[1]) - int(find[0])

                    new_line = line.replace(find[0], str(new_num))
                    new_line = new_line.replace(find[1], str(new_num))
                    aggiornato += new_line + "\n"
                else:
                    aggiornato += line + "\n"

            except IndexError:
                aggiornato += line + "\n"

        regex = re.compile(r"di (.*)?\(")
        regex2 = re.compile(r"su ([0-9]) di (.*)?\(")
        lst = re.findall(regex, aggiornato)
        quantita = re.findall(regex2, aggiornato)
        if not quantita: quantita = re.findall(r"> ([0-9]+) di ([A-z ]+)",
                                               aggiornato)  # se cerchi con lo zaino vuoto cambia il messaggio
        commands = []
        self.quantita = [(q[0], q[1].rstrip()) for q in quantita]
        last_ixd = len(lst) - len(lst) % 3
        for i in range(0, (last_ixd) - 2, 3):
            commands.append("/ricerca " + ",".join(lst[i:i + 3]))

        if last_ixd < len(lst): commands.append("/ricerca " + ",".join(lst[last_ixd:len(lst)]))

        return commands


class Boss:
    def __init__(self, bot, dispatcher, db):
        """Questa classe è utilizzate per gestire gli attacchi al boss, i parametri sono:
        bot : bot dell'updater
        dispatcher: sempre dell'updater
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
        self.bot = bot
        self.db = db
        self.lista_boss = []
        self.punteggi = []
        self.last_update_id = 0
        self.phoenix = False
        self.single_dict = True

        boss_user_decor = db.elegible_user(self.boss_user)
        boss_admin_decor = db.elegible_admin(self.boss_admin)
        reset_boss_ask_decor = db.elegible_admin(self.boss_reset_ask)

        coversation_boss = ConversationHandler(
            [CommandHandler("attacchiBoss", boss_user_decor), RegexHandler("^🏆", boss_admin_decor)],
            states={
                1: [MessageHandler(Filters.text, self.boss_loop)]
            },
            fallbacks=[CommandHandler('Fine', self.fine)]
        )
        dispatcher.add_handler(coversation_boss)

        dispatcher.add_handler(CommandHandler("resetBoss", reset_boss_ask_decor))
        dispatcher.add_handler(CallbackQueryHandler(self.boss_reset_confirm, pattern="^/resetBoss"))

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

    def boss_admin(self, bot, update):
        """Inoltra il messaggio del boss, solo per admin"""
        # print("Admin boss")


        # prendi il dizionario, lista  e id
        boss = self.db.execute(db_call.TABELLE['punteggio']['select']['all_and_users'])
        if not boss:
            boss = {}
            id = 0
        else:
            try:
                id = boss[0]["msg_id"]
                self.single_dict = False
            except KeyError:
                id = boss["msg_id"]

        self.punteggi = boss
        self.last_update_id = id

        self.lista_boss = self.cerca_boss(update.message.text)

        reply_markup = ReplyKeyboardMarkup([["Phoenix", "Titan"]], one_time_keyboard=True)
        update.message.reply_text("Di quale boss stiamo parlando?",
                                  reply_markup=reply_markup)
        return 1

    def boss_user(self, bot, update):
        """Se un user vuole visualizzare le stesse info degli admin non ha diritto alle modifiche"""

        self.punteggi = self.db.execute(db_call.TABELLE['punteggio']['select']['all_and_users'])

        reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Completa", "Fine"]],
                                           one_time_keyboard=False)
        update.message.reply_text("Quali info vuoi visualizzare?", reply_markup=reply_markup)
        return 1

    def boss_reset_confirm(self, bot, update):
        if "Si" in update.callback_query.data:
            self.lista_boss = []
            self.punteggi = {}
            self.last_update_id = 0
            self.phoenix = False
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

    def boss_loop(self, bot, update):
        """Funzione di loop dove ogni methodo , tranne fine, ritorna dopo aver inviato il messaggio"""

        choice = update.message.text
        if choice == "Non Attaccanti":
            return self.non_attaccanti(bot, update)
        elif choice == "Punteggio":
            return self.punteggio(bot, update)
        elif choice == "Completa":
            return self.completa(bot, update)
        elif choice == "Fine":
            return self.fine(bot, update)

        # se l'admin vuole modificare la lista
        elif choice == "Phoenix" or choice == "Titan":
            if choice == "Phoenix":
                self.phoenix = True
            else:
                self.phoenix = False

            # todo: trova un'equivalente di id che non cambia ongi volta che rinvii lo stesso messaggio

            if self.last_update_id == update.message.message_id:
                update.message.reply_text("Stai cercando di salvare lo stesso messaggio due volte!")
                return 1
            else:
                self.last_update_id = update.message.message_id

            # aggiunge i membri nel dizionario se non sono gia presenti
            skipped = []
            # print(self.lista_boss)
            users = self.db.get_users()
            users_name = [elem["username"] for elem in users]
            users_name_id = [(elem["username"], elem['id']) for elem in users]

            if self.single_dict: self.punteggi = [
                self.punteggi]  # se ho un solo dizionario ne creo una lista per far funzionare il cilo successivo

            print(self.punteggi)
            for username in self.lista_boss:
                if username[0] in users_name and not bool(self.punteggi.pop(
                        0)):  # se lo username è presente nella tabella users del db ma la tabella dei punteggi è vuota
                    self.punteggi.append({'username': username[0],
                                          'id': [elem[1] for elem in users_name_id if elem[0] == username[0]].pop(0),
                                          # aggiungo l'id associato
                                          'valutazione': 0,
                                          'attacchi': 0})  # aggiungo l'user alla lista
                elif username[0] in users_name and \
                        not username[0] in [elem['username'] for elem in
                                            self.punteggi]:  # se lo username è presente nella tabella users del db ma non nel dizionario (quindi non nella tabella punteggi del db)
                    self.punteggi.append({'username': username[0],
                                          'id': [elem[1] for elem in users_name_id if elem[0] == username[0]].pop(0),
                                          # aggiungo l'id associato
                                          'valutazione': 0,
                                          'attacchi': 0})  # aggiungo l'user alla lista


            else:  # altrimenti ho una lista di dizionari
                found = False

                for username in self.lista_boss:
                    for single_dict in self.punteggi:
                        if single_dict['username'] == username[0]:  # se è gia presente nel db
                            found = True
                            single_dict['msg_id'] = self.last_update_id
                            if self.phoenix and isinstance(username[2], int):  # non ha attaccato ed è phoenix
                                single_dict['valutazione'] += 2
                            elif not self.phoenix and isinstance(username[2], int):  # non ha attaccato ed è titan
                                single_dict['valutazione'] += 1
                            elif isinstance(username[2], tuple):  # ha attaccato
                                single_dict['attacchi'] = username[2][1]
                    if not found:
                        skipped.append(username)
                    found = False

            # print(self.punteggi, self.single_dict)
            if not len(skipped) == len(self.lista_boss):  # se non ho saltato tutti gli username
                self.db.salva_punteggi_in_db(self.punteggi)

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
            return self.fine(bot, update)

    def punteggio(self, bot, update):
        """Visualizza la sita di tutti con punteggio annesso"""

        if not self.punteggi:
            update.message.reply_text("La lista è vuota! Chiedi agli admin di aggiornarla")
            return ConversationHandler.END

        sortedD = sorted([(elem['username'], elem['valutazione']) for elem in self.punteggi], reverse=True)
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

    def completa(self, bot, update):
        """Visualizza la lista completa ti tutte le info"""

        if not len(self.lista_boss) > 0:
            update.message.reply_text("Devi prima inoltrare il messaggio dei boss!")
            return ConversationHandler.END

        to_send = "✅ <b>Hanno attaccato</b>:\n"

        attaccato = sorted([elem for elem in self.lista_boss if elem[2] != 0], key=lambda tup: int(tup[2][0]),
                           reverse=True)
        non_attaccato = [elem for elem in self.lista_boss if elem[2] == 0]

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
                                                                                                      '\'') + "</b> danno a <b>" + str(
                elem[2][1]) + "</b> boss\n"
            i += 1

        to_send += "\n❌ <b>Non hanno attaccato</b>:\n"

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

    def fine(self, bot, update):
        update.message.reply_text("Finito", reply_markup=ReplyKeyboardRemove())
        self.lista_boss = []
        return ConversationHandler.END

    def non_attaccanti(self, bot, update):
        """Visualizza solo la lista di chi non ha ancora attaccato"""

        if not len(self.punteggi) > 0:
            update.message.reply_text("La lista è vuota! Chiedi agli admin di aggiornarla")
            return ConversationHandler.END

        to_send = ""
        for elem in [(elem['attacchi'], elem['username']) for elem in self.punteggi]:
            if (elem[0] == 0): to_send += str(elem[1]) + "\n"

        update.message.reply_text(to_send)
        return 1
