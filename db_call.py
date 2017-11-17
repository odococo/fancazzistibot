#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Small script to show PostgreSQL and Pyscopg together
#

import logging
import json
import os
from urllib import parse
import psycopg2
import psycopg2.extras


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# aggiunge un utente al database
def add_user(user, id_bot=None):
    # salvo l'id dell'utente o del bot
    execute("""INSERT INTO id_users(id) 
            VALUES(%s)
            ON CONFLICT(id) DO NOTHING""", (user['id'],)
    )
    # salvo le altre informazioni relative ad utenti o bot
    # queste informazioni potrebbero cambiare nel tempo, quindi
    # prima di tutto selezione le ultime informazioni note dal database
    # se sono uguali ignoro, altrimenti effettuo un inserimento
    user_db = execute("""SELECT a.*
                   FROM users AS a
                   INNER JOIN (
                        SELECT id, MAX(date) AS date
                        FROM users
                        GROUP BY id
                   ) b ON a.id = b.id AND a.date = b.date
                   WHERE a.id = %s""", (user['id'],)
           )
    if different_user(user, user_db):
        execute("""INSERT INTO users(
                id, username, first_name, last_name, language_code)
                VALUES(%s, %s, %s, %s, %s)""",
                (user['id'], user['username'], 
                user['first_name'], user['last_name'], 
                user['language_code']))
    if id_bot is not None:
        execute("""INSERT INTO bot_users(id_bot, id_user, language)
                VALUES(%s, %s, %s)
                ON CONFLICT(id_bot, id_user) DO NOTHING;""",
                (id_bot, user['id'], user['language_code'])
        )

# aggiunge un bot al database. Il bot ha le medesime caratteristiche di un utente
def add_bot(bot):
    add_user(bot)

# ritorna l'elenco dei punteggi    
def get_punteggi():
  query = """SELECT username, valutazione
          FROM punteggio JOIN users ON (id_user = id)"""
  return execute(query)

# aggiungi un punteggio
def add_punteggio(id, punteggio):
  query = """INSERT INTO punteggio (id_user, valutazione)
          VALUES (%s, %s)"""
  return execute(query, (id, punteggio))
#------------------------------------------------------------------------------- 
# essendoci anche la data, non posso fare il controllo direttamente da db
def different_user(userA, userB):
    if (userB and (userA['id'] == userB['id']) and 
        (userA['username'] == userB['username']) and
        (userA['first_name'] == userB['first_name']) and 
        (userA['last_name'] == userB['last_name']) and
        (userA['language_code'] == userB['language_code'])):
        return False
    return userA
   
# esegue una query arbitraria    
def execute(query, param=None):
    print(query)
    cursor = connect_db();
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
      
TABELLE = {
  "id_users": {
    "create": """CREATE TABLE IF NOT EXISTS id_users(
              id integer PRIMARY KEY,
              admin boolean DEFAULT false,
              tester boolean DEFAULT false,
              loot_user boolean DEFAULT false,
              loot_admin boolean DEFAULT false)""",
    "drop": """DROP TABLE IF EXISTS id_users CASCADE""",
    "select": """SELECT * FROM id_users""",
    "insert": """INSERT INTO id_users (id) 
              VALUES(%s)
              ON CONFLICT(id) DO NOTHING""",
    "update": """UPDATE id_users
              SET admin = %s, tester = %s, loot_user = %s, loot_admin = %s
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
    "select": """SELECT * FROM users""",
    "insert": """INSERT INTO users (id, username, first_name, last_name, language_code)
              VALUES (%s, %s, %s, %s ,%s)
              ON CONFLICT (id) DO NOTHING""",
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
    "select": """SELECT * FROM bot_users""",
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
              type varchar(20),""",
    "drop": """DROP TABLE IF EXISTS activity CASCADE""",
    "select": """SELECT * FROM activity""",
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
              valutatione numeric(1) DEFAULT 0,
              date timestamp DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(id_user))""",
    "drop": """DROP TABLE IF EXISTS valutazione CASCADE""",
    "select": """SELECT * FROM valutazione""",
    "insert": """INSERT INTO punteggio (id_user, valutazione)
              VALUES (%s, %s)
              ON CONFLICT(id_user) DO UPDATE
              SET valutazione = EXCLUDED.valutazione, date = CURRENT_TIMESTAMP""",
    "update": """UPDATE punteggio
              SET valutazione = %s
              WHERE id_user = %s""",
    "delete": """DELETE FROM punteggio
              WHERE id_user = %s"""
  }
}

def init():
    #map(lambda tabella: execute(TABELLE[tabella]['drop']), TABELLE)
    print(execute(TABELLE['id_users']['select']))
    map(lambda tabella: execute(TABELLE[tabella]['create']), TABELLE)
    map(lambda tabella: print(execute(TABELLE[tabella]['select'])), TABELLE)
    
if __name__ == "__main__":
    init()
