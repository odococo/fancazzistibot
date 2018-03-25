#! /usr/bin/env python
# -*- coding: utf-8 -*-
import codecs

from Other import utils
import re

API = "http://fenixweb.net:3300/api/v2/"
TOKEN = "cMeBZ7H22h8ApDho1722"
ITEMS = API + TOKEN + "/items"
SHOP = API + TOKEN + "/shop/"
MARKET=API+TOKEN+"/history/market_direct"
RICETTE=API+TOKEN+"/crafts/"
TEAMS="/team/I%20Fancazzisti"
PLAYERS="/players/"


OGGETTI = {}
OGGETTI_DB = {}
LAST_UPDATE = None

def use_api(url):
    try:
        return utils.get_content(url, True)['res']
    except (KeyError , TypeError):
        print (utils.get_content(url, True))
        return {}

def get_ricetta(id_oggetto):
    id_oggetto=str(id_oggetto)
    return use_api(RICETTE+id_oggetto+"/needed")

def set_items():
    global OGGETTI
    global OGGETTI_DB
    oggetti = use_api(ITEMS)
    OGGETTI = {oggetto['name']: get_item(oggetto) for oggetto in oggetti}
    OGGETTI_DB = {oggetto['id']: oggetto['name'] for oggetto in oggetti}
  
def get_item(oggetto):
    return {
        'stima': oggetto['estimate'],
        'id': oggetto['id'],
        'prezzo': 0,
        'base': oggetto['value']
    }
  
def set_prices():
    negozi = [use_api(SHOP + str(codice)) for codice in []]
    global OGGETTI
    for negozio in negozi:
        for oggetto in negozio:
            OGGETTI[OGGETTI_DB[oggetto['item_id']]]['prezzo'] = oggetto['price']
    
def value(text):
  update()
  oggetto = text[text.index("per")+4:text.index(":")]
  
  valore = "Prezzi per: {}\n".format(oggetto)
  valore += "- Base: {}\n".format(OGGETTI[oggetto]['base'])
  valore += "- Stima: {}\n".format(OGGETTI[oggetto]['stima'])
  
  oggetti = [oggetto.split(" ") for oggetto in text.split("\n") if re.match("^[0-9]", oggetto)]
  oggetti = {" ".join(oggetto[2:-1]): int(oggetto[0]) for oggetto in oggetti}
  prezzo_craft = int(text[text.rindex(":")+1:text.index("§")].replace("'", ""))
  
  valore += "- Somma base oggetti: {}\n".format(sum([OGGETTI[oggetto]['base']*oggetti[oggetto] for oggetto in oggetti]))
  valore += "- Somma stima oggetti: {}\n".format(sum([OGGETTI[oggetto]['stima']*oggetti[oggetto] for oggetto in oggetti]))
  
  prezzi_mancanti = [oggetto for oggetto in oggetti if OGGETTI[oggetto]['prezzo'] == 0]
  valore += "- Negozi: {}\n".format(sum([OGGETTI[oggetto]['prezzo']*oggetti[oggetto] for oggetto in oggetti]))
  if prezzi_mancanti:
    valore += "Prezzi mancanti: {}\n".format("\n".join(prezzi_mancanti))
    
  valore += "- Prezzo craft: {}".format(prezzo_craft)
  return valore
  
def update():
  global LAST_UPDATE
  if(not LAST_UPDATE or utils.diff_date(LAST_UPDATE, utils.now(False)) > 0):
    LAST_UPDATE = utils.now(False)
    print(LAST_UPDATE)
    set_items()
    set_prices()


def create_complete_item_file(file_name):
    with open(file_name,"w+") as file:
        file.writelines(str(use_api(ITEMS)))


def get_dipendenze(file_name):


    idx=0
    while True:
        with codecs.open(file_name, encoding='utf-8') as file:
            rea = file.read()
            oggetti = eval(rea.replace("null", "None"))

        try:
            oggetto=oggetti[idx]
            print(str(idx)+"/"+str(len(oggetti)))
            idx+=1

            if oggetto['craftable'] and 'dipendenze' not in oggetto.keys():
                dipendenze=use_api(RICETTE+str(oggetto['id'])+"/needed")
                oggetto['dipendenze']=oggetti_inner(dipendenze,file_name)
                with open(file_name,"w+") as file:
                    file.writelines(str(oggetti))
        except IndexError:
            break

def oggetti_inner(dipendenze_list,file_name):

    res=[]

    #aggiungi lettura deigli oggetti aggiornata
    with codecs.open(file_name, encoding='utf-8') as file:
        rea = file.read()
        oggetti = eval(rea.replace("null", "None"))

    for oggetto in dipendenze_list:
        oggetto = next((item for item in oggetti if item["id"] == oggetto['id']))

        if oggetto['craftable'] and "dipendenze" not in oggetto.keys():
            dipendenze=use_api(RICETTE+str(oggetto['id'])+"/needed")
            oggetto['dipendenze']=oggetti_inner(dipendenze,file_name)


            res+=oggetto['dipendenze']

            oggetti[oggetti.index(oggetto)]=oggetto
            with open(file_name, "w+") as file:
                 file.writelines(str(oggetti))


        elif "dipendenze" in oggetto.keys():
            res+=oggetto['dipendenze']
            #res.append(oggetto['id'])


        else:
            res.append(oggetto['id'])

    return res


file_name="Resources/oggetti_dipendenze"


#create_complete_item_file(file_name)
get_dipendenze(file_name)