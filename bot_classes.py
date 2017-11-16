import re
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, RegexHandler, MessageHandler, Filters, CommandHandler, \
    CallbackQueryHandler

from utils import is_numeric


class Loot:

    def __init__(self, bot, dispatcher):
        self.bot=bot
        self.costo_craft=0
        self.stima_flag=False
        self.quantita=[]
        self.costo=[]
        self.to_send_negozi=""

        #adding dispatchers
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
        reply_markup = ReplyKeyboardMarkup([["Anulla", "Stima"]], one_time_keyboard=True)
        update.message.reply_text("Adesso puoi inoltrarmi tutti i risultati di ricerca di @lootplusbot per "
                                  "avere il totale dei soldi da spendere. Quando hai finito premi Stima, altrimenti annulla.",
                                  reply_markup=reply_markup)
        self.stima_flag = True
        return 1

    def stima(self, bot, update):
        """ Inoltra tutte i messaggi /ricerca di @lootbotplus e digita /stima. Così otterrai il costo totale degli oggetti, la
               top 10 di quelli piu costosi e una stima del tempo che impiegherai a comprarli tutti."""

        if update.message.text == "Anulla":
            update.message.reply_text("Ok ho annullato tutto")
            return self.annulla(bot, update)
        elif update.message.text == "Stima":
            if not self.stima_flag:
                update.message.reply_text(
                    "Per usare questo comando devi aver prima inoltrato la lista di @craftlootbot!")
                return 1

            if len(self.costo) == 0:
                update.message.reply_text("Non hai inoltrato nessun messaggio da @lootbotplus")
                return self.annulla(bot, update)

            # merged è una lista di quadruple con i seguenti elementi:
            # elem[0]= quantità oggetto
            # elem[1]= nome oggetto
            # elem[2]= costo oggetto
            # elem[3]= numero negozio per oggetto

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

            for elem in merged:
                self.to_send_negozi += "Compra l'oggetto <b>" + elem[1] + "</b> (" + str(
                    elem[0]) + ") al negozio:\n@lootplusbot " + str(elem[3]) + "\n"

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

    def annulla(self,bot, update):
        """Annulla la stima"""

        self.stima_flag = False
        self.costo_craft = 0
        self.quantita = []
        self.to_send_negozi = ""

        return ConversationHandler.END

    def send_negozi(self, bot, update):
        print("send negozi")
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

        self.to_send_negozi=""

    def estrai_oggetti(self, msg):

        restante = msg.split("già possiedi")[0].split(":")[1]
        aggiornato = ""

        for line in restante.split("\n"):
            if line[2:3] != line[7:8]:
                new_num = int(line[7:8]) - int(line[2:3])

                new_line = line.replace(line[7:8], str(new_num))
                new_line = new_line.replace(line[2:3], str(new_num))
                aggiornato += new_line + "\n"
            else:
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
