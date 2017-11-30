#! /usr/bin/env python
# -*- coding: utf-8 -*-

import ast
import datetime
import json

import math
import requests
from bs4 import BeautifulSoup

COMANDI_BOT_FATHER = """
win - Ti dice la probabilità di vittoria che hai nell'ispezione dello gnomo
dice - lancia un dado di numeroFacce un quantitativo di volte pari a numeroDadi
consiglia - Invia una tabella con i numeri da cambiare
roll - lancia un dado senza specificare nulla
info - ottieni le informazioni riguardanti il tuo account
convert - Converte test o numero verso una base arbitraria, si possono fornire valori di conversione per personalizzare il risultato
help - mostra il messaggio di help
start - avvia il bot
resetboss - resetta i punteggi del Boss
helplink - invia link del help completo
pinboss - pinna il messaggio di attacco al boss
utente - visualizza le info di un utente
utenti - Visualizza gli utenti che utilizzano un determinato bot
registra - Aggiorna i permessi di un utente
attacchiboss - visializza le info sui punteggi del Boss
resetboss - resetta i punteggi del Boss
cercacraft - ricerca gli oggetti tramite punteggio craft
permessi - stampa i permessi relativi al tuo account
compra - ti aiuta a decidere quali scrigni comprare
sendtoall - Invia un messaggio a tutti gli users
json - invia il json dell'update
rarita - invia le rarita che piu ti mancano nello zaino
resetrarita - resetta le rarità salvate sinora
removeuser - rimuove un user dal bot
"""


def is_admin(id):
    """Verifica se l'id dell'utente è di un admin o meno"""
    admin = (89675136,  # Odococo
             337053854,  # AlanBerti
             24978334,  # brandimax
             )
    return id in admin

def text_splitter(text, splitter="\n", split_every=10):
    """Divide un messaggio da mandare in piu parti, ritorna una lista di stringhe"""
    text = text.split(splitter)

    text = [text[split_every * i:split_every * i + split_every] for i in range(0, math.ceil(len(text) / split_every))]

    res=[]
    for elem in text:
        to_append="\n".join(elem)
        if to_append: res.append(to_append)
    return res

def is_dev(id):
    """Verifica se l'id del bot è quello del fancazzista supremo"""
    return id == 333089594


def is_fanca_admin(id):
    """Verifica se l'id dell'utente è di un admin dei fancazzisti o meno"""
    admin = (107839625,  # IMayonesX
             241317532,  # Osho27
             )

    return id in admin


def is_tester(id):
    tester = (107839625,  # IMayonesX
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
    fields = ["<strong>{}</strong>: <code>{}</code>".format(key, value)
              for key, value in user.items() if key != "date"]
    return "\n".join(fields)


def get_user_id(update):
    try:
        return str(update._effective_user.id)
    except AttributeError:
        return str(update['message']['from'])
    finally:
        return 0


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
