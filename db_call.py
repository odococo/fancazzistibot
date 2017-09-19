#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Small script to show PostgreSQL and Pyscopg together
#

import logging
import json
import psycopg2
import psycopg2.extras


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# carattere di default per il database 
# perché null == null ritorna falso in esso
DEFAULT_NULL = "!"

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
                id, username, first_name, last_name, language_code, date)
                VALUES(%s, %s, %s, %s, %s, %s)""",
                (user['id'], user['username'], 
                user['first_name'], user['last_name'], 
                user['language_code'], user['date']))
    if id_bot is not None:
        execute("""INSERT INTO bot_users(id_bot, id_user, 
                date, language)
                VALUES(%s, %s, %s, %s)
                ON CONFLICT(id_bot, id_user) DO NOTHING;""",
                (id_bot, user['id'], user['date'], user['language_code'])
        )

def add_bot(bot):
    add_user(bot)
    
def different_user(userA, userB):
    if (userB and (userA['id'] == userB['id']) and 
        (userA['username'] == userB['username']) and
        (userA['first_name'] == userB['first_name']) and 
        (userA['last_name'] == userB['last_name']) and
        (userA['language_code'] == userB['language_code'])):
        return False
    return userA
    
def execute(query, param=None):
    cursor = connect_db();
    if cursor is not None:
        try:
            cursor.execute(query, param)
            if "SELECT" in query:
                if cursor.rowcount == 1:
                    return cursor.fetchone()
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
    
def connect_db():
    try:
        conn = psycopg2.connect("dbname='telegram_bot' user='postgres' host='localhost' password='postgres'")
        conn.autocommit = True
        return conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    except Exception as error:
        logger.error("Errore nella connessione al database: {}".format(error))
        return None

def test():
    try:
        conn = psycopg2.connect("dbname='telegram_bot' user='postgres' host='localhost' password='postgres'")
        return conn.cursor()
    except Exception as e:
        logger.error("Errore nella connessione al database: {}".format(e))
        return None
    
if __name__ == "__main__":
    test()