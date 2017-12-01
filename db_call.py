#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Small script to show PostgreSQL and Pyscopg together
#

import logging
import os
from functools import wraps
from inspect import signature
from urllib import parse

import psycopg2
import psycopg2.extras
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import utils

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
            'all_id': """SELECT * FROM id_users""",
            'from_id': """SELECT * FROM id_users WHERE id = %s""",
            'all': """SELECT * FROM id_users NATURAL JOIN users"""
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
        "insert": """INSERT INTO users (id, username)
              VALUES (%s, %s)""",
        "update": """UPDATE users
              SET username = %s,
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
            'all': """SELECT * FROM bot_users""",
            'by_ids': """SELECT * FROM bot_users WHERE id_user=%s and id_bot=%s"""
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
              ON CONFLICT(id) DO UPDATE
              SET valutazione = EXCLUDED.valutazione, msg_id = 0""",
        "update": """UPDATE punteggio 
                    SET valutazione = %s ,msg_id =%s, attacchi=%s   
                    WHERE id = %s;""",
        "reset": """update punteggio set (msg_id , valutazione, attacchi) = (0 ,0,0)""",
        "delete": """DELETE FROM punteggio
              WHERE id = %s"""
    },
    "bot": {
        "select": {
            "by_id": """SELECT * FROM bot WHERE id= %s""",
            "all": """SELECT * FROM bot"""
        }
    },
    "items": {
        "select": {
            'select': 'SELECT * FROM items',
            'by_id': 'SELECT * FROM items WHERE id = %s'
        },
        'insert': {
            'new_user': "INSERT INTO items VALUES(%s, 0,0,0,0,0,0,0,0)"
        },
        'update': """UPDATE items
              SET c = %s, nc = %s, r = %s, ur = %s, l = %s, e=%s,  u=%s, ue=%s
              WHERE id = %s""",
        'reset': """UPDATE items SET c=0, nc=0, r=0, ur=0, l=0, e=0, u=0, ue=0 WHERE id =%s""",
        'delete': "DELETE FROM items WHERE id = %s"
    }
}

COMANDO_CONNESSIONE_HEROKU_DB = "heroku pg:psql"#comando per connettersi al db

developer_dicts = {"brandimax": 24978334, "odococo": 89675136}
developer_message = []#usata per salvare i messaggi di richiesta accesso


class DB:
    def __init__(self):

        self.connect_db()

    # ============GETTER======================================
    def get_token(self, bot_id):
        res = self.execute(TABELLE['bot']['select']['by_id'], (bot_id,))
        # print(res)
        return res

    def get_user_items(self, id):
        return self.execute(TABELLE['items']['select']['by_id'], (id,))

    def get_users(self):
        return self.execute(TABELLE['users']['select']['all'])

    def get_users_and_id(self):
        return self.execute(TABELLE['id_users']['select']['all'])

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

    def get_permission_user(self, user_id):
        return self.execute(TABELLE["id_users"]['select']['from_id'], (user_id,))

    def get_punteggi(self):
        query = TABELLE['punteggio']['select']['all']
        return self.execute(query)

    def get_punteggi_username(self):
        return self.execute(TABELLE['punteggio']['select']['all_and_users'])


    # ============ADDER/UPDATER======================================
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

    def add_user_to_items(self, id):
        item_users = self.execute(TABELLE['items']['select']['select'])
        # print("item_users",item_users)
        if not item_users:  # se il db è vuoto
            self.execute(TABELLE['items']['insert']['new_user'], (id,))
            return

        if not isinstance(item_users, list): item_users = [item_users]
        # print(item_users)

        for user in item_users:
            if id == user['id']: return  # se lo user è gia presente nel db lascio stare

        # se sono arrivato qua lo user non è nel db e quindi lo aggiungo
        self.execute(TABELLE['items']['insert']['new_user'], (id,))

    def add_bot(self, bot):
        self.add_user(bot)

    def add_punteggio(self, id, punteggio):
        query = TABELLE['punteggio']['insert']
        return self.execute(query, (id, punteggio))

    def update_items(self, items_us, id):

        items_db = self.execute(TABELLE['items']['select']['by_id'], (id,))

        for key in items_us.keys():
            items_db[key.lower()] += items_us[key]

        # print(items_db)

        self.execute(TABELLE['items']['update'], (
            items_db['c'],
            items_db['nc'],
            items_db['r'],
            items_db['ur'],
            items_db['l'],
            items_db['e'],
            items_db['u'],
            items_db['ue'],
            id
        ))

    def update_user(self, user):
        query = TABELLE['id_users']['update']
        return self.execute(query,
                            (user['admin'], user['tester'], user['loot_user'], user['loot_admin'], user['banned'],
                             user['id']))

    def add_new_user(self, user):
        # print("Saving new user")
        self.execute(TABELLE['id_users']['insert']['complete_user'],
                     (user['id'], False, False, True, False, False))

        self.execute(TABELLE['users']['insert'],
                     (user['id'], user['username']))

    def update_punteggi(self, dizionario):
        """Salva il i punteggi aggiornati aggiornandoli in caso gia fossero presenti oppure aggiungendoli altrimenti"""

        for elem in dizionario:
            self.execute(TABELLE['punteggio']['insert'],
                         (elem['id'], elem['valutazione'], elem['msg_id'], elem['attacchi']))

    def add_bot_user(self, effective_user, bot_id):
        self.execute(TABELLE['bot_users']['insert'],(bot_id, effective_user['id'],effective_user['language_code'],))

    # ============DELETE/RESET======================================
    def ban_user(self, user):
        # salvo l'id dell'utente o del bot
        # print("Sto negando l'accesso all'user " + str(user['id']))
        self.execute(TABELLE['id_users']['insert']['complete_user'],
                     (user['id'], False, False, False, False, True))

    def delete_from_all(self, user_id):
        self.execute(TABELLE['id_users']['delete'], (user_id,))
        self.execute(TABELLE['users']['delete'], (user_id,))
        self.execute(TABELLE['punteggio']['delete'], (user_id,))
        self.execute(TABELLE['items']['delete'], (user_id,))

    def reset_punteggio(self):
        self.execute(TABELLE['punteggio']['reset'])

    def reset_rarita_user(self, id):
        self.execute(TABELLE['items']['reset'], (id,))

    def delete_user(self, user):
        self.execute(TABELLE['id_users']["delete"], user["id"])

    def different_user(self, userA, userB):
        if (userB and (userA['id'] == userB['id']) and
                (userA['username'] == userB['username']) and
                (userA['first_name'] == userB['first_name']) and
                (userA['last_name'] == userB['last_name']) and
                (userA['language_code'] == userB['language_code'])):
            return False
        return userA

    # ============================STATIC METHODS===================================
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

            # ==============================ACCESS METHODS=======================================================

    # ===============================ACCESS TO BOT===========================================
    def elegible_loot_user(self, func):
        """questa funzione ha il compito di verificare se l'id utente è abilitato a chiamare il comando
        il suo utilizzo è il seguente:
        data la funzione command che deve essere wrappata, si può creare una nuova funzione elegible_user(command) """

        @wraps(func)
        def check_if_user_can_interact(bot, update, *args, **kwargs):
            """Questa funzione ritorna true se l'user puo interagire, altrimenti false
            inoltre in caso di false (user non presente nel db inizia il procedimento di richiesta d'accesso"""

            user_id = update._effective_user
            # print("cerco user con id " + str(user_id) + ", nel database")
            user = DB.execute(TABELLE["id_users"]["select"]["from_id"], (user_id['id'],))
            # print("ho trovato : " + str(user))
            if not user:#user non prensete nel db id_users
                if 'private' in update.message.chat.type:# se il messaggio è stato mandato in privata allora devo chiedere l'accesso
                    self.request_access(bot, user_id)
                elif 'supergroup' in update.message.chat.type:# altrimenti guardo se è presente nei bot_users
                    bot_users=DB.execute(TABELLE['bot_users']['select']['by_ids'],(user_id, bot.id))
                    if not bot_users:#se non è presente glielo dico e lo salvo nel db
                        update.message.reply_text("E tu chi sei? Non ti ho mai visto da queste parti..."
                                                  "Perche non mi invii un bel messaggio di start cosi diventiamo amici?",
                                                  reply_to_message_id=update.message.message_id)
                        self.add_bot_user(update._effective_user, bot.id)

                return
            elif user["banned"]:
                update.message.reply_text("Spiacente sei stato bannato dal bot")
                return
            else:
                sig = signature(func)
                if len(sig.parameters) > 1:
                    return func(bot, update, *args, **kwargs)
                else:
                    return func(*args, **kwargs)




        return check_if_user_can_interact

    def elegible_admin(self, func):
        """stesso compito della funzione elegible_user, solo che verifica anche se l'id è admin"""

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
                sig = signature(func)
                if len(sig.parameters) > 1:
                    return func(bot, update, *args, **kwargs)
                else:
                    return func(*args, **kwargs)
            else:
                update.message.reply_text("Non sei abilitato ad usare questo comando")
                return

        return check_if_admin

    def elegible_loot_admin(self, func):
        """stesso compito della funzione elegible_user, solo che verifica anche se l'id è loot_admin"""

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
            elif user["loot_admin"] or user["admin"]:
                sig = signature(func)
                if len(sig.parameters) > 1:
                    return func(bot, update, *args, **kwargs)
                else:
                    return func(*args, **kwargs)
            else:
                update.message.reply_text("Non sei abilitato ad usare questo comando")
                return

        return check_if_admin

    def elegible_tester(self, func):
        """stesso compito della funzione elegible_user, solo che verifica anche se l'id è tester"""

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
            elif user["tester"]:
                sig = signature(func)
                if len(sig.parameters) > 1:
                    return func(bot, update, *args, **kwargs)
                else:
                    return func(*args, **kwargs)
            else:
                update.message.reply_text("Non sei abilitato ad usare questo comando")
                return

        return check_if_admin

    @utils.catch_exception
    def grant_deny_access(self, bot, update):
        """Funziona tramite callback query e serve a garantire l'accesso o meno all'udente id"""
        text = update.callback_query.data.split(" ")
        command = text[0]
        user_lst = text[1:]
        user = {"id": user_lst[0], "username": " ".join(user_lst[1:])}
        if (command.strip("/") == "consentiAccessoSi"):
            if DB.execute(TABELLE["id_users"]["select"]["from_id"], (user['id'],)):
                for msg in developer_message:
                    bot.edit_message_text(
                        chat_id=msg.chat_id,
                        text="Lo user : " + str(user["username"]) + ", è gia presente nel db",
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                return

            # print("Accesso garantito")
            self.add_new_user(user)
            bot.send_message(user["id"], "Ti è stato garantito l'accesso al bot!")

            for msg in developer_message:
                bot.edit_message_text(
                    chat_id=msg.chat_id,
                    text="L'accesso a user : " + str(user["username"]) + ", è stato garantito",
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )

        else:
            # print("Accesso negato")
            bot.send_message(user["id"], "Non ti è stato garantito l'accesso al bot :(")
            self.ban_user(user)
            for msg in developer_message:
                bot.edit_message_text(
                    chat_id=msg.chat_id,
                    text="L'accesso a user : " + str(user["username"]) + ", è stato negato",
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )

        developer_message.clear()

    @utils.catch_exception
    def request_access(self, bot, user):
        """Invia la richiesta di accesso ai comandi agli id presenti in veleloper_dict"""
        to_send = "L'utente :\nid: " + str(user["id"]) + "\nusername: " + str(user["username"]) + "\nfirst_name: " + \
                  str(user["first_name"]) + "\nlast_name: " + str(
            user["last_name"]) + "\n" + "\nHa richiesto l'accesso a " + \
                  str(bot.username) + "\nConsenti?"
        user = str(user["id"]) + " " + str(user["username"])
        # print(to_send,user)
        for dev in developer_dicts.values():
            developer_message.append(bot.send_message(dev, to_send, reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Si", callback_data="/consentiAccessoSi " + user),
                InlineKeyboardButton("No", callback_data="/consentiAccessoNo " + user)
            ]]), one_time_keyboard=True))
