#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re
import datetime
import requests
import json
import ast

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
      converted_values = [(from_base**index)*int(val) for index, val in enumerate(reverse(value))]
      return str(sum(converted_values))
  else:
    return "Specifica la base originale (conversione a stringa) oppure la base destinazione (conversione da stringa)"
        
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
    
def get_pretty_json(value):
    if not isinstance(value, dict):
        value = ast.literal_eval(value)
    return json.dumps(value, indent=2)
