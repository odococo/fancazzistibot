#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re
import datetime
import requests
import json
import ast
import emoji
import operator


from bs4 import BeautifulSoup
from telegram import ReplyMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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

def is_dev(id):
    """Verifica se l'id del bot è quello del fancazzista supremo"""
    return id == 333089594
    
def is_fanca_admin(id):
    """Verifica se l'id dell'utente è di un admin dei fancazzisti o meno"""
    admin = (107839625, #IMayonesX
             241317532, #Osho27
            )
    return id in admin

def is_tester(id):
    tester = (107839625, #IMayonesX
            )
    return is_admin(id) or id in tester


def is_numeric(value, strict_int=False):
    """Verifica se il valore passato è un numerico oppure una stringa che contiere un numerico"""
    return isinstance(value, int) or (
        not strict_int and isinstance(value, str)
        and value.isnumeric())


def reverse(obj):
    """Ribalta l'oggetto passato"""
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

def get_user_id(update):
    try:
        return update._effective_user.id
    except IndexError:
        return 0


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
    #print(restante.split("\n"))

    for line in restante.split("\n"):
        if line[2:3] != line[7:8]:
            new_num = int(line[7:8]) - int(line[2:3])
            print(new_num)
            new_line = line.replace(line[7:8], str(new_num))
            new_line = new_line.replace(line[2:3], str(new_num))
            aggiornato += new_line + "\n"
        else:
            aggiornato += line + "\n"
    #print(aggiornato)
    regex = re.compile(r"di (.*)?\(")
    regex2 = re.compile(r"su ([0-9]) di (.*)?\(")
    lst = re.findall(regex, aggiornato)
    quantita = re.findall(regex2, aggiornato)
    commands = []
    quantita = [(q[0], q[1].strip()) for q in quantita]
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

        #print(costo, quantita)
        merged=[]
        for q in quantita:
            c = [item for item in costo if item[0] == q[1]]
            if (len(c) > 0):
                c = c[0]
                merged.append((q[0], q[1], c[1]))
        print(merged)
        tot = 0
        for elem in merged:
            tot += int(elem[0]) * int(elem[2])

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
        #print("\n\nStima Parziale\n\n")
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

# =============================BOSS============================================

global lista_boss, dict_boss, last_update_id, phoenix
"""in ordine, lista data da cerca_boss
 dizionario con chiave nome e valore punteggio
 update id (int) dell'ultimo messaggio inoltrato dall'admin, serve per vedere se non sta inoltrando un doppione
 boolean phoenix, serve all'admin per decidere il sistema di valori"""
def cerca_boss(msg):
    """Dato il messaggio di attacco ai boss ritorna una lista di liste con elementi nel seguente ordine:\n
    lista[0]: nome \n
    lista[1]: Missione/cava + tempo se in missione o cava, 1 altrimenti\n
    lista[2]: 0 se non c'è stato attacco al boss, tupla altrimenti: tupla[0] danno, tupla[1] numero di boss"""
    prova = msg.split("Attività membri:\n")[1]
    prova = emoji.demojize(prova)
    name_reg1 = re.compile(r"([0-z_]+) :")
    name_reg2=re.compile(r"^([0-z_]+) .*")
    obl_reg = re.compile(r":per.*: ([0-z /(/)]+)")
    boss_reg = re.compile(r":boar: ([0-9]+) .*/([0-9])")

    res = []

    for elem in prova.split("\n\n"):
        try:
            name = re.findall(name_reg1, elem)[0]
        except IndexError:
            name=re.findall(name_reg2, elem)[0]
        obl = re.findall(obl_reg, elem)
        boss = re.findall(boss_reg, elem)[0]
        if (len(obl) == 0):
            obl = 1
        else:
            obl = obl[0]
        if boss[0] == "0": boss = 0
        res.append([name, obl, boss])

    return res

def boss_admin(bot, update):
    """Inoltra il messaggio del boss, solo per admin"""

    #controlla se admin
    if not is_admin(get_user_id(update)):
        update.message.reply_text("Non sei autorizzato ad inoltrare questi messaggi")
        return ConversationHandler.END
    global lista_boss, dict_boss, last_update_id, phoenix

    #TODO: prendi dizionario e last_update_id dal database
    #prendi il dizionario, lista  e id
    dict_boss={}
    last_update_id=0

    lista_boss=cerca_boss(update.message.text)

    reply_markup = ReplyKeyboardMarkup([["Phoenix", "Titan"]], one_time_keyboard=True)
    update.message.reply_text("Di quale boss stiamo parlando?",
                              reply_markup=reply_markup)
    return 1

def boss_user(bot, update):
    """Se un user vuole visualizzare le stesse info degli admin non ha diritto alle modifiche"""
    reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Completa", "Fine"]],
                                       one_time_keyboard=False)
    update.message.reply_text("Quali info vuoi visualizzare?", reply_markup=reply_markup)
    return 1


def punteggio(bot, update):
    """Visualizza la sita di tutti con punteggio annesso"""
    global lista_boss, dict_boss

    if not len(lista_boss) > 0:
        update.message.reply_text("Devi prima inoltrare il messaggio dei boss!")
        return ConversationHandler.END
    if not len(dict_boss.keys()) > 0:
        update.message.reply_text("Il dizionario è vuoto (contatta @brandimax)")
        return ConversationHandler.END

    sortedD = sorted(dict_boss.items(), key=operator.itemgetter(1), reverse=True)

    to_send = ""
    for elem in sortedD:
        to_send += str(elem[0]) +" : "+ str(elem[1])+"\n"

    update.message.reply_text(to_send)
    return 1 #1 è l'id del boss_loop nel conversation handler

def completa(bot, update):
    """Visualizza la lista completa ti tutte le info"""
    global lista_boss, dict_boss

    if not len(lista_boss) > 0:
        update.message.reply_text("Devi prima inoltrare il messaggio dei boss!")
        return ConversationHandler.END
    if not len(dict_boss.keys()) > 0:
        update.message.reply_text("Il dizionario è vuoto (contatta @brandimax)")
        return ConversationHandler.END

    to_send="✅ <b>Hanno attaccato</b>:\n"

    attaccato=sorted([elem for elem in lista_boss if elem[2]!=0],key=lambda tup: int(tup[2][0]),reverse=True)
    non_attaccato=[elem for elem in lista_boss if elem[2]==0]

    i=1
    for elem in attaccato:
        if i==1: to_send+="🥇"+str(i)+") "
        elif i==2: to_send+="🥈"+str(i)+") "
        elif i==3: to_send+="🥉"+str(i)+") "
        else: to_send+=str(i)+") "
        to_send+="@"+str(elem[0])+" : facendo <b>"+'{:,}'.format(int(elem[2][0])).replace(',', '\'')+"</b> danno a <b>"+str(elem[2][1])+"</b> boss\n"
        i+=1

    to_send+="\n❌ <b>Non hanno attaccato</b>:\n"

    i=1
    for elem in non_attaccato:
        to_send+=str(i)+") @"+str(elem[0])+" : il suo punteggio attuale è <b>"+str(dict_boss[elem[0]])+"</b>"
        if elem[1]==1:
            to_send+=", può attaccare\n"
        else:
            to_send+=", non può attaccare perchè in "+str(elem[1])+"\n"
        i+=1


    update.message.reply_text(to_send,parse_mode="HTML")
    return 1

def fine(bot, update):
    update.message.reply_text("Finito",reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END



def boss_loop(bot, update):
    """Funzione di loop dove ogni methodo , tranne fine, ritorna dopo aver inviato il messaggio"""
    global phoenix, lista_boss,last_update_id

    choice=update.message.text
    if choice=="Non Attaccanti": return non_attaccanti(bot,update)
    elif choice=="Punteggio":return punteggio(bot,update)
    elif choice == "Completa":return completa(bot,update)
    elif choice=="Fine": return fine(bot,update)

    #se l'admin vuole modificare la lista
    elif choice=="Phoenix" or choice=="Titan" and is_admin(get_user_id(update)):
        if choice=="Phoenix": phoenix=True
        else: phoenix=False
        # aggiunge i membri nel dizionario se non sono gia presenti
        for elem in lista_boss:
            if elem[0] not in dict_boss.keys():
                dict_boss[elem[0]] = 0
            if elem[2] == 0 and phoenix: dict_boss[elem[0]] += 2
            elif elem[2] == 0 and not phoenix:  dict_boss[elem[0]] += 1

            last_update_id = update.message.message_id
            #Todo: salva dizionario e last_update solo se id è admin

        reply_markup = ReplyKeyboardMarkup([["Non Attaccanti", "Punteggio"], ["Completa", "Fine"]],
                                           one_time_keyboard=False)
        update.message.reply_text("OK!\nAdesso fammi sapere in che formato vuoi ricevere le info.",
                                  reply_markup=reply_markup)

        return 1

    else:
        #TODO: elif se manda un altro messaggio  gestisci
        update.message.reply_text("Non ho capito, ripeti")
        return 1



def non_attaccanti(bot, update):
    """Visualizza solo la lista di chi non ha ancora attaccato"""
    global lista_boss, dict_boss

    if not len(lista_boss)>0:
        update.message.reply_text("Devi prima inoltrare il messaggio dei boss!")
        return ConversationHandler.END
    if not len(dict_boss.keys())>0:
        update.message.reply_text("Il dizionario è vuoto (contatta @brandimax)")
        return ConversationHandler.END

    sortedD=sorted(dict_boss.items(), key=operator.itemgetter(1), reverse=True)

    to_send=""
    for elem in sortedD:
        if(elem[1]>0):to_send+=str(elem[0])+"\n"

    update.message.reply_text(to_send)
    return 1










