#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import utils
import re

API = "http://fenixweb.net:3300/api/v2/"
TOKEN = "cMeBZ7H22h8ApDho1722"
ITEMS = API + TOKEN + "/items"
SHOP = API + TOKEN + "/shop/"

NEGOZI = (
    14501401327,
    18164013683,
    26214958953,
    27710823262,
    31437794971,
    36268311737,
    37065414168,
    45796402190,
    50778334988,
    55605058279,
    68873282471,
    71938314999,
    82265422713,
    84499506942,
    90104392404,
    97210686305,
)

OGGETTI = {}
OGGETTI_DB = {}
LAST_UPDATE = None

def set_items():
    global OGGETTI
    global OGGETTI_DB
    oggetti = utils.get_content(ITEMS, True)['res']
    OGGETTI = {oggetto['name']: get_item(oggetto) for oggetto in oggetti}
    OGGETTI_DB = {oggetto['id']: oggetto['name'] for oggetto in oggetti}
  
def get_item(oggetto):
    return {
        'stima': oggetto['estimate'],
        'id': oggetto['id'],
        'prezzo': 0
    }
  
def set_prices():
    negozi = [utils.get_content(SHOP + str(codice), True)['res'] for codice in NEGOZI]
    global OGGETTI
    for negozio in negozi:
        for oggetto in negozio:
            OGGETTI[OGGETTI_DB[oggetto['item_id']]]['prezzo'] = oggetto['price']
    
def value(text):
  update()
  text = "Prezzi per: {}\n".format(text[text.index("per")+4:test.index(":")])
  oggetti = [oggetto.split(" ") for oggetto in text.split("\n") if re.match("^[0-9]", oggetto)]
  prezzo_craft = int(text[text.rindex(":")+1:text.index("§")].replace("'", ""))
  oggetti = {" ".join(oggetto[2:-1]): int(oggetto[0]) for oggetto in oggetti}
  text += "Prezzo bot: {}\n".format(sum([OGGETTI[oggetto]['stima']*oggetti[oggetto] for oggetto in oggetti]))
  prezzi_mancanti = [oggetto for oggetto in oggetti if OGGETTI[oggetto]['prezzo'] == 0]
  text += "Prezzo negozi: {}\n".format(sum([OGGETTI[oggetto]['prezzo']*oggetti[oggetto] for oggetto in oggetti]))
  if prezzi_mancanti:
    text += "Prezzi mancanti: {}\n".format("\n".join(prezzi_mancanti))
  text += "Prezzo craft: {}".format(prezzo_craft)
  return text
  
def update():
  global LAST_UPDATE
  if(not LAST_UPDATE or utils.diff_date(LAST_UPDATE, utils.now()) > 0):
    LAST_UPDATE = utils.now()
    print(LAST_UPDATE)
    set_items()
    set_prices()
