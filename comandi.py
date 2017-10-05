#! /usr/bin/env python
# -*- coding: utf-8 -*-

import random
import json

import utils
from insubria import get_last_exams

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
    command_text = (update.callback_query.data 
      if update.callback_query else update.message.text).split(" ")
    self.command = command_text[0]
    self.params = [param.strip() for param in command_text[1:]]
        
  def getattr(self, key, fallback=None):
    """Wrapper per la funzione getattr"""
    for attr in dir(self):
      if attr[1:] == key:
        return getattr(self, attr)
    return fallback
        
  def execute(self):
    method = self.getattr(self.command[1:], utils.unknown_command)
    if (method.__name__.startswith("A") and
      not self.is_admin(update.message.from_user.id)):
      self.answer("Non sei abilitato a usare questo comando")
    else:
      method()
            
  def answer(self, text, **options):
    """Wrapper che consente di inviare risposte testuali che superano il limite di lunghezza"""
    if not 'parse_mode' in options:
      options['parse_mode'] = "Markdown"
      while text:
        self.update.message.reply_text(text[:4096], **options)
        text = text[4096:]
            
  def command_list(self, admin=False):
    """Ritorna la lista dei comandi disponibili"""
    commands = [command for command in dir(self) 
      if command.startswith("U") or (command.startswith("A") and admin)]
    commands = {command[1:]: getattr(self, command).__doc__ for command in commands}
    return commands
    
  #----------------------------------------------------------------------------------

  def Ustart(self):
    """Mostra un esempio del markdown di telegram"""
    self.answer("_Help!_, *Help!*, `Help!`, ```Help```\n/help per ottenere la lista comandi")

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
    print(user, type(user), str(user))
    self.answer(user)
    
  def Ujson(self):
    """Ottieni il json dell'update"""
    self.answer(update)
        
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
                text += "*{}*: `{}`\n".format(
                    user['bot_id'],
                    user['user_id'])
        else:
            text = "Non ci sono utenti nel database"
        self.answer(text, parse_mode="Markdown")
        
    # TODO /insubriaNUM per specificare quanti esami vedere
    def Ainsubria(self):
        """Ottieni informazioni relative ad un esame o uno studente"""
        if self.params:
            get_last_exams(" ".join(self.params))
        else:
            text = ("Cosa vuoi sapere?\n"
                    "/insubria matricola"
                    "/insubria corso")
