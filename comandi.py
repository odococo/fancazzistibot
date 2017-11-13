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

HELP="""Benvenuto nel FancaBot! Questo bot ha diverse funzionalità per semplificare il gioco @lootbot, di seguito 
le elencheremo tutte con il seguente formato "ESEMPIO - SPIEGAZIONE":\n
/win 1 2 3 4 5 - Usa questo comando con 5 numeri separati da spazio per avere le tue possibilità di vincita nell'ispezione dello gnomo\n
/consiglia 1 2 3 4 5 - Usa questo comando con 5 numeri separati da spazio per avere una tabella di numeri da cambiare
(la prima colonna rappresenta il numeroDaCambiare->NumeroCambiato, la seconda e la terza sono rispettivamente nuova e
la vecchia probabilità di vincita, la quarta è il decremento o incremento di probabilità in caso di cambio)\n
/dice numeroFaccie, numeroDadi - lancia un dado di numeroFaccie un quantitativo di volte pari a numeroDadi\n
/roll - lancia un dado senza specificare nulla\n
/info - ottini le informazioni riguardanti il tuo account\n
/convert base_originale-base_destinazione-valori_di_conversione testo/numero - Converte test/numero da e verso una 
base arbitraria, si possono fornire valori di conversione per personalizzare il risultato\n
/help - mostra questo messaggio\n\n
Inoltre è anche possibile usufruire delle funzionalità dell'inoltro da @craftlootbot e @lootbotplus:\n
Quando hai un lunog elenco di oggetti data da /lista in @craftlootbot, la puoi inoltrare per ottenere una comoda lista di comandi 
/ricerca da inviare a @lootbotplus. Una volta fatto questo puoi inoltrare tutti i risultati di /ricerca qui e infine confermare
premento "Stima" per ottenere il costo totale del craft, i 10 oggetti piu costosi e il tempo medio per acquistarli tutti.
Se, invece non ti interessa avere queste informazioni premi "Annulla".\n
Questo è tutto per adesso (ma siamo in continuo sviluppo!), se hai idee o suggerimenti scrivici e non tarderemo a risponderti!\n
Crediti: @brandimax @Odococo
"""

COMANDI="""
win - Usa questo comando con 5 numeri separati da spazio per avere le tue possibilità di vincita nell'ispezione dello gnomo
dice - lancia un dado di numeroFacce un quantitativo di volte pari a numeroDadi
consiglia - Usa questo comando con 5 numeri separati da spazio per avere una tabella di numeri da cambiare (maggiori info nel help)
roll - lancia un dado senza specificare nulla
info - ottini le informazioni riguardanti il tuo account
convert - Converte test/numero da e verso una base arbitraria, si possono fornire valori di conversione per personalizzare il risultato
help - mostra questo messaggio di help
"""

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
    #print(self.command, self.params)
        
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
            
  def command_list(self, admin=False, dev=False):
    """Ritorna la lista dei comandi disponibili"""
    commands = [command for command in dir(self)
      if command.startswith("U") or (command.startswith("A") and admin) or (command.startswith("D") and dev)]
    commands = {command[1:]: getattr(self, command).__doc__ for command in commands}
    return commands
    
  def unknown_command(self):
    self.answer("Ti sembra che {} sia nell'elenco?\n/help per la lista dei comandi".format(self.command))
    
  #----------------------------------------------------------------------------------

  def Ustart(self):
    """Mostra un esempio del markdown di telegram"""
    self.answer(self.help())

  def Uhelp(self):
    """Visualizza l'elenco dei comandi con relativa descrizione"""
    commands = self.command_list(utils.is_admin(
      self.update.message.from_user.id), utils.is_dev(self.bot.id))
    commands = {"/" + command : commands.get(command) for command in commands}
    text = [key + ": " + str(value) for key, value in commands.items()]
    text = "\n".join(text)
    text += """Inoltre è anche possibile usufruire delle funzionalità dell'inoltro da @craftlootbot e @lootbotplus:\n
Quando hai un lunog elenco di oggetti data da /lista in @craftlootbot, la puoi inoltrare per ottenere una comoda lista di comandi 
/ricerca da inviare a @lootbotplus. Una volta fatto questo puoi inoltrare tutti i risultati di /ricerca qui e infine confermare
premento "Stima" per ottenere il costo totale del craft, i 10 oggetti piu costosi e il tempo medio per acquistarli tutti.
Se, invece non ti interessa avere queste informazioni premi "Annulla".\n
Questo è tutto per adesso (ma siamo in continuo sviluppo!), se hai idee o suggerimenti scrivici e non tarderemo a risponderti!\n
Crediti: @brandimax @Odococo"""
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

  def Uwin(self):
    """/win 1 2 3 4 5 - Usa questo comando con 5 numeri separati da spazio per avere le tue possibilità di vincita nell'ispezione dello gnomo\n
/consiglia 1 2 3 4 5 - Usa questo comando con 5 numeri separati da spazio per avere una tabella di numeri da cambiare
(la prima colonna rappresenta il numeroDaCambiare->NumeroCambiato, la seconda e la terza sono rispettivamente nuova e
la vecchia probabilità di vincita, la quarta è il decremento o incremento di probabilità in caso di cambio)\n"""
    #print("win")
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



