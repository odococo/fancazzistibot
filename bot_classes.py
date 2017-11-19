import operator
import re

import emoji
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, RegexHandler, MessageHandler, Filters, CommandHandler, \
    CallbackQueryHandler

import db_call
from db_call import get_user, get_users
from utils import is_numeric, is_admin, get_user_id, request_access


class Loot:
    def __init__(self, bot, dispatcher):
        self.bot = bot
        self.costo_craft = 0
        self.stima_flag = False
        self.quantita = []
        self.costo = []
        self.to_send_negozi = ""

        # adding dispatchers
        coversation = ConversationHandler(
            [RegexHandler("^Lista oggetti necessari per", self.ricerca)],
            states={
                1: [MessageHandler(Filters.text, self.stima)]
            },
            fallbacks=[CommandHandler('Annulla', self.annulla)])

        dispatcher.add_handler(coversation)
        dispatcher.add_handler(CallbackQueryHandler(self.send_negozi, pattern="^/mostraNegozi"))

    def check_user(self, id):
        db_call.execute(db_call.TABELLE["users"]["from_id"],id)


    def ricerca(self, bot, update):
        """Condensa la lista di oggetti di @craftlootbot in comodi gruppi da 3,basta inoltrare la lista di @craftlootbot"""
        user= db_call.execute(db_call.TABELLE["users"]["from_id"],id)

        if not user:
            request_access(bot, update._effective_user)
            return ConversationHandler.END
        elif user["banned"]:
            update.message.reply_text("Spiacente sei stato bannato dal bot")
            return


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

        if update.message.text == "Anulla":
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
            vifdadelem[3]= numero negozio per oggetto"""
            merged = []
            for q in self.quantita:
                c = [item for item in self.costo if item[0] == q[1]]
                if (len(c) > 0):
                    c = c[0]
                    merged.append((q[0], q[1], c[1], c[2]))

            tot = 0
            for elem in merged:
                if is_numeric(elem[0]):
                    tot += int(elem[0]) * int(elem[2])

            tot += int(self.costo_craft)

            update.message.reply_text("Secondo le stime di mercato pagherai " +
                                      "{:,}".format(tot).replace(",", "'") + "§ (costo craft incluso)")

            if (len(self.costo) > 10):
                self.costo.sort(key=lambda tup: int(tup[1]), reverse=True)

                to_print = "I 10 oggetti piu costosi sono:\n"
                for i in range(0, 9):
                    to_print += self.costo[i][0] + " : " + self.costo[i][1] + " §\n"

                update.message.reply_text(to_print)

            m, s = divmod(len(self.costo) * 10, 60)

            update.message.reply_text("Comprando gli oggetti dal negozio impiegherai un tempo di circa :\n "
                                      + str(m) + " minuti e " + str(s) + " secondi\n")

            # fixme: dividi il send negozi in parti da 30 perche l'HTML semtte di funzionare al 39-esimo
            for elem in merged:

                if int(elem[0]) > 1:
                    self.to_send_negozi += "Compra l'oggetto <b>" + elem[1] + "</b> (<b>" + str(
                        elem[0]) + "</b>) al negozio:\n<pre>@lootplusbot " + str(elem[3]) + "</pre>\n"
                else:
                    self.to_send_negozi += "Compra l'oggetto <b>" + elem[
                        1] + "</b> al negozio:\n<pre>@lootplusbot " + str(elem[3]) + "</pre>\n"

            update.message.reply_text("Vuoi visualizzare i negozi?", reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Si", callback_data="/mostraNegoziSi"),
                InlineKeyboardButton("No", callback_data="/mostraNegoziNo")
            ]]))

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
        self.to_send_negozi = ""
        update.message.reply_text("Ok ho annullato tutto", reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def send_negozi(self, bot, update):
        if "Si" in update.callback_query.data:
            if self.to_send_negozi:
                text = self.to_send_negozi
            else:
                text = "Si è verificato un errore, contatta @brandimax"
        else:
            text = "Ok"
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            text=text,
            message_id=update.callback_query.message.message_id,
            parse_mode="HTML"
        )

        self.to_send_negozi = ""

    def estrai_oggetti(self, msg):

        restante = msg.split("già possiedi")[0].split(":")[1]
        aggiornato = ""

        regex = re.compile(r"> ([0-9]+) su ([0-9]+)")
        to_loop = restante.split("\n")
        to_loop.pop(0)
        for line in to_loop:
            find = re.findall(regex, line)
            try:
                if find[0] != find[1]:
                    new_num = int(find[0]) - int(find[1])

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
        commands = []
        self.quantita = [(q[0], q[1].strip()) for q in quantita]
        last_ixd = len(lst) - len(lst) % 3
        for i in range(0, (last_ixd) - 2, 3):
            commands.append("/ricerca " + ",".join(lst[i:i + 3]))

        if last_ixd < len(lst): commands.append("/ricerca " + ",".join(lst[last_ixd:len(lst)]))

        return commands


class Boss:
    def __init__(self, bot, dispatcher):
        self.bot = bot
        self.lista_boss = []
        self.dict_boss = {}
        self.last_update_id = 0
        self.phoenix = False

        coversation_boss = ConversationHandler(
            [CommandHandler("attacchiBoss", self.boss_user), RegexHandler("^🏆", self.boss_admin)],
            states={
                1: [MessageHandler(Filters.text, self.boss_loop)]
            },
            fallbacks=[CommandHandler('Fine', self.fine)]
        )
        dispatcher.add_handler(coversation_boss)

        dispatcher.add_handler(CommandHandler("resetBoss", self.boss_reset_ask))
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
        print("Admin boss")

        # controlla se admin
        if not is_admin(get_user_id(update)):
            update.message.reply_text("Non sei autorizzato ad inoltrare questi messaggi")
            return ConversationHandler.END

        # TODO: prendi dizionario e last_update_id dal database
        # prendi il dizionario, lista  e id
        self.dict_boss = {}
        self.last_update_id = 0

        self.lista_boss = self.cerca_boss(update.message.text)

        reply_markup = ReplyKeyboardMarkup([["Phoenix", "Titan"]], one_time_keyboard=True)
        update.message.reply_text("Di quale boss stiamo parlando?",
                                  reply_markup=reply_markup)
        return 1

    def boss_user(self, bot, update):
        """Se un user vuole visualizzare le stesse info degli admin non ha diritto alle modifiche"""
        # todo if user_id not in db
        if False:
            request_access(bot, update._effective_user)
            return ConversationHandler.END

        reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Completa", "Fine"]],
                                           one_time_keyboard=False)
        update.message.reply_text("Quali info vuoi visualizzare?", reply_markup=reply_markup)
        return 1

    def boss_reset_confirm(self, bot, update):
        if "Si" in update.callback_query.data:
            self.lista_boss = []
            self.dict_boss = {}
            self.last_update_id = 0
            self.phoenix = False
            # todo: invia sul db
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
        if not is_admin(get_user_id(update)):
            update.message.reply_text("Non sei abilitato ad usare a questo comando!")
            return

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
        elif choice == "Completa" and is_admin(get_user_id(update)):
            return self.completa(bot, update)
        elif choice == "Completa" and not is_admin(get_user_id(update)):
            update.message.reply_text("Non sei abilitato ad usare questa funzione")
            return 1
        elif choice == "Fine":
            return self.fine(bot, update)

        # se l'admin vuole modificare la lista
        elif choice == "Phoenix" or choice == "Titan" and is_admin(get_user_id(update)):
            if choice == "Phoenix":
                self.phoenix = True
            else:
                self.phoenix = False
            if self.last_update_id == update.message.message_id:
                update.message.reply_text("Stai cercando di salvare lo stesso messaggio due volte!")
                return 1

            # aggiunge i membri nel dizionario se non sono gia presenti
            for elem in self.lista_boss:
                if elem[0] not in self.dict_boss.keys():
                    self.dict_boss[elem[0]] = 0
                if elem[2] == 0 and self.phoenix:
                    self.dict_boss[elem[0]] += 2
                elif elem[2] == 0 and not self.phoenix:
                    self.dict_boss[elem[0]] += 1

                self.last_update_id = update.message.message_id
                # Todo: salva dizionario e last_update in db

            reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Completa", "Fine"]],
                                               one_time_keyboard=False)
            update.message.reply_text("Dati salvati!\nAdesso fammi sapere in che formato vuoi ricevere le info",
                                      reply_markup=reply_markup)

            return 1

        else:
            # TODO: elif se manda un altro messaggio gestisci
            update.message.reply_text("Non ho capito, ripeti")
            return 1


    def punteggio(self, bot, update):
        """Visualizza la sita di tutti con punteggio annesso"""

        if not len(self.dict_boss.keys()) > 0:
            update.message.reply_text("La lista è vuota! Chiedi agli admin di aggiornarla")
            return ConversationHandler.END

        sortedD = sorted(self.dict_boss.items(), key=operator.itemgetter(1), reverse=True)

        to_send = "\n⛔️⛔️<b>Giocatori da espellere</b>⛔️⛔️\n"
        for elem in sortedD:
            if elem[1] > 3: to_send += "@" + str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

        to_send += "\n❗️❗️<b>Giocatori a rischio espulsione</b>❗️❗️️\n"
        for elem in sortedD:
            if elem[1] == 3: to_send += "@" + str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

        to_send += "\n⚠<b>️Non proprio i migliori</b>⚠️\n"
        for elem in sortedD:
            if elem[1] == 2: to_send += "@" + str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

        to_send += "\n✅<b>Buono ma non buonissimo</b>✅\n"
        for elem in sortedD:
            if elem[1] == 1: to_send += "@" + str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

        to_send += "\n🎉<b>I nostri best players</b>🎉\n"
        for elem in sortedD:
            if elem[1] == 0: to_send += "@" + str(elem[0]) + " : <b>" + str(elem[1]) + "</b>\n"

        update.message.reply_text(to_send, parse_mode="HTML")
        return 1  # 1 è l'id del boss_loop nel conversation handler


    def completa(self, bot, update):
        """Visualizza la lista completa ti tutte le info"""

        if not len(self.lista_boss) > 0:
            update.message.reply_text("Devi prima inoltrare il messaggio dei boss!")
            return ConversationHandler.END
        if not len(self.dict_boss.keys()) > 0:
            update.message.reply_text("La lista è vuota! Chiedi agli admin di aggiornarla")
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
            to_send += str(i) + ") @" + str(elem[0]) + " : il suo punteggio attuale è <b>" + str(
                self.dict_boss[elem[0]]) + "</b>"
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

        if not len(self.dict_boss.keys()) > 0:
            update.message.reply_text("La lista è vuota! Chiedi agli admin di aggiornarla")
            return ConversationHandler.END

        sortedD = sorted(self.dict_boss.items(), key=operator.itemgetter(1), reverse=True)

        to_send = ""
        for elem in sortedD:
            if (elem[1] > 0): to_send += str(elem[0]) + "\n"

        update.message.reply_text(to_send)
        return 1
