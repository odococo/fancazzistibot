#! /usr/bin/env python
# -*- coding: utf-8 -*-

import random
import utils, os, re
from db_call import execute
from negozi_loot import value
from PokerDice import calc_score, consigliami

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    User
)

class Command():

  def __init__(self, bot, update):
    """Salva bot, update, comando e parametri"""
    self.bot = bot
    self.update = update

    #Se ho un messaggio dato da tasto inline
    if update.callback_query:
      command_text = update.callback_query.data
    # Se il messaggio ricevuto è stato inoltrato
    elif update.message.forward_from:
      if update.message.forward_from.username == "craftlootbot":
        command_text = "/loot " + update.message.text
    #Altrimenti se si tratta di un semplice messaggio
    else:
      command_text = update.message.text

    command_text = command_text.split(" ")
    self.command = command_text[0]
    self.params = [param.strip() for param in command_text[1:]]
    print(self.command, self.params)
        
  def getattr(self, key, fallback=None):
    """Wrapper per la funzione getattr"""
    for attr in dir(self):
      if attr[1:] == key:
        return getattr(self, attr)
    return fallback
        
  def execute(self):
    method = self.getattr(self.command[1:], self.unknown_command)
    if (method.__name__.startswith("A") and
      not utils.is_admin(self.update.message.from_user.id)):
      self.answer("Non sei abilitato a usare questo comando")
    else:
      method()
            
  def answer(self, text, pretty_json=False, **options):
    """Wrapper che consente di inviare risposte testuali che superano il limite di lunghezza"""
    if not 'parse_mode' in options:
      options['parse_mode'] = "HTML"
      if pretty_json:
        text = utils.get_pretty_json(text)
      while text:
        self.update.message.reply_text(text[:4096], **options)
        text = text[4096:]
            
  def command_list(self, admin=False):
    """Ritorna la lista dei comandi disponibili"""
    commands = [command for command in dir(self)
      if command.startswith("U") or (command.startswith("A") and admin)]
    commands = {command[1:]: getattr(self, command).__doc__ for command in commands}
    return commands
    
  def unknown_command(self):
    self.answer("Ti sembra che {} sia nell'elenco?\n/help per la lista dei comandi".format(self.command))
    
  #----------------------------------------------------------------------------------

  def Ustart(self):
    """Mostra un esempio del markdown di telegram"""
    self.answer("<i>Help!</i>, <b>Help!</b>, <code>Help!</code>, <pre>Help</pre>\n/help per ottenere la lista comandi")

  def Uhelp(self):
    """Visualizza l'elenco dei comandi con relativa descrizione"""
    commands = self.command_list(utils.is_admin(
      self.update.message.from_user.id))
    commands = {"/" + command : commands.get(command) for command in commands}
    text = [key + ": " + str(value) for key, value in commands.items()]
    text = "\n".join(text)
    self.answer(text)

  def Uinline(self):
    """Esempio di comandi inline"""
    keyboard = [
      [InlineKeyboardButton(
        "Option 1",
        callback_data='1'),
      InlineKeyboardButton(
        "Option 2",
        callback_data='2')],
      [InlineKeyboardButton(
        "Option 3",
        callback_data='3')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    self.answer('Please choose:', reply_markup=reply_markup)

  def Uroll(self):
    """Lancia un dado"""
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

  def Udice2(self):
    """Lancia un dado specificando numero di facce e lanci da effettuare"""
    if(len(self.params)!=1 or all(utils.is_numeric(param) for param in self.params)):
        self.answer("Il comando funziona così:\n/dice numero_facce numero_lanci")
        return

    res="Il risultato è ["
    for counter in range(int(self.params[1])):
      res+=str(random.randint(1, int(self.params[0])))+", "

    res.rstrip(",")
    res+="]"
    self.answer(res)

  def Udice(self):
    """Lancia un dado specificando numero di facce e lanci da effettuare"""
    if (len(self.params) == 2
      and all(utils.is_numeric(param) for param in self.params)):
      text = ""
      for counter in range(int(self.params[1])):
        text += "L'esito n {} è {}\n".format(
          counter+1, random.randint(1, int(self.params[0])))
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
    """Converte test/numero da e verso una base arbitraria\n
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
    
  def Uloot(self):
    """Inoltra da @craftlootbot /lista item per ottenere il valore dell'oggetto"""
    self.answer(value(" ".join(self.params)))

  def Uwin(self):
    """Uso: /win 1 2 3 4 5; ti dice quali sono le tue probabilità di vincita contro lo gnomo avversario"""
    print("win")
    #se ci sono troppi o pochi numeri non va bene
    if len(self.params) != 5:
      self.answer("Devi inserire 5 numeri separati da spazio!")
      return

    #trasforma i parametri in una lista di int
    numeri=[int(param) for param in self.params]
    #calcola il valore della vincita
    win=(1-calc_score(numeri))*100
    self.answer("Possibilità di vincita : " + "{:.3f}".format(win) + "%")

  def Uconsiglia(self):
    """Uso: /consiglia 1 2 3 4 5; ti manda una tabella in cui:\n
    La prima colonna indica il numero che dovresti cambiare seguito da una freccietta '->' e il numero che potrebbe uscirti\n
    La seconda e terza colonna ti indicano rispettivamente la nuova probabilità di vincita (se cambi il numero) e la vecchia\n
    La terza indica di quando sale o scende la nuova probabilità"""

    # se ci sono troppi o pochi numeri non va bene
    if len(self.params) != 5:
      self.answer("Devi inserire 5 numeri separati da spazio!")
      return
    numeri = [int(param) for param in self.params]
    path2img = consigliami(numeri)
    if path2img == 0:
      self.answer("Non Cambiare !")
      return

    with open(path2img, "rb") as file:
      self.bot.sendPhoto(self.update.message.from_user.id,file)
    os.remove(path2img)

  
  # admin command ------------------------------------------------------------
  def Autente(self):
    """Visualizza le informazioni relative a un utente
Ricerca tramite username o id"""
    if self.params:
      result = utils.get_user_db(self.params[0])
      if result:
        text = utils.get_user(result)
      else:
        text = "Non ci sono utenti che rispondono ai parametri della ricerca"
    else:
      text = "Specifica id o username dell'utente che vuoi cercare"
    self.answer(text, parse_mode="Markdown")
                
  def Autenti(self):
    """Visualizza gli utenti che utilizzano un determinato bot"""
    query = """SELECT utenti.id AS user_id,
            bot.id AS bot_id
            FROM bot_users
            INNER JOIN users AS utenti ON utenti.id = id_user
            INNER JOIN users AS bot ON bot.id = id_bot
            GROUP BY utenti.id, bot.id"""
    users = execute(query)
    if users:
      text = "Elenco utenti:\n"
      for user in users:
        text += "<b>{}</b>: <code>{}</code>\n".format(
          user['bot_id'],
          user['user_id'])
    else:
      text = "Non ci sono utenti nel database"
      self.answer(text, parse_mode="Markdown")

class CraftBot():
    def __init__(self, bot, update):
        """Salva bot, update, comando e parametri"""
        self.bot = bot
        self.update = update
        self.stima = False
        self.quantity=[]
        self.costo=[]
        self.costo_craft=0


        # Se il messaggio ricevuto è stato inoltrato
        #print(update)
        if update.message.forward_from:
            if update.message.forward_from.username == "craftlootbot":
                self.command="ricerca"
                self.text=update.message.text.lower()
            elif update.message.forward_from.username == "lootplusbot":
                self.command="stima"
                self.text=update.message.text.lower()
        # Altrimenti se si tratta di un semplice messaggio
        else:
            self.command = "unknown"
            self.text=""



    def execute(self):
        if(self.command=="ricerca"): self.Dricerca()
        elif (self.command=="stima"): self.Ustima()
        else: self.unknown_command()

    def unknown_command(self):
        self.answer("C'è qualcosa di errato nel messaggio... sei sicuro di averlo inoltrato correttamente?")

    def answer(self, text, pretty_json=False, **options):
        """Wrapper che consente di inviare risposte testuali che superano il limite di lunghezza"""
        if not 'parse_mode' in options:
            options['parse_mode'] = "HTML"
            if pretty_json:
                text = utils.get_pretty_json(text)
            while text:
                self.update.message.reply_text(text[:4096], **options)
                text = text[4096:]

    def estrai_oggetti(self):

        restante = self.text.split("già possiedi")[0].split(":")[1]
        aggiornato = ""
        # print(restante)

        for line in restante.split("\n"):
            if ">" in line:
                # print(line)
                first_num = line.split()[1]
                # print(first_num)
                second_num = line.split()[3]
                # print(second_num)
                what = line.split("di ")[1]
                # print(what)
                right_num = str(int(second_num) - int(first_num))
                right_line = right_num + " su " + right_num + " di " + what
                # print(right_line)
                aggiornato += right_line + "\n"
            else:
                aggiornato += line + "\n"

        # print(aggiornato)
        regex = re.compile(r"di (.*)?\(")
        regex2 = re.compile(r"su ([0-9]) di (.*)?\(")
        lst = re.findall(regex, aggiornato)
        self.quantity = re.findall(regex2, aggiornato)
        commands = []
        # print(lst)
        last_ixd = len(lst) - len(lst) % 3
        for i in range(0, (last_ixd) - 2, 3):
            commands.append("/ricerca " + ",".join(lst[i:i + 3]))

        commands.append("/ricerca " + ",".join(lst[last_ixd:len(lst)]))
        final_string = ""

        for command in commands:
            final_string += command + "\n"

        return final_string

    def stima_parziale(self):
        prov = self.text.split("negozi per ")[1:]
        lst = []
        for elem in prov:
            lst.append((elem.split(">")[0].replace("\n", "") + elem.split(">")[1].replace("\n", "")))

        # print(lst)
        regex = re.compile(r"(.*):.*\(([0-9 .]+)")

        for elem in lst:
            e = re.findall(regex, elem)
            # print(e)

            self.costo.append((e[0][0], e[0][1].replace(".", "").replace(" ", "")))


    def Dricerca(self):
        """Condensa la lista di oggetti di @craftlootbot in comodi gruppi da 3,basta inoltrare la lista di @craftlootbot"""
        to_send = self.estrai_oggetti()
        self.costo_craft = self.text.split("per eseguire i craft spenderai: ")[1].split("§")[0].replace("'", "")

        self.answer(to_send)
        self.answer("Adesso puoi inoltrarmi tutti i risultati di ricerca di @lootplusbot per "
                                "avere il totale dei soldi da spendere. Quando hai finito usa il comando /stima "
                    "per avere le informazioni.")
        self.stima = True

    def Ustima(self):
        """ Inoltra tutte i messaggi /ricerca di @lootbotplus e digita /stima. Così otterrai il costo totale degli oggetti, la 
        top 10 di quelli piu costosi e una stima del tempo che impiegherai a comprarli tutti."""
        if not self.stima:
            self.answer("Per usare questo comando devi aver prima inoltrato la lista di @craftlootbot!")
            return
        self.stima_parziale()
        if len(self.costo) == 0: return

        # print(self.costo, self.quantity)
        tot = 0
        for (much, what) in zip(self.costo, self.quantity):
            tot += int(what[0]) * int(much[1])
        tot += int(self.costo_craft)

        self.answer("Secondo le stime di mercato pagherai " +
                                "{:,}".format(tot).replace(",", "'") + "§ , (costo craft incluso)")

        self.costo.sort(key=lambda tup: int(tup[1]), reverse=True)
        to_print = "I 10 oggetti piu costosi sono:\n"
        for i in range(1, 11):
            to_print += self.costo[i][0] + " : " + self.costo[i][1] + " §\n"

        self.answer(to_print)

        m, s = divmod(len(self.costo) * 10, 60)

        self.answer("Se compri tutti gli oggetti dal negozio impiegherai un tempo di circa : "
                                + str(m) + " minuti e " + str(s) + " secondi\n")

        self.costo.clear()
        self.quantity.clear()

