#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re
import datetime
import requests
import json

from bs4 import BeautifulSoup

from comandi import Command
from db_call import execute

def new_command(bot, update):
    command = Command(bot, update)
    command.execute()
        
def unknown_command():
    if re.search("^[.!/](dec2)?b(b)?\d+$", self.command):
        self.getattr(self.command[1:self.command.rindex("b")+1])()
    else:
        self.answer("Ti sembra che {} sia nell'elenco?".format(self.command))

            
def is_admin(id):
    """Verifica se l'id dell'utente è di un admin o meno"""
    admin = (89675136, # Odococo
             337053854 # AlanBerti
    )
    return id in admin
        
def is_numeric(value, strict_int=False):
    """Controlla se un valore è numerico oppure è una stringa di un numero"""
    return isinstance(value, int) or (
           not strict_int and isinstance(value, str)
           and value.isnumeric())
            
def reverse(self, obj):
    if isinstance(obj, str):
        return obj[::-1]
    elif isinstance(obj, int):
        return int(str(obj)[::-1])
    elif isinstance(obj, list):
        obj.reverse()
        return obj
    else:
        return None
        
def get_user(self, user):
    """Ritorna una stringa riguardante un utente"""
    if not user:
        return None
    fields = ["*{}*: `{}`".format(key, value)
            for key, value in user.items() if key != "date"]
    return "\n".join(fields)
    
def get_user_db(key_value):
    """Cerca un utente nel database"""
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
    
def convert_value(to_base, value, values=None, number=False):
    """Converte una stringa in una base specifica"""
    if not value:
        return None
    if not values:
        values = [str(n) for n in range(base)]
    if is_numeric(value, not number):
        converted_value = []
        value = convert_value(10, int(value))
        while value > 0:
            converted_value.append(values[value % to_base])
            value //= base
        return reverse(converted_value)
    else:
        return ["".join(convert_value(to_base, ord(char), values)) for char in value]
        
def now(string=True):
    """Ritorna la data attuale nel formato yyyy-mm-dd h:m:s"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S") if string else now
    
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
