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

from Other import utils

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
            'all': """SELECT * FROM id_users NATURAL JOIN users""",
            'banned':"""SELECT * FROM id_users WHERE banned = true"""
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
        "update": """UPDATE users SET username = %s  WHERE id = %s""",
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
              id_user integer REFERENCES id_users ON DELETE CASCADE,
              content text NOT NULL,
              date timestamp DEFAULT CURRENT_TIMESTAMP,
              type text)""",
        "drop": """DROP TABLE IF EXISTS activity CASCADE""",
        "select": {
            'all': """SELECT * FROM activity""",
            "by_type":"""SELECT * FROM activity WHERE type=%s""",
            "by_user": """SELECT * FROM activity WHERE id_user=%s""",
            "by_date_min": """SELECT * FROM activity WHERE date<=%s""",
            "by_date_max": """SELECT * FROM activity WHERE date>=%s""",
        },
        "insert": """INSERT INTO activity ( id_user, content, type)
              VALUES (%s, %s ,%s)""",
        "update": {
            "type":""""UPDATE activity SET type = %s WHERE id = %s""",
            "sentiment":"""UPDATE activity SET sentiment =%s WHERE id=%s"""

        },

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
    },
    "all": {
        "delete": """DELETE FROM punteggio WHERE id = %s;
                    DELETE FROM activity WHERE id = %s;
                    DELETE FROM users WHERE id = %s;
                    DELETE FROM id_users WHERE id = %s"""
    },
    "top": {
        "insert": """INSERT INTO top ( pc_tot , pc_set,  money,  ability,  rango,  id, agg ) VALUES 
                    (%s,%s,%s,%s,%s,%s, CURRENT_TIMESTAMP) ON CONFLICT(id) DO UPDATE SET pc_tot=EXCLUDED.pc_tot, 
                      pc_set=EXCLUDED.pc_set, money=EXCLUDED.money, ability=EXCLUDED.ability,
                       rango=EXCLUDED.rango, agg=CURRENT_TIMESTAMP""",
        "select": {
            "all": "SELECT * FROM top NATURAL JOIN users;"
        }
    },
    "teams": {
        "select": {
            "all_ordered": "SELECT numero, pc, update FROM teams WHERE team = %s ORDER BY numero",
            "all": "SELECT nome, numero, pc, update FROM teams"},
        "insert": """INSERT INTO teams (nome , numero, pc, update) VALUES (%s, %s, %s, CURRENT_TIMESTAMP) ON CONFLICT(nome, numero) DO NOTHING""",
        "delete": {
            "by_date_today": "DELETE FROM teams WHERE update < CURRENT_TIMESTAMP",
            "by_date": "DELETE FROM teams WHERE update < %s",
            "by_team": "DELETE FROM teams WHERE nome=%s",
            "all": "DELETE FROM teams"
        }
    },
    "contest_creator": {
        "select": {
            "creator": "SELECT creator_id, creator_username FROM contest_creator",
            "rules": "SELECT rules FROM contest_creator",
            "rewards": "SELECT rewards FROM contest_creator",
            "min_max": "SELECT min_participants, max_participants FROM contest_creator",
        },
        "insert": "INSERT INTO contest_creator (creator_id , creator_username, rules, rewards, min_participants, max_participants)"
                  " VALUES (%s, %s, %s, %s, %s, %s)",
        "delete": "DELETE FROM contest_creator"
    },
    "bugs":{
        "insert":"INSERT INTO bugs (bug,id) VALUES (%s, %s)",
        "delete":"DELETE FROM bugs WHERE id=%s",
        "select":"SELECT * FROM bugs"
    },
    "activity_points":{
        "update":{
                "win":"UPDATE activity_points SET points=points + %s where id=%s",
                "loose":"UPDATE activity_points SET points=points + %s where id=%s"},
        "insert":"INSERT INTO activity_points ( id, points) VALUES (%s, 0) ON CONFLICT (id) DO NOTHING",
        "select":{
            "by_id":"SELECT * FROM activity_points WHERE id=%s",
            "all":"SELECT * FROM activity_points NATURAL JOIN users"}

    }
}

COMANDO_CONNESSIONE_HEROKU_DB = "heroku pg:psql"  # comando per connettersi al db

developer_dicts = {"brandimax": 24978334, "odococo": 89675136}
developer_message = []  # usata per salvare i messaggi di richiesta accesso


class DB:
    """Classe per gestire l'interfacciamento con il database"""

    def __init__(self):

        self.connect_db()

    # ============GETTER======================================
    def get_token(self, bot_id):
        """Prende tutti i bot nella tabella bot
        @:param bot_id
        @:type: int
         @:return: dizionario del bot """
        res = self.execute(TABELLE['bot']['select']['by_id'], (bot_id,))
        # print(res)
        return res

    def get_user_items(self, id):
        """Prende tutti gli user in items
        @:param id: id dello user
        @:type: int
         @:return: lista (o dizionario dipende da quanti user ci sono) di utenti """
        return self.execute(TABELLE['items']['select']['by_id'], (id,))

    def get_users(self):
        """Prende tutti gli user in users
         @:return: lista (o dizionario dipende da quanti user ci sono) di utenti """
        return self.execute(TABELLE['users']['select']['all'])

    def get_users_and_id(self):
        """Prende tutti gli user in id_users
         @:return: lista (o dizionario dipende da quanti user ci sono) di utenti """
        return self.execute(TABELLE['id_users']['select']['all'])

    def get_user(self, key_value):
        """Prende l'user dalla tabella users
        @:param key_value: valore secondo cui si cerca l'utente (id o username)
        @:type: int o str
         @:return:  dizionario dell'utente """
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
        """Prende tutti gli user in id_users
         @:return: lista (o dizionario dipende da quanti user ci sono) di utenti """
        return self.execute(TABELLE['id_users']['select']['all'])

    def get_permission_user(self, user_id):
        """Prende i permessi dello user specificato
        @:param user_id: id dello user di cui vuoi sapere le info
        @:type: dict
         @:return: dizionario dello user specificato """
        return self.execute(TABELLE["id_users"]['select']['from_id'], (user_id,))

    def get_punteggi(self):
        """Prende tutti gli user in punteggi tranne lo username
         @:return: lista (o dizionario dipende da quanti user ci sono) di utenti """
        query = TABELLE['punteggio']['select']['all']
        return self.execute(query)

    def get_punteggi_username(self):
        """Prende tutti gli user in punteggi insieme allo username
         @:return: lista (o dizionario dipende da quanti user ci sono) di utenti """
        return self.execute(TABELLE['punteggio']['select']['all_and_users'])

    def get_all_top(self):
        """Prende tutti gli user in top
        @:return: lista (o dizionario dipende da quanti user ci sono) di utenti """
        return self.execute(TABELLE['top']['select']['all'])

    def get_team_ordered(self):
        """Prende tutti gli elementi dentro team"""
        return self.execute(TABELLE['teams']['select']['all_ordered'])

    def get_team_all(self):
        return self.execute(TABELLE['teams']['select']['all'])

    def get_key_contest_creator(self, keys):
        """Prende gli elementi dentro key dalla tabella contest_creator
        @:param key: lista di stringhe contenenti le chiavi del dizionario TABELLE['constest_creator']['select']
        @:type: list of str
        @:return: lista di valori contenuti dentro la tabella nell'ordine in cui sono stati richiesti in keys"""

        res = []
        for key in keys:
            res.append(self.execute(TABELLE['constest_creator']['select'][key], ()))

        return res

    def get_bugs(self):
        """Return all bugs in table bugs"""
        return self.execute(TABELLE['bugs']['select'])

    def get_banned(self):
        """Ritorna tutti gli id degli utenti bannati"""
        return self.execute(TABELLE['id_users']['select']['banned'])

    def get_activity(self, type=False,user=False,date_min=False,date_max=False):
        """Ritorna la lista delle activity a seconda della chiave specificata
        @:param type: stringa rappresentante il tipo (guarda dentro track_activity)
        @:param user: id dello user in int
        @:param date_min: datetime object con la data
        @:param date_max: datetime object con la data"""

        if type:
            return self.execute(TABELLE['activity']['select']['by_type'],(type,))
        elif user:
            return self.execute(TABELLE['activity']['select']['by_user'],(user,))
        elif date_min:
            return self.execute(TABELLE['activity']['select']['by_date_min'],(date_min,))
        elif date_max:
            return self.execute(TABELLE['activity']['select']['by_date_max'],(date_max,))
        # se le chiavi sono tutte false allora prendo tutte le activity
        elif not type and not user and not date_max and not date_min:
            return self.execute(TABELLE['activity']['select']['all'])
        else:
            return False

    def get_activity_points_by_id(self, user_id):
        """Ritorna i punti di uno user"""
        return self.execute(TABELLE['activity_points']['select']['by_id'],(user_id,))['points']

    def get_activity_points_all(self):
        return self.execute(TABELLE['activity_points']['select']['all'],)

    # ============ADDER/UPDATER======================================
    def add_user(self, user, id_bot=None):
        """Aggiunge uno user alle tabelle id_users e bot_users
        @:param user: dizionario dello user, necessita delle chiavi id, language_code
        @:type: dict
        @:param id_bot: id del bot a cui aggiungere lo user
        @:type: int"""
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
        """Aggiunge un user alla tabella items
        @:param id: id dell'user
        @:type: int"""
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
        """Non so che faccia"""
        self.add_user(bot)

    def add_punteggio(self, id, punteggio):
        """Aggiunge uno user nella tabella punteggio con relativo id
        @:param id: id dell'user
        @:type: int
        @:param punteggio: punteggio relativo all'user
        @:type: int"""
        query = TABELLE['punteggio']['insert']
        return self.execute(query, (id, punteggio))

    def update_items(self, items_us, id):
        """Aggiorna gli item realtivi ad un user
        @:param items_us: necessita delle chiavi c, nc, r, ur, l, e, u, ue
        @:type: dict
        @:param id: user id
        @:type: int"""

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
        """Aggiorna uno user nella tabella id_users
        @:param user: dizionario, necessita delle chiavi:
        admin, teste, loot_user, loot_admin, banned, id"""
        query = TABELLE['id_users']['update']
        return self.execute(query,
                            (user['admin'], user['tester'], user['loot_user'], user['loot_admin'], user['banned'],
                             user['id']))

    def add_new_user(self, user):
        """Aggiunge un nuovo utente alle tabelle id_user e users
        @:param user: dizionario, necessita delle chiavi id, username"""
        # print("Saving new user")
        self.execute(TABELLE['id_users']['insert']['complete_user'],
                     (user['id'], False, False, True, False, False))

        self.execute(TABELLE['users']['insert'],
                     (user['id'], user['username']))

    def update_punteggi(self, dizionario):
        """Salva il i punteggi aggiornati aggiornandoli in caso gia fossero presenti oppure aggiungendoli altrimenti
        @:param dizionario: lista di dict, necessita delle chiavi id, valutazione, msg_id, attacchi
        @:type: list of dict"""

        for elem in dizionario:
            self.execute(TABELLE['punteggio']['insert'],
                         (elem['id'], elem['valutazione'], elem['msg_id'], elem['attacchi']))

    def add_bot_user(self, effective_user, bot_id):
        """Aggiunge uno user in bot_users
        @:param effective_user: utente, necessita delle chiavi id, language_code
        @:type: dict"""
        self.execute(TABELLE['bot_users']['insert'], (bot_id, effective_user['id'], effective_user['language_code'],))

    def add_update_top_user(self, pc_tot, pc_set, money, ability, rango, id):
        """Aggiunge un user alla tabella top, se gia esiste lo aggiorna
        @:param pc_tot: punti craft totali
        @:type: int
        @:param pc_set: punti craft settimanali
        @:type: int
        @:param money: edosoldi
        @:type: int
        @:param ability: abilità
        @:type: int
        @:param rango: rango
        @:type: int
        @:param id: id dell'user
        @:type: int
        """
        self.execute(TABELLE['top']['insert'], (pc_tot, pc_set, money, ability, rango, id,))

    def update_username(self, new_username, id):
        """Cambia lo username nel tabella users
        @:param new_username: nuovo username
        @:type: str
        @:param id: id dello user che vuole cambiare il nome
        @:type: int"""
        self.execute(TABELLE['users']['update'], (new_username, id,))

    def update_teams(self, team_name, numero, pc):
        """Aggiunge una riga dentro la tabella teams
        @:param team_name: nome del team
        @:type: str
        @:param numero: numero rappresentante la posizione temporale dell'elemento
        @:type: int
        @:param pc: punti craft totali
        @:type: int"""

        self.execute(TABELLE['teams']['insert'], (team_name, numero, pc))

    def insert_creator(self, creator_id, creator_username, rules, rewards, min_participants, max_participants):
        """Inserisce dentro la tabella constest_creator i parametri"""

        self.execute(TABELLE['constest_creator']['insert'],
                     (creator_id, creator_username, rules, rewards, min_participants, max_participants,))

    def add_bug(self, bug):
        """Add a row in bugs
        @:param bug: the bug
        @:type: str"""
        #conta le row in bugs
        bugs=self.get_bugs()

        if not bugs:id_b=0
        elif not isinstance(bugs,list): id_b=1
        else: id_b=len(bugs)
        id_b+=1

        self.execute(TABELLE['bugs']['insert'],(bug, id_b,))

    def add_activity(self,id_user, content, type):
        """Aggiunge una riga alla tabella activity
        @:param id_user: l'id dello user che ha inviato il messaggio
        @:type: int
        @:param content: il messaggio inviato
        @:type: str
        @:param type: il tipo di messaggio
        @:type: str"""

        self.execute(TABELLE['activity']['insert'],(id_user,content,type))

    def add_sentiment_activity(self, sentiment, activity_id):
        """Aggiunge un sentimento a una riga della tabella activity
        @:param: sentiment {-1,0,1} = {negativa, neutrale, positiva}
        @:type: int
        @:param activity_id: id dell'attività
        @:type: int"""

        print(sentiment)
        if sentiment not in [-1,0,1]: return

        self.execute(TABELLE['activity']['update']['sentiment'],(sentiment,activity_id,))

    def insert_activity_points(self, user_id):
        """Inserisce uno user dentro la tabella activity points con punteggio zero
        @:param user_id: ide dello user
        @:type: int"""

        self.execute(TABELLE['activity_points']['insert'],(user_id,))

    def update_activity_points(self, user_id,score):
        """Aggiorna lo score di uno user enlla tabella activity_points
        @:param user_id: ide dello user
        @:type: int
        @:param score: punteggio {-1,1}
        @:type: int"""
        
        print("score :"+str(score))

        if score<0:
            self.execute(TABELLE['activity_points']['update']['loose'],(score,user_id,))
        else:
            self.execute(TABELLE['activity_points']['update']['win'],(score, user_id,))


    # ============DELETE/RESET======================================
    def ban_user(self, user):
        """Banna un user dal bot
        @:param user: dizionario dell'user, necessita l'id"""
        # salvo l'id dell'utente o del bot
        # print("Sto negando l'accesso all'user " + str(user['id']))
        self.execute(TABELLE['id_users']['insert']['complete_user'],
                     (user['id'], False, False, False, False, True))

    def delete_from_all(self, user_id):
        """Elimina un utente dalle tabelle id_users, users, punteggio, items
        @:param user_id: id dell'utente"""
        self.execute(TABELLE['id_users']['delete'], (user_id,))
        self.execute(TABELLE['users']['delete'], (user_id,))
        self.execute(TABELLE['punteggio']['delete'], (user_id,))
        self.execute(TABELLE['items']['delete'], (user_id,))

    def reset_punteggio(self):
        """Resetta tutti i punteggi nella tabella punteggio"""
        self.execute(TABELLE['punteggio']['reset'])

    def reset_rarita_user(self, id):
        """Resetta le rarità relativa ad un utente
        @:param id: id dell'utente
        @:type: int"""
        self.execute(TABELLE['items']['reset'], (id,))

    def delete_user(self, user):
        """Elimina un user dalla tabella id_users
        @:param user: dizionario rappresentate l'utente, necessita della key id
        @:type: dict"""
        self.execute(TABELLE['id_users']["delete"], user["id"])

    def different_user(self, userA, userB):
        """Verifica che due user siano diveri
        @:param userA: primo user
        @:type: dict
        @:param userB: secondo user
        @:type: dict
        """
        if (userB and (userA['id'] == userB['id']) and
                (userA['username'] == userB['username']) and
                (userA['first_name'] == userB['first_name']) and
                (userA['last_name'] == userB['last_name']) and
                (userA['language_code'] == userB['language_code'])):
            return False
        return userA

    def delete_teams_by_date_now(self):
        """Elimina dalla tabella teams tutti gli elementi con data antecedente a ora"""
        self.execute(TABELLE['teams']['delete']['by_date_today'])

    def delete_teams_by_date(self, datetime):
        """Elimina dalla tabella teams tutti gli elementi con data antecedente a datetime
        @:param datetime: data da cui iniziare a cancellare le righe
        @:type: datetime"""
        self.execute(TABELLE['teams']['delete']['by_date'], (datetime,))

    def delete_teams_by_name(self, team_name):
        """Elimina dalla tabella teams tutti gli elementi con nome uguale a team_name
        @:param team_name: nome del team
        @:type: str"""
        self.execute(TABELLE['teams']['delete']['by_team'], (team_name,))

    def delete_teams_all(self, team_name):
        """Elimina dalla tabella teams tutti gli elementi"""
        self.execute(TABELLE['teams']['delete']['all'])

    def delete_contest_creator(self):
        """Elimina tutti i valori dentro contest_creator"""

        self.execute(TABELLE['constest_creator']['delete'])

    def delete_bug(self,id):
        """Cancella una row dalla tabella bugs in base all'id
        @:param id: l'id del bug
        @:type: int"""
        self.execute(TABELLE['bugs']['delete'],(id,))

    #============================UTILS======================================
    def is_loot_admin(self, id):
        """Verifica che l'id passato sia di un admin o admin loot
        @:param id: l'id dello user
        @:type: str
        @:return: bool"""
        users=self.execute(TABELLE['id_users']['select']['from_id'],(id,))
        if not users: return False
        if not isinstance(users, list): users=[users]

        for elem in users:
            if elem['id']==id:
                if elem['admin'] or elem['loot_admin']: return True
                else: break

        return False


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
            if not user:  # user non prensete nel db id_users
                if 'private' in update.message.chat.type:  # se il messaggio è stato mandato in privata allora devo chiedere l'accesso
                    self.request_access(bot, user_id)
                elif 'supergroup' in update.message.chat.type:  # altrimenti guardo se è presente nei bot_users
                    bot_users = DB.execute(TABELLE['bot_users']['select']['by_ids'], (user_id, bot.id))
                    if not bot_users:  # se non è presente glielo dico e lo salvo nel db
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
        # costruisce il dizionario dal messaggio
        user = {"id": user_lst[0], "username": " ".join(user_lst[1:])}
        if (command.strip(
                "/") == "consentiAccessoSi"):  # se viene garantito l'accesso salva l'user nel db e notifa user e developer

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

        else:  # altrimenti aggiungi l'user alla lista bannati e notifica i developers
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
        """Invia la richiesta di accesso ai comandi agli id presenti in deleloper_dict"""
        to_send = "L'utente :\nid: " + str(user["id"]) + "\nusername: " + str(user["username"]) + "\nfirst_name: " + \
                  str(user["first_name"]) + "\nlast_name: " + str(
            user["last_name"]) + "\n" + "\nHa richiesto l'accesso a " + \
                  str(bot.username) + "\nConsenti?"
        bot.send_message(user['id'], "La richiesta di accesso al bot è stata inoltrata, aspetta la risposta")

        # costruisce il messaggio da inivare dal dizionario
        user = str(user["id"]) + " " + str(user["username"])

        # print(to_send,user)
        for dev in developer_dicts.values():
            # manditiene in memoria i messaggi inviati per evitare doppie risposte
            developer_message.append(bot.send_message(dev, to_send, reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Si", callback_data="/consentiAccessoSi " + user),
                InlineKeyboardButton("No", callback_data="/consentiAccessoNo " + user)
            ]]), one_time_keyboard=True))
