#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Small script to show PostgreSQL and Pyscopg together
#

import logging
import json
import os
from functools import wraps
from urllib import parse
import psycopg2
import psycopg2.extras
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import utils

# todo: db_call dovrebbe diventare una calsse

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


TABELLE = {
            "id_users": {
                "create": {"normal": """CREATE TABLE IF NOT EXISTS id_users(
              id integer PRIMARY KEY,
              admin boolean DEFAULT false,
              tester boolean DEFAULT false,
              loot_user boolean DEFAULT false,
              loot_admin boolean DEFAULT false,
              banned boolean DEFAULT false)""",
                           "banned": """CREATE TABLE IF NOT EXISTS id_users(
              id integer PRIMARY KEY,
              admin boolean DEFAULT false,
              tester boolean DEFAULT false,
              loot_user boolean DEFAULT false,
              loot_admin boolean DEFAULT false,
              banned boolean DEFAULT true)"""},
                "drop": """DROP TABLE IF EXISTS id_users CASCADE""",
                "select": {
                    'all': """SELECT * FROM id_users""",
                    'from_id': """SELECT * FROM id_users WHERE id = %s"""
                },
                "insert": {
                    'single_id': """INSERT INTO id_users (id) 
                            VALUES(%s)
                            ON CONFLICT(id) DO NOTHING""",
                    'complete_user': """INSERT INTO id_users (id ,admin, tester, loot_user, loot_admin, banned)
                                VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING;"""},
                "update": """UPDATE id_users
              SET admin = %s, tester = %s, loot_user = %s, loot_admin = %s, banned = %s
              WHERE id = %s""",
                "delete": """DELETE FROM id_users
              WHERE id = %s"""
            },
            "users": {
                "create": """CREATE TABLE IF NOT EXISTS users(
              id integer REFERENCES id_users ON DELETE CASCADE,
              username varchar(255),
              first_name varchar(255),
              last_name varchar(255),
              language_code varchar(10),
              date timestamp DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(id, date))""",
                "drop": """DROP TABLE IF EXISTS users CASCADE""",
                "select": {
                    'all': """SELECT * FROM users""",
                    'from_username': """SELECT * 
                       FROM users NATURAL JOIN id_users
                       WHERE username = %s AND date >= ALL(SELECT date
                        FROM users
                        WHERE username = %s)""",
                    'from_id': """SELECT *
              FROM users NATURAL JOIN id_users
              WHERE id = %s AND date >= ALL(SELECT date
                FROM users
                WHERE id = %s)"""

                },
                "insert": """INSERT INTO users (id, username, first_name, last_name, language_code)
              VALUES (%s, %s, %s, %s ,%s)""",
                "update": """UPDATE users
              SET username = %s, first_name = %s, last_name = %s, language_code = %s
              WHERE id = %s""",
                "delete": """DELETE FROM users
              WHERE id = %s"""
            },
            "bot_users": {
                "create": """CREATE TABLE IF NOT EXISTS bot_users(
              id_bot integer REFERENCES id_users ON DELETE CASCADE,
              id_user integer REFERENCES id_users ON DELETE CASCADE,
              date timestamp DEFAULT CURRENT_TIMESTAMP,
              language varchar(10),
              PRIMARY KEY(id_bot, id_user))""",
                "drop": """DROP TABLE IF EXISTS bot_users CASCADE""",
                "select": {
                    'all': """SELECT * FROM bot_users"""
                },
                "insert": """INSERT INTO bot_users (id_bot, id_user, language)
              VALUES (%s, %s, %s)
              ON CONFLICT (id_bot, id_user) DO UPDATE
              SET language = EXCLUDED.language""",
                "update": """UPDATE bot_users
              SET language = %s
              WHERE id_bot = %s AND id_user = %s""",
                "delete": """DELETE FROM bot_users
              WHERE id_bot = %s AND id_user = %s"""
            },
            "activity": {
                "create": """CREATE TABLE IF NOT EXISTS activity(
              id serial PRIMARY KEY,
              id_bot integer REFERENCES id_users ON DELETE CASCADE,
              id_user integer REFERENCES id_users ON DELETE CASCADE,
              content text NOT NULL,
              date timestamp DEFAULT CURRENT_TIMESTAMP,
              type varchar(20))""",
                "drop": """DROP TABLE IF EXISTS activity CASCADE""",
                "select": {
                    'all': """SELECT * FROM activity"""
                },
                "insert": """INSERT INTO activity (id_bot, id_user, content, type)
              VALUES (%s, %s, %s ,%s)""",
                "update": """UPDATE activity
              SET type = %s
              WHERE id = %s""",
                "delete": """DELETE FROM activity
              WHERE id = %s"""
            },
            "punteggio": {
                "create": """CREATE TABLE IF NOT EXISTS punteggio(
              id_user integer REFERENCES id_users ON DELETE CASCADE,
              valutazione numeric(1) DEFAULT 0,
              msg_id integer DEFAULT 0,
              PRIMARY KEY(id_user))""",
                "drop": """DROP TABLE IF EXISTS punteggio CASCADE""",
                "select": {
                    'all': """SELECT * FROM punteggio """,
                    'all_and_users': """SELECT * FROM punteggio NATURAL JOIN users"""
                },
                "insert": """INSERT INTO punteggio (id, valutazione, msg_id, attacchi)
              VALUES (%s, %s, %s, %s)
              ON CONFLICT(id_user) DO UPDATE
              SET valutazione = EXCLUDED.valutazione, msg_id = 0""",
                "update": """UPDATE punteggio 
                    SET valutazione = %s ,msg_id =%s, attacchi=%s   
                    WHERE id = %s;""",
                "reset": """update punteggio set (msg_id , valutazione, attacchi) = (0 ,0,0)""",
                "delete": """DELETE FROM punteggio
              WHERE id_user = %s"""
            }
        }

developer_dicts = {"brandimax": 24978334}  # , "odococo":89675136}


class DB:
    def __init__(self):


        self.connect_db()

    # aggiunge un utente al database
    def add_user(self, user, id_bot=None):
        # salvo l'id dell'utente o del bot
        self.execute(TABELLE['id_users']['insert'], (user['id'],))
        # salvo le altre informazioni relative ad utenti o bot
        # queste informazioni potrebbero cambiare nel tempo, quindi
        # prima di tutto selezione le ultime informazioni note dal database
        # se sono uguali ignoro, altrimenti effettuo un inserimento
        user_db = self.get_user(user['id'])
        if self.different_user(user, user_db):
            self.execute(TABELLE['users']['insert'],
                         (user['id'], user['username'], user['first_name'], user['last_name'], user['language_code']))
        if id_bot is not None:
            self.execute(TABELLE['bot_users']['insert'], (id_bot, user['id'], user['language_code']))

    def ban_user(self, user):
        # salvo l'id dell'utente o del bot
        print("Sto negando l'accesso all'user " + str(user['id']))
        self.execute(TABELLE['id_users']['insert']['complete_user'],
                     (user['id'], False, False, False, False, True))

    def save_new_user(self, user):
        print("Saving new user")
        self.execute(TABELLE['id_users']['insert']['complete_user'],
                     (user['id'], False, False, True, False, False))
        self.execute(TABELLE['users']['insert'],
                     (user['id'], user['username'], user['first_name'], user['last_name'], user['language_code']))

    def reset_punteggio(self):
        self.execute(TABELLE['punteggio']['reset'])

    # aggiunge un bot al database. Il bot ha le medesime caratteristiche di un utente
    def add_bot(self, bot):
        self.add_user(bot)

    def get_users(self):
        return self.execute(TABELLE['users']['select']['all'])

    def delete_user(self, user):
        self.execute(TABELLE['id_users']["delete"], user["id"])

    def get_user(self, key_value):
        if utils.is_numeric(key_value):
            key_value = int(key_value)
            query = TABELLE['users']['select']['from_id']
        else:
            if key_value[0] == '@':
                key_value = key_value[1:]
            query = TABELLE['users']['select']['from_username']
        user = self.execute(query, (key_value, key_value))
        return user

    def get_id_users(self):
        return self.execute(TABELLE['id_users']['select']['all'])

    def update_user(self, user):
        query = TABELLE['id_users']['update']
        return self.execute(query,
                            (user['admin'], user['tester'], user['loot_user'], user['loot_admin'], user['banned'],
                             user['id']))

    # ritorna l'elenco dei punteggi
    def get_punteggi(self):
        query = TABELLE['punteggio']['select']['all']
        return self.execute(query)

    # aggiungi un punteggio
    def add_punteggio(self, id, punteggio):
        query = TABELLE['punteggio']['insert']
        return self.execute(query, (id, punteggio))

    # -------------------------------------------------------------------------------
    # essendoci anche la data, non posso fare il controllo direttamente da db
    def different_user(self, userA, userB):
        if (userB and (userA['id'] == userB['id']) and
                (userA['username'] == userB['username']) and
                (userA['first_name'] == userB['first_name']) and
                (userA['last_name'] == userB['last_name']) and
                (userA['language_code'] == userB['language_code'])):
            return False
        return userA

    def salva_punteggi_in_db(self, dizionario, is_single):
        print("DIZIONARIO\n\n")
        print(dizionario)
        print("\n\n")
        """Salva il i punteggi aggiornati, se is_single==True allora dizionario è un semplice dizionario
        altrimenti è una lista di dizionari"""
        if is_single:
            if not isinstance(dizionario['attacchi'], int): dizionario['attacchi'] = dizionario['attacchi'][1]
            self.execute(TABELLE['punteggio']['insert'],
                         (dizionario['id'], dizionario['valutazione'], dizionario['msg_id'], dizionario['attacchi']))
        else:
            for elem in dizionario:
                attacchi = 0
                if not isinstance(elem['attacchi'], int):
                    # print("tuple!")
                    attacchi = int(elem['attacchi'][1])
                    # print(attacchi)
                self.execute(TABELLE['punteggio']['insert'],
                             (elem['id'], elem['valutazione'], elem['msg_id'], attacchi))

    # esegue una query arbitraria
    @staticmethod
    def execute(query, param=None):
        cursor = DB.connect_db();
        if cursor is not None:
            try:
                cursor.execute(query, param)
                if "SELECT" in query:
                    if cursor.rowcount == 1:
                        return dict(cursor.fetchone())
                    else:
                        return [dict(record) for record in cursor]
                elif "RETURNING" in query:
                    if cursor.rowcount:
                        return [dict(record) for record in cursor]
                    else:
                        return True
                else:
                    return True
            except Exception as error:
                print("ERRORE {} \n{}\n{}".format(error, query, param))
                return False


                # connessione al db

    @staticmethod
    def connect_db():
        try:
            parse.uses_netloc.append("postgres")
            url = parse.urlparse(os.environ["DATABASE_URL"])
            conn = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
            )
            conn.autocommit = True
            return conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        except Exception as error:
            logger.error("Errore nella connessione al database: {}".format(error))
            return None

#==============================ACCESS METHODS=======================================================

    def elegible_user(self, func):
        @wraps(func)
        def check_if_user_can_interact(bot, update, *args, **kwargs):
            """Questa funzione ritorna true se l'user puo interagire, altrimenti false
            inoltre in caso di false (user non presente nel db inizia il procedimento di richiesta d'accesso"""
            user_id = update._effective_user
            # print("cerco user con id " + str(user_id) + ", nel database")
            user = DB.execute(TABELLE["id_users"]["select"]["from_id"], (user_id['id'],))
            # print("ho trovato : " + str(user))
            if not user:
                self.request_access(bot, user_id)
                return
            elif user["banned"]:
                update.message.reply_text("Spiacente sei stato bannato dal bot")
                return
            else:
                return func(bot, update, *args, **kwargs)

        return check_if_user_can_interact




    def elegible_admin(self, func):
        @wraps(func)
        def check_if_admin(bot, update, *args, **kwargs):
            """Questa funzione ritorna true se l'user puo interagire, altrimenti false
            inoltre in caso di false (user non presente nel db inizia il procedimento di richiesta d'accesso"""
            user_id = update._effective_user
            # print("cerco user con id " + str(user_id) + ", nel database")
            user = DB.execute(TABELLE["id_users"]["select"]["from_id"], (user_id['id'],))
            # print("ho trovato : " + str(user))
            if not user:
                self.request_access(bot, user_id)
                return
            elif user["banned"]:
                update.message.reply_text("Spiacente sei stato bannato dal bot")
                return
            elif user["admin"]:
                return func(bot, update, *args, **kwargs)
            else:
                update.message.reply_text("Non sei abilitato ad usare questo comando")
                return

        return check_if_admin

    def grant_deny_access(self ,bot, update):
        text = update.callback_query.data.split(" ")
        command = text[0]
        user_lst = text[1:]
        user = {"id": user_lst[0], "username": user_lst[1], "first_name": user_lst[2], "last_name": user_lst[3],
                "language_code": user_lst[4]}
        if (command.strip("/") == "consentiAccessoSi"):
            # print("Accesso garantito")
            self.save_new_user(user)
            bot.send_message(user["id"], "Ti è stato garantito l'accesso al bot!")
            for dev in developer_dicts.values():
                bot.send_message(dev, "L'accesso a user : " + str(user["username"]) + ", è stato garantito")
        else:
            # print("Accesso negato")
            bot.send_message(user["id"], "Non ti è stato garantito l'accesso al bot :(")
            self.ban_user(user)
            for dev in developer_dicts.values():
                bot.send_message(dev, "L'accesso a user : " + str(user["username"] + ", è stato negato"))

    def request_access(self, bot, user):
        to_send = "L'utente :\nid: " + str(user["id"]) + "\nusername: " + str(user["username"]) + "\nfirst_name: " + \
                  str(user["first_name"]) + "\nlast_name: " + str(
            user["last_name"]) + "\n" + "\nHa richiesto l'accesso a " + \
                  str(bot.username) + "\nConsenti?"
        user = str(user["id"]) + " " + str(user["username"]) + " " + str(user["first_name"]) + " " + str(
            user["last_name"]) + " " + str(user["language_code"])
        # print(to_send)
        for dev in developer_dicts.values():
            bot.send_message(dev, to_send, reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Si", callback_data="/consentiAccessoSi " + user),
                InlineKeyboardButton("No", callback_data="/consentiAccessoNo " + user)
            ]]))
