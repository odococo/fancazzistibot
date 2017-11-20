#! /usr/bin/env python
# -*- coding: utf-8 -*-

import random
import utils, os, re
from db_call import DB

from negozi_loot import value
from PokerDice import calc_score, consigliami

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    User
)

COMANDI_PLUS = """
attacchiBoss - Ti permette di visualizzare i punteggi di tutti i membri del team in varie forme\n
"""


class Command():
    def __init__(self, bot, update, db):
        """Salva bot, update, comando e parametri"""
        self.bot = bot
        self.update = update
        self.db=db
        # Se ho un messaggio dato da tasto inline
        if update.callback_query:
            command_text = update.callback_query.data
        # Se il messaggio ricevuto è stato inoltrato
        elif update.message.forward_from:
            if update.message.forward_from.username == "craftlootbot":
                command_text = "/loot " + update.message.text
        # Altrimenti se si tratta di un semplice messaggio
        else:
            command_text = update.message.text

        command_text = command_text.split(" ")
        self.command = command_text[0]
        self.params = [param.strip() for param in command_text[1:]]
        # print(self.command, self.params)

    def getattr(self, key, fallback=None):
        """Wrapper per la funzione getattr"""
        for attr in dir(self):
            if attr[1:] == key:
                return getattr(self, attr)
        return fallback

    def execute(self):
        method = self.getattr(self.command[1:], self.unknown_command)
        if (method.__name__.startswith("A")):
            method=self.db.elegible_admin(method)
        elif (method.__name__.startswith("D") and
                  not utils.is_dev(self.bot.id)):
            pass
        else:
            method=self.db.elegible_user(method)
        method(self.bot, self.update)

    def answer(self, text, pretty_json=False, **options):
        """Wrapper che consente di inviare risposte testuali che superano il limite di lunghezza"""
        if not 'parse_mode' in options:
            options['parse_mode'] = "HTML"
        message_id = None
        if pretty_json:
            text = utils.get_pretty_json(text)
        while text:
            message_id = self.update.message.reply_text(text[:4096], **options)
            text = text[4096:]
        return message_id

    def command_list(self, admin=False, dev=False):
        """Ritorna la lista dei comandi disponibili"""


        commands = [command for command in dir(self)
                    if
                    command.startswith("U") or (command.startswith("A") and admin) or (command.startswith("D") and dev)]
        commands = {command[1:]: getattr(self, command).__doc__ for command in commands}
        return commands

    def unknown_command(self):
        self.answer("Ti sembra che {} sia nell'elenco?\n/help per la lista dei comandi".format(self.command))

    # ----------------------------------------------------------------------------------

    def Ustart(self):
        """ - Inizzializza il bot con la schermata di help"""
        self.answer("""Benvenuto al Fancabot. Ha diverse funzionalità! Scoprile con /help!\n
    
Crediti: @brandimax @Odococo""")

    def Uhelp(self):
        """Visualizza l'elenco dei comandi con relativa descrizione"""
        commands = self.command_list(utils.is_admin(
            self.update.message.from_user.id), utils.is_dev(self.bot.id))
        commands = {"/" + command: commands.get(command) for command in commands}
        text = "Benvenuto nel FancaBot! Questo bot ha diverse funzionalità per semplificare il gioco @lootgamebot\n"
        prov = [key + " " + str(value) for key, value in commands.items()]
        text += "\n".join(prov)
        text += COMANDI_PLUS
        text += """Inoltre è anche possibile usufruire delle funzionalità dell'inoltro da @craftlootbot e @lootplusbot:\n
Quando hai un lungo elenco di oggetti data da /lista in @craftlootbot, la puoi inoltrare per ottenere una comoda lista di comandi 
/ricerca da inoltrare a @lootplusbot. Una volta fatto questo puoi inoltrare tutti i risultati di /ricerca qui e infine confermare
premendo "Stima" per ottenere il costo totale del craft, i 10 oggetti piu costosi, il tempo medio per acquistarli tutti 
e una lista di comandi negozio. Se, invece non ti interessa avere queste informazioni premi "Annulla".\n
In più il bot è anche abilitato per funzionare nel gruppo di Fancazzisti! Per verificare quali membri del team madre hanno attaccato
e quali no usa il comando /attacchiBoss, ti verranno presentate delle scelte da fare a seconda di quale informazione vuoi, quando hai 
finito premi "Fine".\n
Questo è tutto per adesso (ma siamo in continuo sviluppo!), se hai idee o suggerimenti scrivici e non tarderemo a risponderti!\n
Crediti: @brandimax @Odococo e un ringraziamento speciale a @PioggiaDiStelle per avermi aiutato <3"""
        self.answer(text)

    # def Uinline(self):
    #   """Esempio di comandi inline"""
    #   keyboard = [
    #     [InlineKeyboardButton(
    #       "Option 1",
    #       callback_data='1'),
    #     InlineKeyboardButton(
    #       "Option 2",
    #       callback_data='2')],
    #     [InlineKeyboardButton(
    #       "Option 3",
    #       callback_data='3')]]
    #   reply_markup = InlineKeyboardMarkup(keyboard)
    #   self.answer('Please choose:', reply_markup=reply_markup)

    def Uroll(self):
        """Lancia un dado senza specificare nulla"""
        keyboard = [
            [InlineKeyboardButton("4", callback_data="/dice 4"),
             InlineKeyboardButton("6", callback_data="/dice 6"),
             InlineKeyboardButton("8", callback_data="/dice 8")],
            [InlineKeyboardButton("10", callback_data="/dice 10"),
             InlineKeyboardButton("12", callback_data="/dice 12"),
             InlineKeyboardButton("20", callback_data="/dice 20")],
            [InlineKeyboardButton("25", callback_data="/dice 25"),
             InlineKeyboardButton("50", callback_data="/dice 50"),
             InlineKeyboardButton("100", callback_data="/dice 100")
             ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        self.answer(
            "Seleziona il numero di facce:",
            reply_markup=reply_markup)

    def Udice(self):
        """Lancia un dado specificando numero di facce e lanci"""
        if (len(self.params) == 2
            and all(utils.is_numeric(param) for param in self.params)):
            text = ""
            for counter in range(int(self.params[1])):
                text += "L'esito n {} è {}\n".format(
                    counter + 1, random.randint(1, int(self.params[0])))
                if self.update.message:
                    self.answer(text)
                else:
                    self.bot.edit_message_text(
                        chat_id=self.update.callback_query.message.chat_id,
                        text=text,
                        message_id=self.update.callback_query.message.message_id
                    )
        elif (len(self.params) == 1
              and utils.is_numeric(self.params[0])):
            actual_dice = "/dice " + self.params[0]
            keyboard = [
                [InlineKeyboardButton(
                    "1", callback_data=actual_dice + " 1"),
                    InlineKeyboardButton(
                        "2", callback_data=actual_dice + " 2"),
                    InlineKeyboardButton(
                        "3", callback_data=actual_dice + " 3")],
                [InlineKeyboardButton(
                    "4", callback_data=actual_dice + " 4"),
                    InlineKeyboardButton(
                        "5", callback_data=actual_dice + " 5"),
                    InlineKeyboardButton(
                        "6", callback_data=actual_dice + " 6")],
                [InlineKeyboardButton(
                    "7", callback_data=actual_dice + " 7"),
                    InlineKeyboardButton(
                        "8", callback_data=actual_dice + " 8"),
                    InlineKeyboardButton(
                        "9", callback_data=actual_dice + " 9")
                ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if self.update.message:
                self.answer(
                    "Seleziona il numero di lanci da effettuare:",
                    reply_markup=reply_markup)
            else:
                self.bot.edit_message_text(
                    chat_id=self.update.callback_query.message.chat_id,
                    text="Seleziona il numero di lanci da effettuare:",
                    message_id=self.update.callback_query.message.message_id,
                    reply_markup=reply_markup
                )
        else:
            self.answer("Il comando funziona così:\n"
                        "/dice numero_facce numero_lanci")

    def Uinfo(self):
        """Ottieni le informazioni riguardo il tuo account"""
        user = self.update.message.from_user
        self.answer(str(user), pretty_json=True)

    def Ujson(self):
        """Ottieni il json dell'update"""
        self.answer(str(self.update), pretty_json=True)

    def Uconvert(self):
        """Converte testo/numero da e verso unabase arbitraria.
    Si possono fornire valori di conversione per personalizzare il risultato"""
        convert_params = self.params[0].split("-") if self.params else []
        if len(convert_params) != 3:
            text = "Comando invalido. Sintassi:\n"
            text += "/convert base_originale-base_destinazione-valori_di_conversione testo/numero\n"
            text += "Esempio: /convert -16-0123456789ABCDEF testo -> traduce un testo in esadecimale"
        else:
            from_base, to_base, values = convert_params
            text = utils.convert(
                self.params[1:],
                int(from_base) if from_base else None,
                int(to_base) if to_base else None,
                values
            )
        self.answer(text)

    def Uwin(self):
        """Per avere le tue possibilità di vincita nell'ispezione dello gnomo"""
        # print("win")
        # se ci sono troppi o pochi numeri non va bene
        if len(self.params) != 5:
            self.answer("Devi inserire 5 numeri separati da spazio! Esempio: /win 1 2 3 4 5")
            return

        # trasforma i parametri in una lista di int
        numeri = [int(param) for param in self.params]
        # calcola il valore della vincita
        win = (1 - calc_score(numeri)) * 100
        self.answer("Possibilità di vincita : " + "{:.3f}".format(win) + "%")

    def Uconsiglia(self):
        """Per avere una tabella di numeri da cambiare
    (la prima colonna rappresenta il numeroDaCambiare->NumeroCambiato, la seconda e la terza sono rispettivamente nuova e
    la vecchia probabilità di vincita, la quarta è il decremento o incremento di probabilità in caso di cambio)"""

        # se ci sono troppi o pochi numeri non va bene
        if len(self.params) != 5:
            self.answer("Devi inserire 5 numeri separati da spazio! Esempio /consiglia 1 2 3 4 5")
            return
        numeri = [int(param) for param in self.params]
        path2img = consigliami(numeri)
        if path2img == 0:
            self.answer("Non Cambiare !")
            return

        with open(path2img, "rb") as file:
            self.bot.sendPhoto(self.update.message.from_user.id, file)
        os.remove(path2img)

    def Dprova(self):
        """test dev"""
        self.answer("ok")

    def Dboss(self):
        """Fissa un messaggio per l'attacco del boss con i seguenti valori:\n
    boss -> 0 (titano) o 1 (phoenix)\n
    giorno -> da 0 a 6 (da lunedì a domenica)\n
    ora -> un'ora qualsiasi"""
        # fixme: verifica del corretto inserimento dei parametri, cambia nome in DfissaBoss
        chat_id = -1001284891867  # Bot per i Boss
        boss = self.params[0]
        giorno = self.params[1]
        ore = self.params[2]
        nomi_boss = ["il Titano", "Phoenix"]
        giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        from_id = self.update.message.from_user.id
        if utils.is_admin(from_id) or utils.is_fanca_admin(from_id):
            message = self.bot.send_message(chat_id=chat_id,
                                            text="Attaccate " + nomi_boss[int(boss) % 2] + " entro le " + ore + " di " +
                                                 giorni[int(giorno) % 7])
            self.bot.pinChatMessage(chat_id, message.message_id, True)

    # admin command ------------------------------------------------------------
    def Autente(self):
        """Visualizza le informazioni relative a un utente
    Ricerca tramite username o id"""
        if self.params:
            result = self.db.get_user(self.params[0])
            if result:
                text = utils.get_user(result)
            else:
                text = "Non ci sono utenti che rispondono ai parametri della ricerca"
        else:
            text = "Specifica id o username dell'utente che vuoi cercare"
        self.answer(text)

    def Autenti(self):
        """Visualizza gli utenti che utilizzano un determinato bot"""
        query = """SELECT utenti.id AS user_id,
            bot.id AS bot_id
            FROM bot_users
            INNER JOIN users AS utenti ON utenti.id = id_user
            INNER JOIN users AS bot ON bot.id = id_bot
            GROUP BY utenti.id, bot.id"""
        users = self.db.execute(query)
        if users:
            users = [users] if isinstance(users, dict) else users
            text = "Elenco utenti:\n"
            for user in users:
                text += "<code>{}</code>: <code>{}</code>\n".format(
                    user['bot_id'],
                    user['user_id'])
        else:
            text = "Non ci sono utenti nel database"
        self.answer(text)


    def Aregistra(self):
        """Aggiorna i permessi di un utente"""
        if len(self.params) == 2:
            key = self.params[0]
            permesso = self.params[1]
            user = self.db.get_user(key)
            if permesso not in user:
                text = "Non esiste questo permesso!"
            else:
                user[permesso] = not user[permesso]
                self.db.update_user(user)
            text = "Aggiornamento completato!"
        else:
            text = """Non hai inserito i parametri correttamente! /registra utente permesso
    utente tramite id o username
    permesso tra questi valori: tester admin loot_admin loot_user banned"""
        self.answer(text)

def new_command(bot, update):
    command = Command(bot, update, DB())
    command.execute()

