#! /usr/bin/env python
# -*- coding: utf-8 -*-

import random

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
        self.params = command_text[1:]
        
    def getattr(self, key, fallback=None):
        """Wrapper per la funzione getattr"""
        for attr in dir(self):
            if attr[1:] == key:
                return getattr(self, attr)
        return fallback
        
    def execute(self):
        method = self.getattr(self.command[1:], utils.unknown_command)
        print(method, type(method))
        if (method.startswith("A") and 
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
        """Ritorna la lista dei comandi disponibili
        
        admin: permette di filtrare i comandi per utente o admin (tutti)"""
        if(admin):
            commands = list(filter(
                lambda command: (command.startswith("U") or
                command.startswith("A")), dir(self)
            ))
        else:
            commands = list(filter(
                lambda command: command.startswith("U"), dir(self)
            ))
        commands = {command[1:]: getattr(self, command).__doc__ 
            for command in commands}
        return commands
    
    #----------------------------------------------------------------------------------

    def Ustart(self):
        """Mostra un esempio del markdown di telegram"""
        self.answer("_Help!_, *Help!*, `Help!`, ```Help```")

    def Uhelp(self):
        """Visualizza l'elenco dei comandi con relativa descrizione"""
        command = utils.command_list(self.is_admin(
            self.update.message.from_user.id))
        command = {"/" + command : command.get(command) 
            for command in command}
        text = [key + ": " + str(value) 
            for key, value in command.items()]
        text = "\n".join(text)
        self.answer(text)

    def Uinline(self):
        """Esempio di comandi inline"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "Option 1",          
                callback_data='1'),
                InlineKeyboardButton(
                    "Option 2", 
                    callback_data='2')],
            [
                InlineKeyboardButton(
                    "Option 3", 
                    callback_data='3')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        self.answer('Please choose:', reply_markup=reply_markup)

    def Uroll(self):
        """Lancia un dado"""
        keyboard = [
            # prima riga
            [InlineKeyboardButton("4", callback_data="/dice 4"),
             InlineKeyboardButton("6", callback_data="/dice 6"),
             InlineKeyboardButton("8", callback_data="/dice 8")],
            # seconda riga
            [InlineKeyboardButton("10", callback_data="/dice 10"),
             InlineKeyboardButton("12", callback_data="/dice 12"),
             InlineKeyboardButton("20", callback_data="/dice 20")],
            # terza riga
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
                # prima riga
                [InlineKeyboardButton(
                    "1", callback_data=actual_dice + " 1"),
                 InlineKeyboardButton(
                    "2", callback_data=actual_dice + " 2"),
                 InlineKeyboardButton(
                    "3", callback_data=actual_dice + " 3")],
                # seconda riga
                [InlineKeyboardButton(
                    "4", callback_data=actual_dice + " 4"),
                 InlineKeyboardButton(
                    "5", callback_data=actual_dice + " 5"),
                 InlineKeyboardButton(
                    "6", callback_data=actual_dice + " 6")],
                # terza riga
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
                    "Seleziona il numero di lanci "
                            "da effettuare:", 
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
        user = utils.get_user(utils.get_user_db(unicode(user.id)))
        self.answer(user)
        
    def Ub(self, base=None, number=False, values=None):
        """Traduce in una base a scelta del testo"""
        base = self.command[2:] if not base else base
        if not utils.is_numeric(base):
            text = "Seleziona una base valida (numerica)\n"
            if number:
                text += "Esempi: /dec2b2 (binario) /dec2b8 (base8) /dec2b16 (base16)"
            else:
                text += "Esempi: /b2 (base2) /b8 (base8) /b16 (base16)"
        else:
            if not self.params:
                text = "Cosa vuoi convertire? {} valore".format(self.command)
            else:
                converted_text = self.convert_value_to(int(base), 
                    "".join(self.params), values, number)
                text = "Valore per valore: {}\n\nStringa unica: `{}`".format(
                    " ".join(converted_text), "".join(converted_text))
        self.answer(text)
    
    def Udec2b(self):
        """Converte un numero in una base a piacere"""
        self.getattr("b")(self.command[6:], True)
        
    def Ubb(self):
        """Converte un testo in una base a piacere.
        Bisogna specificare, tramite stringa unica al primo parametro,
        i valori corrispondenti ad ogni valore convertito"""
        base = self.command[3:]
        if not self.params[0]:
            self.answer("Non hai specificato la tabella di valori corrispondenti")
        elif len(self.params[0]) == int(base):
            self.getattr("b")(base, values=self.params.pop(0))
        else:
            self.answer("Base e lunghezza della tabella non coincidono")
    
    def Udec2bb(self):
        """Converte un numero in una base a piacere.
        Bisogna specificare, tramite stringa al primo parametro,
        i valori corrispondenti ad ogni valore convertito"""
        base = self.command[7:]
        if not self.params[0]:
            self.answer("Non hai specificato la tabella di valori corrispondenti")
        elif len(self.params[0]) == int(base):
            self.getattr("b")(base, True, self.params.pop(0))
        else:
            self.answer("Base e lunghezza della tabella non coincidono")
    
    def Ubin(self):
        """Converte un testo in binario"""
        self.getattr("b")(2)
    
    def Udec2bin(self):
        """Converte un numero o testo in binario"""
        self.getattr("b")(2, True)
        
    def Uoct(self):
        """Converte un testo in ottale"""
        self.getattr("b")(8)
        
    def Udec2oct(self):
        """Converte un numero in ottale"""
        self.getattr("b")(8, True)
        
    def Uhex(self):
        """Converte un testo in esadecimale"""
        self.getattr("b")(16, values="0123456789ABCDEF")
        
    def Udec2hex(self):
        """Converte un numero in esadecimale"""
        self.getattr("b")(16, True, "0123456789ABCDEF")
        
    def base64(self):
        """Converte testo in base64"""
        command = update.message.text.split(" ")
        text_to_convert = "".join(command[1:])
        if len(command) > 1:
            text1 = "".join(self.convert_value_to(64, text_to_convert, 
                ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                 "abcdefghijklmnopqrstuvwxyz"
                 "0123456789+/")))
            text2 = "".join(self.convert_value_to(64, text_to_convert,
                ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "abcdefghijklmnopqrstuvwxyz"
                "0123456789-_")))
            while len(text1) % 4 != 0:
                text1 += "="
            while len(text2) % 4 != 0:
                text2 += "="
            text = "Con + e /: `{}`\n\nCon - e \_: `{}`".format(text1, text2)
        else:
            text = "Cosa vuoi convertire? /base64 testo"
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
