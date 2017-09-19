#! /usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import datetime
import logging
import time

from bs4 import BeautifulSoup
                    
import utils

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

URL_BASE = ("https://uninsubria.esse3.cineca.it"
            "/ListaEsitiEsame.do")
CORSI_LAUREA = {'F004': 10104,
                'F013': 10153}
CORSI = {'ALGEBRA E GEOMETRIA': 22986,
         'ALGORITMI E STRUTTURE DATI': 22971,
         'ANALISI E RICONOSCIMENTO NELLE RETI SOCIALI': 24429,
         'ANALISI MATEMATICA': 22988,
         'APPLICAZIONI WEB': 22984,
         'ARCHITETTURA DEGLI ELABORATORI': 22989,
         'AUTOMI E LINGUAGGI': 24604,
         'BASI DI DATI': 22990,
         'ELABORAZIONE DELLE IMMAGINI': 24593,
         'FONDAMENTI DEI LINGUAGGI DI PROGRAMMAZIONE': 24602,
         'FONDAMENTI DI SICUREZZA': 24591,
         'GESTIONE PROGETTI SOFTWARE': 24592,
         'GRAFICA COMPUTAZIONALE': 24601,
         'INFORMAZIONE, TRASMISSIONE E CODICI A PROTEZIONE D\'ERRORE': 22983,
         'INGLESE ': 22977,
         'LABORATORIO I': 22972,
         'LABORATORIO II': 22978,
         'LABORATORIO INTERDISCIPLINARE': 24597,
         'LABORATORIO INTERDISCIPLINARE A': 24596,
         'LABORATORIO INTERDISCIPLINARE B': 25122,
         'LOGICA MATEMATICA': 24600,
         'MICROCONTROLLORI ': 24868,
         'MODELLI INNOVATIVI PER LA GESTIONE DEI DATI': 24595,
         'PROGETTAZIONE DEL SOFTWARE': 22973,
         'PROGRAMMAZIONE': 22969,
         'PROGRAMMAZIONE CONCORRENTE E DISTRIBUITA': 22987,
         'PROGRAMMAZIONE DI DISPOSITIVI MOBILI': 23951,
         'PROGRAMMAZIONE PROCEDURALE E AD OGGETTI': 25123,
         'RETI DI TELECOMUNICAZIONE': 24603,
         'SISTEMI INFORMATIVI': 22979,
         'SISTEMI OPERATIVI': 22993,
         'STORIA DEGLI AUTOMI E DELL\'INFORMATICA': 22980,
         'TIROCINIO FORMATIVO': 22931}
         
MATRICOLE = {'LORETTA ARNOLDI': 711664,
             'MARTINA BIANCHI': 713897,
             'ALESSANDRO DE GRANDI': 727160,
             'EMANUELA DE SENA': 728115,
             'KOFFI VITAL AMOI': 728565,
             'ALESSANDRO GIOVANNACCI': 728707,
             'CHIARA CARLINI': 729126,
             'RICCARDO DAVANZO': 729128,
             'GIULIANO GERACI': 729129,
             'MARCO MANTOVANI': 729130,
             'MARCO MARCHIORI': 729131,
             'SAMUELE SALVIA': 729178,
             'FRANCESCO MANCUSO': 729183,
             'SABRINA SOLDÀ': 729209,
             'ANNA BOSELLI': 729212,
             'IVAN DANZA': 729256,
             'NICOLAS FORTE': 729258,
             'PAOLO PANTALEO': 729288,
             'ANDREA BARBAGALLO': 729298,
             'FEDERICO CREMONA': 729302,
             'ANDREA DELIA': 729304,
             'ANDREA PIETRO GRASSO': 729365,
             'FRANCESCO CUSUMANO': 729408,
             'RICCARDO PACIFICO': 729411,
             'FRANCESCO ANTONIO SESSA': 729412,
             'NICOLÒ ARIOLI': 729495,
             'NICOLÒ BUGANZA': 729531,
             'STEFANO SELVA': 729559,
             'BENEDETTA BIELLI': 729696,
             'SILVIA RISETTI': 729761,
             'GIANMARIO CASULA': 729853,
             'GIOVANNI BROGGI': 729976,
             'VLADI VERRI': 730030,
             'ALESSIO SANGIORGI': 730420,
             'IVAN LAMPERTI': 730654,
             'ALESSANDRO EMANUELE PIOTTI': 730659,
             'DAVIDE RESTA': 730660,
             'ANATOLIY ROSHKA': 730662,
             'MARCO VANOLO': 730831,
             'MARCO GATTO': 730847,
             'DANIELE ASTA': 730907,
             'MATTEO PIOVANELLI': 730989,
             'LUCA BASILICO': 731099,
             'CLAUDIO SIMONELLI': 731147,
             'GIORGIA SIRIGU': 731149,
             'SIMONE REGUZZONI': 731168,
             'FRANCESCO BALLATORE': 731577,
             'DAVID PORTA': 731869}

def get_last_exams(corso=None, matricola=None, limit=5):
    if matricola and not corso:
        esami = []
        for corso in CORSI:
            esami.append({corso: get_exam("F004", corso, str(matricola))})
        print(esami)
    else:
        corso = corso.upper()
        print(get_exam(url_parziale, corso, matricola))
    
def get_exam(corso_laurea, nome_corso, matricola=None):
    sessione = "jsessionid=1.esse3-uninsubria-prod-01"
    corso_laurea = "cds_id={}".format(CORSI_LAUREA[corso_laurea])
    corso = "ad_id={}".format(CORSI[nome_corso])
    url_parziale = "{};{}?{}&{}".format(URL_BASE, sessione, corso_laurea, corso)
    cont = 1
    gen_proxy = utils.get_proxy()
    proxy = next(gen_proxy)
    finito = 0
    matricole = set()
    esami = []
    esiti = {'idoneo': 0,
             'non idoneo': 0,
             'ritirato': 0,
             'esito non pubblicato': 0,
             'None': 0}
    while True:
        num_esame = "app_id={}".format(cont)
        parte_finale = "&app_log_id=1"
        url = "{}&{}&{}&{}".format(url_parziale, corso, num_esame, parte_finale)
        dettagli_esame = utils.get_content(url)
        if not dettagli_esame.title or dettagli_esame.title.string == "Cineca - Waiting Room":
            print("ERRORE! Cambio proxy")
            proxy = next(gen_proxy)
            continue
        cont += 1
        #nome_esame, codice_esame = get_exam_details(dettagli_esame)
        data = get_exam_date(dettagli_esame)
        if not data:
            finito += 1
            if finito > 3:
                print("Esami di {} finiti".format(nome_corso))
                break
        else:
            finito = 0
        studenti = get_students(dettagli_esame)
        for studente in studenti:
            esiti[studenti[studente]] += 1
            matricole.add(studente)
            if matricola and studente == matricola:
                esame = {'data': data.strftime("%Y-%m-%d"),
                         'esito': studenti[studente]}
                esami.append(esame)
    print("Totale = {}\nDettagli = {}".format(sum(esiti.values()), esiti))
    return esami
    
def get_exam_details(exam):
    if not exam.find(class_="titolopagina"):
        return None
    title = str(exam.find(class_="titolopagina").string)
    index = title.index("(cod.")
    return (title[24:index-1], title[index+6:-1])
    
def get_exam_date(exam):
    if not exam.find(class_="tplTitolo"):
        return None
    date = str(exam.find(class_="tplTitolo").string)
    date = date[date.index(":")+1:]
    if date:
        return datetime.datetime.strptime(date, '%d/%m/%Y')
    else:
        return None
        
def get_students(exam):
    students = iter(exam.find_all("td", class_="detail_table"))
    return {str(student.string): str(next(students).string) for student in students}
    
def main():
    get_last_exams(matricola=731149)
    #max_requests()
    
if __name__ == "__main__":
    main()