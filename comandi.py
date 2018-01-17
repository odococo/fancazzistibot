#! /usr/bin/env python
# -*- coding: utf-8 -*-
import operator
import random
import time

import math
from datetime import datetime, timedelta
from threading import Thread, Event

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove)

import os
import utils
from PokerDice import calc_score, consigliami
from db_call import DB

COMANDI_PLUS = """\n
/attacchiBoss - Ti permette di visualizzare i punteggi di tutti i membri del team in varie forme\n
/cercaCraft num1 num2 - Ti permette di cercare oggetti in base ai punti craft, rarità e rinascita. Dato num1>num2 cerca oggetti craft con valore compreso tra num1 e num2\n
/compra - ti permette di calcolare facilmente quanti scrigni comprare in base a sconti dell'emporio e il tuo budget\n
/resetBoss - resetta i punteggi associati agli attacchi al Boss di tutti\n
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
        #elif update.message.forward_from:
         #   if update.message.forward_from.username == "craftlootbot":
          #      command_text = "/loot " + update.message.text
        # Altrimenti se si tratta di un semplice messaggio
        else:
            command_text = update.message.text

        command_text = command_text.split(" ")
        self.command = command_text[0]
        self.params = [param.strip() for param in command_text[1:]]
        try:
            self.is_private="private" in update.message.chat.type
        except AttributeError:
            self.is_private="private" in update.callback_query.message.chat.type




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
        #print(self.update)
        if self.is_private:
            self.answer("Ti sembra che {} sia nell'elenco?\n/help per la lista dei comandi".format(self.command))

    # ----------------------------------------------------------------------------------

    def Ustart(self):
        """- Inizzializza il bot con la schermata di help"""
        if not self.is_private:
            self.answer("Questo comando è disponibile solo in privata")
            return
        self.answer("""Benvenuto al Fancabot. Ha diverse funzionalità! Scoprile con /help!\n
    
Crediti: @brandimax @Odococo""")

    def Uhelpvideo(self):
        """- Invia il video tutorial per i comandi di difficile comprensione"""
        descrizione="I video disponibili sono: \n"
        for key in videos.keys():
            descrizione+="<b>"+key+"</b> : "+videos[key][0]+"\n"

        inline=[]
        for key in videos.keys():
            inline.append(InlineKeyboardButton(key, callback_data="/helpvideo "+key))

        #print(inline)

        #self.update.message.reply_text(descrizione, reply_markup=InlineKeyboardMarkup(inline), parse_mode="HTML")
        self.bot.send_message(self.update.message.from_user.id,descrizione, reply_markup=InlineKeyboardMarkup([inline]), parse_mode="HTML")

    def Utalenti(self):
        """- Manda un pdf con tutta la lista degli oggetti necessari per ogni talento"""
        self.bot.sendDocument(self.update.message.chat_id, "BQADBAADGAMAAgs3mVFa4igIcxDUAwI")

    def Uroll(self):
        """- Lancia un dado senza specificare nulla"""
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
        """- Ti conduce alla pagina in cui sono scritte le operazioni del bot in forma completa"""
        # todo: usa messageEntity per una migliore foramttazione

        self.answer("https://github.com/odococo/fancazzistibot/blob/master/README.md")

    def Udice(self):
        """numFacce numLanci - Lancia un dado specificando numero di facce e lanci"""
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
        #todo: prendi nome dal db e formatta per bene
        """- Ottieni le informazioni riguardo il tuo account"""
        user = self.db.get_user(self.update.message.from_user.id)
        to_send=utils.get_user(user)
        self.answer(to_send)

    def Upermessi(self):
        """- Ottieni info sui permessi relativi al tuo account"""
        user_id = self.update.message.from_user.id
        permission = self.db.get_permission_user(user_id)
        self.answer(str(permission), pretty_json=True)

    def Ujson(self):
        """- Ottieni il json dell'update"""
        self.answer(str(self.update), pretty_json=True)

    def Uconvert(self):
        """base_originale-base_destinazione-valori_di_conversione testo/numero- Converte testo/numero da e verso unabase arbitraria. Si possono fornire valori di conversione per personalizzare il risultato"""
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
        """num1 num2 num3 num4 num5 - Seguito da cinque numeri separati da spazio, ti da le tue possibilità di vincita nell'ispezione dello gnomo"""
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
        """- Quando inoltri un messagio di craftlootbot vengono automaticamente salvate le rarità degli oggetti che non possiedi. Questo comando ti permette di avere (in percentuale) le informazioni su quali rarità hai mancanza nel tuo zaino. Ottimo da utilizzare in con il comando /compra"""
        if not self.is_private:
            self.answer("Questo comando è disponibile solo in privata")
            return
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
        """- Ti permette di resettare tutte le rarità relative al tuo username, da usare quando hai comprato scrigni all'emporio"""
        if not self.is_private:
            self.answer("Questo comando è disponibile solo in privata")
            return
        user_id = self.update.message.from_user.id
        self.db.reset_rarita_user(user_id)
        self.answer("Rarità resettate")

    def Uconsiglia(self):
        """num1 num2 num3 num4 num5 - Invia un'immagine con una tabella sui numeri che dovresti cambiare e le relative probabilità di vincita"""
        if not self.is_private:
            self.answer("Questo comando è disponibile solo in privata")
            return
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
        """hh:mm - Calcola l'ora che sarà tra un tot di ore\nEsempio: <pre>/cheoresonotra 7:45</pre> """
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
        """- Invia la lista di artefatti"""
        msg="""
<b>FIAMMEGGIANTE</b>
Per ottenere questo artefatto devi raggiungere 85 punti dungeon e possedere 5.000.000§, questi ultimi ti verranno sottratti per completare il rituale.

<b>ELETTRICO</b>
Per ottenere questo artefatto devi raggiungere 10.000 punti creazione, il drago al livello 100 e possedere 10.000.000§, questi ultimi ti verranno sottratti per completare il rituale.

Una volta ottenuti i primi due potrai accedere alla rinascita r4

<b>TEMPESTA</b>
Per ottenere questo artefatto devi portare al livello 10 almeno 5 Talenti, possedere 20 Gemme (verranno consumate) e raggiungere le 200 Imprese completate.

<b>BUIO</b>
Per ottenere questo artefatto devi aver completato 1000 missioni, vinto 500 ispezioni (effettuate o respinte), e ottenuto 2000 Polvere (S).
Ti permette di accedere alla trasmogrificazione

<b>DIVINATORIO</b>
Per ottenere questo artefatto devi:
> Raggiungere il livello 1000
> Aver raggiunto rango 350
> Aver completato 20 scalate complete nello stesso team
> Aver venduto almeno 500 oggetti al Contrabbandiere
> Aver partecipato e aiutato a vincere 5 imprese globali
Una volta ottenuto potrai accedere al potenziamento flaridion

"""
        self.answer(msg)

    def Uregoleboss(self):
        """- invia le regole riguardanti i punteggi del boss"""
        regole="""Mese nuovo regole nuove
Da oggi i punteggi associati al vostro username saranno crucuali nella vostra vita del team!
I punteggi vengono aggiornati ogni volta che si attacca Titan o Phoenix, se avete diemnticato di attaccarlo entro lo scadere del tempo vi verra aggiunto +1 o +2 rispettivamente.
Il valore a cui dovrete tutti puntare è zero ovviamente.
Dal tre in su si è a forte rischio kick dal madre.
Per poter visualizzare il vostro punteggio basta usare il comando /attacchiboss
Lo dico tanto per essere chiaro, l'aggiornamento del punteggio avviene in modo automatico, quidni non ci posso fare nulla per cambiarlo
Detto questo in bocca al lupo"""
        self.answer(regole)

    def Umigra(self):
        """nuovoUsername - Cambia il tuo username dentro al bot"""
        if not self.is_private:
            self.answer("Questo comando è disponibile solo in privata")
            return

        if len(self.params)!=1:
            self.answer("Devi inserire un nome che sarà il tuo nuovo username associato al bot")
            return
        elif "@" in self.params[0]:
            self.answer("Non mettere la chiocciola")
            return
        user_id=self.update.message.from_user.id
        new_username=self.params[0]

        res=self.db.update_username(new_username,user_id)
        #print(res)

        self.answer("Complimenti! il tuo nuovo nome è "+new_username)

    def Uannulladefinitivo(self):
        """- rimuove completamente la tastiera personalizzata (quella con i bottoni) da usare quando non se ne va"""
        if not self.is_private:
            self.answer("Questo comando è disponibile solo in privata")
            return
        self.update.message.reply_text("Levata!",reply_markup=ReplyKeyboardRemove())

    def Ustanzavuota(self):
        """- Invia i drop per le stanze vuote"""
        to_send="""
<b>LISTA DROP DUNGEON</b> (aka Stanza vuota)
Qua sono presenti tutti i drop per le stanze del tipo:
<i>Succede qualcosa, qualcosa che..[qualosa]..procedi alla prossima stanza con aria interrogativa</i>

- forse ti farebbe sentire più <b>fortunato</b> —-> <b>Gettone</b>
- ti fa sentire un po' più <b>esperto</b> di prima —-> <b>10 Exp</b>
- in effetti potrebbe farti <b>sentire meglio</b>—-> <b>Pozione</b>
- <b>luccica e riflette</b> la luce in modo incredibile —-> <b>Gemma</b>
- ti provoca un <b>brivido</b> nella schiena —-> <b>Necronucleo</b>
- ti fa stare un po' più al <b>caldo</b> —-> <b>Lana</b>
- ti fa provoca un <b>prurito</b> fastidioso —-> <b>Polvere</b>
- può farti <b>rialzare</b> una volta in più —-> <b>Piuma di Fenice</b>
"""

        self.answer(to_send, parse_mode="HTML")

    # admin command ------------------------------------------------------------

    def Asvegliamadre(self):
        """msg- Manda un messaggio ai membri del Team madre (quelli dentro la lista punteggio)"""
        if len(self.params)==0:
            self.answer("Devi inviare un messaggio insieme al comando")
            return
        users=self.db.get_punteggi()
        for user in users:
            self.bot.send_message(user['id']," ".join(self.params))

    def Apinboss(self):
        """Fissa un messaggio per l'attacco del boss con i seguenti valori:
               boss -> 0 (titano) o 1 (phoenix)
               giorno -> 0 (oggi) 1 (domani)
               ora -> un'ora qualsiasi nel formato hh:mm (vuoto per attaccare subito)
               E manda un messaggio ai membri del team madre"""


        if not len(self.params) == 3 and not len(self.params) == 2 :
            self.answer("Non hai inserito i parametri giusti!\n"
                        "boss -> 0 (titano) o 1 (phoenix)\n"
                        "giorno -> 0 (oggi) 1 (domani)\n"
                        "ora -> un'ora qualsiasi nel formato hh:mm (vuoto per attaccare subito)")

        chat_id = self.update.effective_chat.id
        boss = self.params[0]
        giorno = self.params[1]

        if len(self.params)==2:
            ore=0
            minuti=0
        else:
            try:
                ore = int(self.params[2].split(":")[0])
            except ValueError:
                self.update.message.reply_text("Non hai inserito un numero corretto per l'ora!")
                return

            try:
                minuti = int(self.params[2].split(":")[1])
            except ValueError:
                self.update.message.reply_text("Non hai inserito un numero corretto per i minuti!")
                return
            except IndexError:
                minuti=0


        try:
            giorno=int(giorno)
        except ValueError:
            self.update.message.reply_text("Non hai inserito un numero corretto per il giorno!")
            return



        nomi_boss = ["il Titano", "Phoenix"]
       # print(giorno,ore, minuti)
        if giorno:
            future_hour = datetime.now() + timedelta(hours=24+1)
        else:
            future_hour = datetime.now() + timedelta(hours=1)

        #print(future_hour)

        future_hour=future_hour.replace(hour=ore, minute=minuti)
        #print(future_hour)

        to_send="Attaccate " + nomi_boss[int(boss) % 2] + " entro le " +\
                                             str(str(future_hour.time()).split(".")[0]) + " del "+\
                                             str(future_hour.date().strftime('%d-%m-%Y'))

        message = self.bot.send_message(chat_id=chat_id,
                                        text=to_send)
        self.bot.pinChatMessage(chat_id, message.message_id, True)
        self.bot.deleteMessage(chat_id=self.update.message.chat.id,
                               message_id=self.update.message.message_id)

        #invio messaggio ai membri del team madre
        users = self.db.get_punteggi()
        for user in users:
            self.bot.send_message(user['id'], to_send)

    def Autente(self):
        """username - Visualizza le informazioni relative a un utente. Ricerca tramite username o id"""
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
        """- Visualizza gli utenti che utilizzano un determinato bot"""
        if not self.is_private:
            self.answer("Questo comando è disponibile solo in privata")
            return
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


        for elem in utils.text_splitter_lines(text, splitter="\n\n"):
            self.answer(elem, parse_mode="HTML")

    def Aregistra(self):
        """username permesso - Aggiorna i permessi di un utente tra [tester, admin ,loot_admin ,loot_user, banned]"""
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
        """username - Rimuove un user dal bot"""
        if len(self.params) != 1:
            self.answer("Devi usare il comando seguito dallo username che vuoi rimuovere dal bot")
            return

        username=self.params[0]
        user=self.db.get_user(username)
        print(user)

        if not user:
            self.answer("Non ci sono users con quell'username")
            return

        if isinstance(user,list):
            print(user)
            user=user[0]
        self.db.delete_from_all(user['id'])
        self.bot.send_message(user['id'],"Sei stato rimosso dal bot")
        self.answer("Ho rimosso "+username+" dal bot")

    def Asveglia(self):
        """username1 username2 ... - Invia un messaggio a uno o piu username per spronarli ad attaccare il boss"""
        if len(self.params)< 1:
            self.answer("Non hai inserito nessun username")
            return

        to_send=["Attacca il boss dannazione!","Lo hai attaccato il boss?","Se non attacchi il boss ti prendo a sberle"]

        for elem in self.params:
            user = self.db.get_user(elem)
            #print(user)
            try:
                self.bot.send_message(user['id'], random.choice(to_send))

            except (KeyError, TypeError):
                self.answer("Non ho trovato " + str(elem) + " tra gli users del bot")
        self.answer("Messaggio inviato")

    def Abanned(self):
        """- Ritorna una lista di tutti gli utenti bannati dal bot"""
        banned=self.db.get_banned()
        if not banned:
            self.answer("Non ci sono utenti bannati nel bot")
            return

        if not isinstance(banned,list): banned=[banned]

        to_send="<b>Id utenti bannati</b>:\n"
        for elem in banned:
            to_send+="<code>"+str(elem['id'])+"</code>\n"

        to_send+="Usa @usinfobot per visualizzare il nome utente"

    def Aunban(self):
        """user_id - unbanna uno user dal bot tramite id (usa /banned per avere la lista dei bannati)"""
        if len(self.params)!=1:
            self.answer("Devi inserire un solo id dopo il comando")
            return

        id=self.params[0]

        if not id.isnumeric():
            self.answer("Non hai inserito un id valido")
            return

        id=int(id)

        users=self.db.get_id_users()

        if not users:
            self.answer("Non sono presneti users nel database")
            return

        if not isinstance(users, list):users=[users]

        found=False
        for user in users:
            if user['id']==id:
                found=True
                break

        if not found:
            self.answer("Non ho trovato l'id specificato nel database")
            return

        self.db.delete_user(id)
        self.bot.sendMessage(id, "Sei stato sbannato! Premi /start per accedere alle funzionalità del bot")
        self.answer("L'id "+str(id)+" è stato sbannato")


    # developer comands ----------------------------------------

    def Dsendtoall(self):
        """msg - Manda un messaggio a tutti gli utenti"""
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

        self.answer(str(self.bot.sendChatAction(self.params[0], "typing")), pretty_json=True)

    def Ddeletefrombot(self):
        """username - Rimuove un o piu users (separati da spazio) dal bot completamente"""
        if len(self.params)<1:
            self.answer("Il comando deve essere seguito da uno o piu username separati da spazio")
        for elem in self.params:
            user=self.db.get_user(elem)
            #print(user)
            try:
                self.db.delete_from_all(user['id'])
                self.bot.send_message(user['id'], "Sei stao rimosso dal bot")
                self.answer(str(elem)+" è stato rimosso dal bot!")

            except (KeyError, TypeError):
                self.answer("Non ho trovato "+str(elem)+" tra gli users del bot")

    def Dciaosoho(self):
        """- Manda ciao ad osho"""
        self.bot.send_message(241317532,"ciao osho")

    def Dchiblocca(self):
        """- Permette di ottenere l'id di chi ha bloccato il bot"""

        @utils.catch_exception
        def inner(bot, update):
            users=self.db.get_users()

            for  user in users:
                self.answer("Mando messaggio a "+str(user['id']))
                self.bot.sendChatAction(user['id'],"typing")
            self.answer("Fine")

        inner(self.bot, self.update)

    def Daddbug(self):
        """bug - aggiunge un bug al todo del bot"""
        if len(self.params)==0:
            self.answer("Non hai inviato nessuna stringa rappresentante il bug")
            return
        bug=" ".join(self.params)
        self.db.add_bug(bug)
        self.answer("Bug aggiunto")

    def Ddeletebug(self):
        """id - rimuove un bug dal bot"""
        if len(self.params)!=1:
            self.answer("Devi usare l'id del bug per poterlo eliminare")
            return
        try:
            bug_id=int(self.params[0])
        except ValueError:
            self.answer("Non hai inserito un id valido")
            return

        self.db.delete_bug(bug_id)
        self.answer("Bug eliminato")

    def Dviewbugs(self):
        """ manda la sita dei bug da correggere"""
        bugs=self.db.get_bugs()


        #controlla che ci siano bug nella tabella
        if not bugs:
            self.answer("Non ci sono bug")
            return
        #se ne è presente uno solo trasformalo da dict a list
        if not isinstance(bugs,list): bugs=[bugs]

        sortedD = sorted(bugs, key=lambda k: k['id'])

        to_send="<b>BUGS</b>\n"
        for elem in sortedD:
            to_send+=str(elem["id"])+") "+elem["bug"]+"\n"
        self.answer(to_send,parse_mode="HTML")


def new_command(bot, update):
    command = Command(bot, update, DB())
    command.execute()

#timer class
class Timer(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stop=False
        self.bot=None
        self.update=None
        self.date_time=None
        self.to_send_id=None

    def set_bot_update(self, bot, update):
        """Setter per bot e update"""
        self.bot = bot
        self.update = update
        self.to_send_id = update.effective_chat.id

    def set_hour(self, date_time):
        """Setta l'ora in cui far partire il timer
         #:param date_time: ora e data della fine del timer
         #:type: datetime"""

        self.date_time=date_time

    def stop_timer(self):
        self.stop=True

    def get_stop_event(self):
        """Ritorna lo stato del thread"""
        return self.stop and self.is_alive()

    def get_remning_time_str(self, string=True):
        """Ritorna la stringa con il tempo rimanente
        @:param string: boolena per ritornare in stringa o datetime
        @:type: bool
        #:return: str or datetime"""
        if not self.date_time:
            self.update.message.reply_text("Non c'è nessun timer impostato")
            return
        remaning_time=self.date_time - datetime.now()

        if string: return str(str(remaning_time.time()).split(".")[0])
        else: return remaning_time.time()

    def get_remaning_time(self):
        """Notifica l'utente del tempo rimanente"""
        self.update.message.reply_text("Mancano "+self.get_remning_time_str())

    def run(self):
        """Runna il timer"""
        if not self.date_time:
            self.bot.sendMessage(self.to_send_id, "Devi prima usare il comando /pinboss")
            return

        self.stop=False

        #prendi la differenza tra quanto c'è da aspettare e ora
        d,h,m=self.dates_diff(self.date_time)
        if h<0:
            to_send="scadrà tra "+str(int(m))+" minuti"
        else:
            to_send="scadrà tra "+str(int(h))+" ore"
        self.bot.sendMessage(self.to_send_id, "Timer avviato!"+to_send)

        #se i minuti da aspettare sono meno di 10 usa quelli come wait time
        wait_time=600
        if m<600: wait_time=m

        #aspetta 10 minuti finche non viene stoppato
        while not self.stop:
            #se il tempo è terminato esci dal ciclo
            if datetime.now()==self.date_time: break
            time.sleep(5)

        self.bot.sendMessage(self.to_send_id,"Il timer è scaduto")

    def dates_diff(self, date_time):
        """Get the difference between a datetime and now
        @:param date_time: the date time
        @:type: datetime"""
        diff = datetime.now() - date_time
        days = diff.days
        days_to_hours = days * 24
        diff_btw_two_times = (diff.seconds) / 3600
        overall_hours = days_to_hours + diff_btw_two_times
        overall_minutes=overall_hours*60

        return  days, overall_hours, overall_minutes
