#! /usr/bin/env python
# -*- coding: utf-8 -*-

import random

import math
from datetime import datetime, timedelta

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

import os
import utils
from PokerDice import calc_score, consigliami
from db_call import DB

COMANDI_PLUS = """\n
/attacchiBoss - Ti permette di visualizzare i punteggi di tutti i membri del team in varie forme\n
/cercaCraft num1 num2 - Ti permette di cercare oggetti in base ai punti craft, rarità e rinascita. Dato num1>num2 cerca oggetti craft con valore compreso tra num1 e num2\n
/compra - ti permette di calcolare facilmente quanti scrigni comprare in base a sconti dell'emporio e il tuo budget\n
/resetBoss - resetta i punteggi associati agli attacchi al Boss di tutti
/top - ti permette di visualizzare la classifica dei top player in base a [pc totali, pc settimanali, edosoldi, abilità, rango)\n\n
<b>=====COMANDI DA INOLTRO=====</b>\n\n
"""


videos={'loot':("Video tutorial su come utilizzare i messaggi di inoltro da @craftlootbot","BAADBAADdgQAAkLEAAFRvQtpL8P36MkC"),
        'rarita':("Tutorial su come utilizzare i comandi /compra e /rarita","BAADBAADygIAAtD9GVEWYOqYqzCxvAI")}


class Command():
    @utils.catch_exception
    def __init__(self, bot, update, db):
        """Salva bot, update, comando e parametri"""
        self.bot = bot
        self.update = update
        self.db = db
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
            method = self.db.elegible_loot_admin(method)
        elif (method.__name__.startswith("D")):
            method = self.db.elegible_admin(method)
        else:
            method = self.db.elegible_loot_user(method)
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
        print(self.update)
        if "private" in self.update.message.chat.type :
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
        text = "Benvenuto nel FancaBot! Questo bot ha diverse funzionalità per semplificare il gioco @lootgamebot\n\n" \
               "<b>=====COMANDI SEMPLICI=====</b>\n\n"
        prov = [key + " " + str(value) for key, value in commands.items()]
        text += "\n\n".join(prov)
        text += COMANDI_PLUS
        text += """Inoltre è anche possibile usufruire delle funzionalità dell'inoltro da @craftlootbot e @lootplusbot:
Quando hai un lungo elenco di oggetti data da /lista in @craftlootbot, la puoi inoltrare, ti satà chiesta quale informazione vuoi visualizzare:
<b>Negozi</b>
Ti permette di ottenere una comoda lista di negozi degli oggetti mancanti da poter inoltrare a @lootbotplus
<b>Ricerca</b>
Ti sarà inviata una comoda lista di comandi /ricerca da inoltrare a @lootplusbot.
Una volta fatto questo puoi inoltrare tutti i risultati di /ricerca qui e infine confermare premendo "Stima" per ottenere il costo totale del craft, i 10 oggetti piu costosi, il tempo medio per acquistarli tutti e una lista di comandi negozio.
Se, invece non ti interessa avere queste informazioni premi "Annulla".
In più il bot è anche abilitato per funzionare nel gruppo di Fancazzisti! Se sei un admin puoi inoltrare il messaggio "Team" in @lootgamebot per salvare gli attacchi che ha fatto il team madre al boss! Ti verra chiesto di scegliere il boss in questione (Phoenix o Titan) e il gioco è fatto.\n\n
<b>Top</b>
Inviando il messaggio "Giocatore" che ottieni in @lootgamebot aggiornerai il database e potrai visualizzare la tuo posizione in classifica! (leggi il comando /top per ulteriori informazioni)
<b>Pietre del Drago</b>
Inoltrando il messagio "/zaino D" da @lootplusbot, otterrai il valore di tutte le pietre del drago che sono presenti nel tuo zaino
<b>=====FINE=====</b>\n\n
Votaci sullo <a href="https://telegram.me/storebot?start=fancazzisti_bot">Storebot</a>!
Questo è tutto per adesso (ma siamo in continuo sviluppo!), se hai idee o suggerimenti scrivici e non tarderemo a risponderti!
Crediti: @brandimax @Odococo e un ringraziamento speciale a @PioggiaDiStelle per avermi aiutato ❤️."""
        self.answer(text, parse_mode="HTML")

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

    def Uhelpvideo(self):
        """Invia il video tutorial per i comandi di difficile comprensione"""
        descrizione="I video disponibili sono: \n"
        for key in videos.keys():
            descrizione+="<b>"+key+"</b> : "+videos[key][0]+"\n"

        inline=[]
        for key in videos.keys():
            inline.append(InlineKeyboardButton(key, callback_data="/helpvideo "+key))

        print(inline)

        #self.update.message.reply_text(descrizione, reply_markup=InlineKeyboardMarkup(inline), parse_mode="HTML")
        self.bot.send_message(self.update.message.from_user.id,descrizione, reply_markup=InlineKeyboardMarkup([inline]), parse_mode="HTML")

    def Utalenti(self):
        """Manda un pdf con tutta la lista degli oggetti necessari per ogni talento"""
        self.bot.sendDocument(self.update.message.chat_id, "BQADBAADGAMAAgs3mVFa4igIcxDUAwI")

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

    def Uhelplink(self):
        """ Ti conduce alla pagina in cui sono scritte le operazioni del bot in forma completa"""
        # todo: usa messageEntity per una migliore foramttazione

        self.answer("https://github.com/odococo/fancazzistibot/blob/master/README.md")

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

    def Upermessi(self):
        """Ottieni info sui permessi relativi al tuo account"""
        user_id = self.update.message.from_user.id
        permission = self.db.get_permission_user(user_id)
        self.answer(str(permission), pretty_json=True)

    def Ujson(self):
        """Ottieni il json dell'update"""
        self.answer(str(self.update), pretty_json=True)

    def Uconvert(self):
        """Converte testo/numero da e verso unabase arbitraria. Si possono fornire valori di conversione per personalizzare il risultato"""
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
        """Seguito da cinque numeri separati da spazio, ti da le tue possibilità di vincita nell'ispezione dello gnomo"""
        # print("win")
        # se ci sono troppi o pochi numeri non va bene
        if len(self.params) != 5:
            self.answer("Devi inserire 5 numeri separati da spazio! Esempio: /win 1 2 3 4 5")
            return

        # trasforma i parametri in una lista di int
        numeri = [int(param) for param in self.params]
        # calcola il valore della vincita
        win = (1 - calc_score(numeri)) * 100
        self.answer("Probabilità di vincita : " + "{:.3f}".format(win) + "%")

    def Urarita(self):
        """Quando inoltri un messagio di craftlootbot vengono automaticamente salvate le rarità degli oggetti che non possiedi. Questo comando ti permette di avere (in percentuale) le informazioni su quali rarità hai mancanza nel tuo zaino. Ottimo da utilizzare in con il comando /compra"""
        user_id = self.update.message.from_user.id
        user_item = self.db.get_user_items(user_id)
        tot = 0
        for key in user_item.keys():
            if not key == "id":
                tot += user_item[key]

        res = ""
        for key in user_item.keys():
            if not key == "id" and not user_item[
                                           key] == 0: res += "Oggetti <b>" + key.upper() + "</b> : " + "{:.3f}".format(
                user_item[key] / tot * 100) + "%\n"

        if not res: res = "Non sono salvate rarità sul tuo account"
        else: res+="Ricorda di resettare le rarità quando compri scrigni all'emporio!\n"

        self.answer(res)

    def Uresetrarita(self):
        """Ti permette di resettare tutte le rarità relative al tuo username, da usare quando hai comprato scrigni all'emporio"""
        user_id = self.update.message.from_user.id
        self.db.reset_rarita_user(user_id)
        self.answer("Rarità resettate")

    def Uconsiglia(self):
        """Seguito da cinque numeri separati da spazio ,invia un'immagine con una tabella sui numeri che dovresti cambiare e le relative probabilità di vincita"""

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

    def Ucheoresonotra(self):
        """Calcola l'ora che sarà tra un tot di ore\nUso: /cheoresonotra hh:mm\nEsempio: /cheoresonotra 7:45 """
        if len(self.params)!= 1:
            self.answer("Non hai inserito il numero corretto di parametri!\nUso: /cheoresonotra hh:mm"
                                           "\nEsempio: /cheoresonotra 7:45")
            return

        try:
            ore=int(self.params[0].split(":")[0])
            minuti=int(self.params[0].split(":")[1])
        except ValueError:
            self.update.message.reply_text("Non hai inserito dei numeri!\nUso: /cheoresonotra hh:mm"
                                           "\nEsempio: /cheoresonotra 7:45")
            return

        future_hour = datetime.now() + timedelta(hours=ore+1, minutes=minuti)
        self.answer("Tra "+str(ore)+" ore e "+str(minuti)+" minuti, saranno le "+
                                       str(str(future_hour.time()).split(".")[0])+" del "+str(future_hour.date().strftime('%d-%m-%Y')))

    def Uartefatti(self):
        """Invia la lista di artefatti"""
        msg="""
FIAMMEGGIANTE
Per ottenere questo artefatto devi raggiungere 85 punti dungeon e possedere 5.000.000§, questi ultimi ti verranno sottratti per completare il rituale.

ELETTRICO
Per ottenere questo artefatto devi raggiungere 10.000 punti creazione, il drago al livello 100 e possedere 10.000.000§, questi ultimi ti verranno sottratti per completare il rituale.

TEMPESTA
Per ottenere questo artefatto devi portare al livello 10 almeno 5 Talenti, possedere 20 Gemme (verranno consumate) e raggiungere le 200 Imprese completate.

BUIO
Per ottenere questo artefatto devi aver completato 1000 missioni, vinto 500 ispezioni (effettuate o respinte), e ottenuto 2000 Polvere (S).

DIVINATORIO
Per ottenere questo artefatto devi:
> Raggiungere il livello 1000
> Aver raggiunto rango 350
> Aver completato 20 scalate complete nello stesso team
> Aver venduto almeno 500 oggetti al Contrabbandiere
> Aver partecipato e aiutato a vincere 5 imprese globali

L'artefatto è pronto ma non può essere ancora ottenuto in quanto potrebbe essere aggiornato lievemente"""
        self.answer(msg)


    # admin command ------------------------------------------------------------

    def Asvegliamadre(self):
        """Manda un messaggio ai membri del Team madre (quelli dentro la lista punteggio)"""
        users=self.db.get_punteggi()
        for user in users:
            self.bot.send_message(user['id']," ".join(self.params))

    def Apinboss(self):
        """Fissa un messaggio per l'attacco del boss con i seguenti valori:
        boss -> 0 (titano) o 1 (phoenix)
        giorno -> da 0 a 6 (da lunedì a domenica)
        ora -> un'ora qualsiasi"""
        if len(self.params) != 3:
            self.answer("Non hai inserito i parametri giusti!\n"
                        "boss -> 0 (titano) o 1 (phoenix)\n"
                        "giorno -> da 0 a 6 (da lunedì a domenica)\n"
                        "ora -> un'ora qualsiasi")
        chat_id=self.update.effective_chat.id
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
        self.bot.deleteMessage(chat_id=self.update.message.chat.id,
                          message_id=self.update.message.message_id)

    def Autente(self):
        """Visualizza le informazioni relative a un utente. Ricerca tramite username o id"""
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
        users = self.db.get_users_and_id()
        if users:
            users = [users] if isinstance(users, dict) else users
            text = "Elenco utenti:\n"
            for user in users:
                text += "<b>username</b>: <code>" + user['username'] + "</code>\n" \
                                                                       "<b>id</b>: <code>" + str(
                    user['id']) + "</code>\n" \
                                  "<b>admin</b>: <code>" + str(user['admin']) + "</code>\n" \
                                                                                "<b>tester</b>: <code>" + str(
                    user['tester']) + "</code>\n" \
                                      "<b>loot_user</b>: <code>" + str(user['loot_user']) + "</code>\n" \
                                                                                            "<b>loot_admin</b>: <code>" + str(
                    user['loot_admin']) + "</code>\n" \
                                          "<b>banned</b>: <code>" + str(user['banned']) + "</code>\n" \
                                                                                          "<b>join date</b>: <code>" + str(
                    user['date']) + "</code>\n\n"
        else:
            text = "Non ci sono utenti nel database"


        for elem in utils.text_splitter(text,splitter="\n\n"):
            self.answer(elem, parse_mode="HTML")


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
            self.bot.send_message(user['id'], "Sei stato promosso a " + permesso)
        else:
            text = """Non hai inserito i parametri correttamente! /registra utente permesso
    utente tramite id o username
    permesso tra questi valori: tester admin loot_admin loot_user banned"""
        self.answer(text)

    def Aremoveuser(self):
        """Rimuove un user dal bot"""
        if len(self.params) != 1:
            self.answer("Devi usare il comando seguito dallo username che vuoi rimuovere dal bot")
            return

        username=self.params[0]
        user=self.db.get_user(username)
        self.db.delete_from_all(user['id'])
        self.bot.send_message(user['id'],"Sei stato rimosso dal bot")
        self.answer("Ho rimosso "+username+" dal bot")

    def Asveglia(self):
        """Invia un messaggio a uno o piu username per spronarli ad attaccare il boss"""
        if len(self.params)< 1:
            self.answer("Non hai inserito nessun username")
            return

        to_send=["Attacca il boss dannazzione!","Lo hai attaccato il boss?","Se non attacchi il boss ti prendo a sberle"]

        for elem in self.params:
            user = self.db.get_user(elem)
            print(user)
            try:
                self.bot.send_message(user['id'], random.choice(to_send))

            except (KeyError, TypeError):
                self.answer("Non ho trovato " + str(elem) + " tra gli users del bot")
        self.answer("Messaggio inviato")

    # developer comands ----------------------------------------

    def Dsendtoall(self):
        """Manda un messaggio a tutti gli utenti"""
        if len(self.params) == 0:
            self.answer("Devi usare il comando seguito da un messaggio")
            return
        users = self.db.get_id_users()

        if not isinstance(users, list): users = [users]

        msg = " ".join(self.params)

        for user in users:
            self.bot.send_message(user['id'], msg)

    def Dprova(self):
        """test dev"""
        self.answer(str(self.bot.getChat(24978334)), pretty_json=True)

    def Ddeletefromall(self):
        """Rimuove un o piu users (separati da spazio) dal bot completamente"""
        if len(self.params)<1:
            self.answer("Il comando deve essere seguito da uno o piu username separati da spazio")
        for elem in self.params:
            user=self.db.get_user(elem)
            print(user)
            try:
                self.db.delete_from_all(user['id'])
                self.bot.send_message(user['id'], "Sei stao rimosso dal bot")
                self.answer(str(elem)+" è stato rimosso dal bot!")

            except (KeyError, TypeError):
                self.answer("Non ho trovato "+str(elem)+" tra gli users del bot")

    def Dciaosoho(self):
        self.bot.send_message(241317532,"ciao osho")

    def Dchiblocca(self):

        users=self.db.get_users()

        for  user in users:
            self.answer("Mando messaggio a "+str(user['id']))
            self.bot.send_message(user['id'],"Messaggio di prova, se lo ricevi vuol dire che non mi hai bloccato!\nBravo/a")



def new_command(bot, update):
    command = Command(bot, update, DB())
    command.execute()
