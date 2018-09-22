Questo bot è diviso in 5 parti fondamentali.

# Comandi base
In questa sezione tratterò solo dei comandi piu semplici del bot, quelli che vengono
triggerati da un messaggio e immediatemente eseguono un'azione (senza l'uso di ulteriori
messaggi).

Questa serie di comandi si trova  [qui](Loot/comandi.py) dentro la classe Command.
Ogni funzione rappresenta un comando, per aggiungere una si deve scegliere prima il livello
di permessi per suddetta funzione [U-> user, A-> admin, D-> developer] e poi aggiungere il nome della
funzione successivamente (senza maiuscole).

Per esempio se voglio un comando per aggiungere un utente utilizzabile solo da un admin la funzione
può chiamare *Aaggiungiutente*. Ogni funzione aggiunta ha bisogno di una docstring
(documentazione) sotto la dichiarazione.

Detto questo si potranno avere accesso all'interno della classe a varie informazioni:
* command : il comando usato dall'utente
* params : il resto della stringa inviata tolto il comando
* bot : il bot a cui è stato inviato il comando
* is_private: bool, comando inviato in privata o in un gruppo
* insulti: lista di stringhe con insulti
* update : tutte le spec del messaggio


# Comandi Avanzati
Questa serie di comandi prevede l'invio di piu messaggi al bot.
Si trovano [qui](Loot/bot_classes) e hanno tutti lo stesso formato.

Ongni classe è una funzione specifica che viene triggherato da un comando.
Un caso semplice è la classe *PietreDrago*.
Ogni init è identico e deve prendere come parametri sia l'updater (classe di telegram per leggere
i messaggi) che il db (clase per interfacciarsi con il database) e tutte dovranno essere inizializzate nel main.

Consiglio di tenere sempre due modalità di funzionamento per queste classi, in caso di debug o meno.
E' **obbligatoria** la modalità *elegilbe_user* che puo essere tranquillamente usata wrappando la vostra funzione principale
(quella che legge il messaggio ed esegue le altre funzionalità) dentro db.elegible_loot_user (puo anche
essere usato elegible_loot_admin). Questo permette di non far usare ad altri i comandi del bot.
Fatto questo potete portare avanti il comando come volete, prendendo anche spunto dalle altre calssi.


## Prima di aggiungere un comando
Una volta implementato un comando bisogna aggiungere la sua firma in modo tale che compaia nel messaggio di help.
Questo puo essere fatto andando nel file [comandi](Loot/comandi.py) e aggiungere una riga dentro la varaiblie *COMANDI_PLUS*
rispettando la formattazione. Infine va aggiunta anche dentro la varaiblie *COMANDI_BOT_FATHER* [qui](Other/utils.py) rispettando la formattazione e
avvertendo brandimax per farla aggiungere alla schermata del bot.

# Database
Il bot si appoggia al database di heroku [postgress](https://devcenter.heroku.com/articles/heroku-postgresql) per salvare informazioni varie.
Tutte queste interazioni sono (e devono rimanere) dentro [db_call](Loot/db_call.py).
Qui è presente sia la variabile *TABELLE*, un dizionario che contiene tutti i comandi SQL per
salvare/cancellare/modificare informazioni dalla varie tabelle del database.
Sia la classe *DB* che usa la variabile *TABELLE* per effettuare diverse funzioni.

Tutte queste funzioni sono divise in :
* getter : prendere info dal database
* adder/updater: per aggiungere o modificare informazioni
* deleter/resetter : per cancellare o resettare una tabella

Inoltre contiene anche le funzioni per verificare la possibilità di accede al bot, sotto
la classe *Access to bot*

# Sentiment Analysis
Cose in piu che non centrano nulla e possono essere trascurate.