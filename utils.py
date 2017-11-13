#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re
import datetime
import requests
import json
import ast

from bs4 import BeautifulSoup
from telegram import ReplyMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ConversationHandler

from comandi import Command
from db_call import execute


def new_command(bot, update):
    command = Command(bot, update)
    command.execute()


def is_admin(id):
    """Verifica se l'id dell'utente è di un admin o meno"""
    admin = (89675136,  # Odococo
             337053854,  # AlanBerti
             24978334,  # brandimax
             )
    return id in admin


def is_numeric(value, strict_int=False):
    return isinstance(value, int) or (
        not strict_int and isinstance(value, str)
        and value.isnumeric())


def reverse(obj):
    if isinstance(obj, str):
        return obj[::-1]
    elif isinstance(obj, int):
        return int(str(obj)[::-1])
    elif isinstance(obj, list):
        obj.reverse()
        return obj
    else:
        return obj


def get_user(user):
    if not user:
        return None
    fields = ["*{}*: `{}`".format(key, value)
              for key, value in user.items() if key != "date"]
    return "\n".join(fields)


def get_user_db(key_value):
    query = """SELECT * FROM users"""
    key_value = (str(key_value) if is_numeric(key_value, True)
                 else key_value)
    if is_numeric(key_value):
        query += " WHERE id = %s"
    else:
        query += " WHERE username = %s"
    query += " ORDER BY date DESC"
    user = execute(query, (key_value,))
    return (user[0] if isinstance(user, list) and len(user)
            else user)


def convert(value, from_base=None, to_base=None, values=None):
    if not value:
        return "Cosa vuoi convertire?"
    elif isinstance(value, list):
        return "".join([convert(val, from_base, to_base, values) for val in value])
    if from_base and not to_base:
        if from_base != 10:
            value = convert(value, from_base, 10, values)
        return chr(int(value))
    elif not from_base and to_base:
        value = str(value)
        value = [ord(val) for val in value]
        return convert(value, 10, to_base, values)
    elif from_base and to_base:
        if to_base != 10:
            value = int(convert(value, from_base, 10, values))
            if not values:
                values = [str(index) for index in range(to_base)]
            converted_values = []
            while value > 0:
                converted_values.append(values[value % to_base])
                value //= to_base
            return "".join(reverse(converted_values))
        else:
            value = str(value)
            converted_values = [(from_base ** index) * int(val) for index, val in enumerate(reverse(value))]
            return str(sum(converted_values))
    else:
        return "Specifica la base originale (conversione a stringa) oppure la base destinazione (conversione da stringa)"


def now(string=True):
    """Ritorna la data attuale nel formato yyyy-mm-dd h:m:s"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S") if string else now


def diff_date(date1, date2):
    return abs(date2 - date1).days


def get_proxy():
    """Ottiene l'ip di un proxy di https://www.sslproxies.org/"""
    proxies = get_content("https://www.sslproxies.org/").find_all('tr')
    for proxy in proxies:
        param = proxy.find_all('td')
        if not param:
            continue
        yield {'https': "http://{ip}:{port}".format(ip=param[0].string, port=param[1].string)}


def get_content(url, parse_json=False, proxies=None):
    request = requests.get(url, allow_redirects=False, proxies=proxies)
    if parse_json:
        return request.json()
    else:
        return BeautifulSoup(request.content, "html.parser")


def get_pretty_json(value):
    if not isinstance(value, dict):
        value = ast.literal_eval(value)
    return json.dumps(value, indent=2)


# =============================LOOT============================================

global costo_craft, stima, quantita, costo


def estrai_oggetti(msg):
    global quantita

    #print(msg)

    restante = msg.split("già possiedi")[0].split(":")[1]
    aggiornato = ""
    #print(restante)

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

    print(aggiornato)
    regex = re.compile(r"di (.*)?\(")
    regex2 = re.compile(r"su ([0-9]) di (.*)?\(")
    lst = re.findall(regex, aggiornato)
    quantita = re.findall(regex2, aggiornato)
    commands = []
    print(quantita)
    last_ixd = len(lst) - len(lst) % 3
    for i in range(0, (last_ixd) - 2, 3):
        commands.append("/ricerca " + ",".join(lst[i:i + 3]))

    commands.append("/ricerca " + ",".join(lst[last_ixd:len(lst)]))
    final_string = ""

    for command in commands:
        final_string += command + "\n"

    return final_string


def ricerca(bot, update):
    """Condensa la lista di oggetti di @craftlootbot in comodi gruppi da 3,basta inoltrare la lista di @craftlootbot"""
    global costo_craft, stima, quantita, costo
    text = update.message.text.lower()
    to_send = estrai_oggetti(text)
    costo_craft = text.split("per eseguire i craft spenderai: ")[1].split("§")[0].replace("'", "")
    update.message.reply_text(to_send)
    reply_markup = ReplyKeyboardMarkup([["Anulla", "Stima"]], one_time_keyboard=True)
    update.message.reply_text("Adesso puoi inoltrarmi tutti i risultati di ricerca di @lootplusbot per "
                              "avere il totale dei soldi da spendere. Quando hai finito premi Stima, altrimenti annulla.",
                              reply_markup=reply_markup)
    stima = True
    costo=[]
    return 1


def annulla(bot, update):
    """Annulla la stima"""
    global stima, costo_craft, quantita

    #print("\n\nAnnulla\n\n")

    stima = False
    costo_craft = 0
    quantita = []
    return ConversationHandler.END


def stima(bot, update):
    """ Inoltra tutte i messaggi /ricerca di @lootbotplus e digita /stima. Così otterrai il costo totale degli oggetti, la 
           top 10 di quelli piu costosi e una stima del tempo che impiegherai a comprarli tutti."""
    global stima, costo_craft, quantita, costo

    #print("\n\nStima\n\n")
    #print(update)

    if update.message.text == "Anulla":
        update.message.reply_text("Ok ho annullato tutto")
        return annulla(bot, update)
    elif update.message.text == "Stima":
        if not stima:
            update.message.reply_text("Per usare questo comando devi aver prima inoltrato la lista di @craftlootbot!")
            return annulla(bot, update)

        if len(costo) == 0:
            update.message.reply_text("Non hai inoltrato nessun messaggio da @lootbotplus")
            return annulla(bot, update)

        print(costo, quantita)
        tot = 0
        for (much, what) in zip(costo, quantita):
            print(tot)
            tot += int(what[0]) * int(much[1])
        tot += int(costo_craft)

        update.message.reply_text("Secondo le stime di mercato pagherai " +
                                  "{:,}".format(tot).replace(",", "'") + "§ , (costo craft incluso)")

        if (len(costo)>10):
            costo.sort(key=lambda tup: int(tup[1]), reverse=True)
            to_print = "I 10 oggetti piu costosi sono:\n"
            for i in range(1, 11):
                to_print += costo[i][0] + " : " + costo[i][1] + " §\n"

            update.message.reply_text(to_print)

        m, s = divmod(len(costo) * 10, 60)

        update.message.reply_text("Se compri tutti gli oggetti dal negozio impiegherai un tempo di circa : "
                                  + str(m) + " minuti e " + str(s) + " secondi\n")

        costo.clear()
        quantita.clear()
        stima = False
        return ConversationHandler.END
    else:
        print("\n\nStima Parziale\n\n")
        stima_parziale(update.message.text.lower())
        return 1


def stima_parziale(msg):
    global costo
    prov = msg.split("negozi per ")[1:]
    lst = []
    for elem in prov:
        lst.append((elem.split(">")[0].replace("\n", "") + elem.split(">")[1].replace("\n", "")))

    #print(lst)
    regex = re.compile(r"(.*):.*\(([0-9 .]+)")

    for elem in lst:
        e = re.findall(regex, elem)
        #print(e)

        costo.append((e[0][0], e[0][1].replace(".", "").replace(" ", "")))
    #print(costo)
