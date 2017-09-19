import json

import utils

NEGOZI = (
    79297374614,
    53930040696,
    49323534240,
    91235949067,
    52769617366,
    97456485241,
    98128917950,
    33993865643,
    54776792608,
    25434498998,
    36908597775,
    23578216146,
)

def create_shops(text):
    oggetti = get_items(text)
    negozi = ""
    while oggetti:
        negozi += "`" + create_shop(oggetti[:10]) + "`\n"
        oggetti = oggetti[10:]
    return negozi
    
def create_shop(items):
    shop = "/negozio "
    shop += ",".join(list(map(lambda item: (
        item['oggetto'] + ":" +
        str(item['prezzo']) + ":" +
        str(item['necessari'])), items)))
    return shop

def get_items(text):
    oggetti = text.split("\n")
    items = {}
    for oggetto in oggetti:
        if oggetto.startswith(">"):
            item = get_item(oggetto)
            items[get_db_item(item['oggetto'])['id']] = item
    for negozio in NEGOZI:
        shop = get_negozio(negozio)
        for item in shop:
            if item['item_id'] in items:
                items[item['item_id']]['prezzo'] = item['price']
    return list(items.values())
    
def get_item(text):
    param = text.split(" ")
    item = {
        'necessari': int(param[1]),
        'oggetto': " ".join(param[5:-1]),
        'prezzo': 0
    }
    return item
    
def get_db_item(nome_oggetto):
    url = "http://fenixweb.net:3300/api/v1/items/" + nome_oggetto
    items = utils.get_content(url, parse_json=True)['res']
    if isinstance(items, list):
        for item in items:
            if item['name'] == nome_oggetto:
                return item
    return items

def get_negozio(codice):
    url = "http://fenixweb.net:3300/api/v1/shop/" + str(codice)
    return utils.get_content(url, parse_json=True)['res']
    
if __name__ == "__main__":
    print(create_shops("""Lista oggetti necessari per Corazza Antimateria: 
> 2 su 2 di Ala della Fenice (E)
> 1 su 2 di Lama Celeste (E)
> 1 su 1 di Manico dello Stregone (E)
> 1 su 1 di Scheggia di Hatrurite (E)
> 1 su 3 di Blocco della Fine (L)
> 2 su 4 di Innesto (L)
> 3 su 4 di Lacrima Galattica (L)
> 1 su 1 di Manico della Fine (L)
> 4 su 4 di Oro Bianco (L)
> 1 su 1 di Oro Nero (L)
> 1 su 1 di Plutonio (L)
> 2 su 4 di Polvere Divina (L)
> 3 su 4 di Ambra Nera (UR)
> 7 su 10 di Avorio (UR)
> 4 su 5 di Laccio Elastico (UR)
> 5 su 8 di Laccio Statico (UR)
> 1 su 2 di Pietra Rituale (UR)
> 1 su 3 di Scaglia di Adamantio (UR)
> 4 su 5 di Scalpello (UR)
> 4 su 5 di Carbonio (R)
> 7 su 8 di Catalizzatore (R)
> 1 su 3 di Cristallo Opaco (R)
> 2 su 3 di Diamante (R)
> 4 su 5 di Pietra del Sangue (R)
> 1 su 7 di Rivestimento da Caccia (R)
> 1 su 2 di Runa Instabile (R)
> 1 su 1 di Runa Stabile (R)
> 2 su 9 di Unguento (R)
> 6 su 9 di Laccio (NC)
> 2 su 6 di Resina (NC)
> 1 su 7 di Telo (NC)"""))