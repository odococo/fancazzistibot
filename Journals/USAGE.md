I comandi sono molteplici, tra cui:
* */start*: fa partire il bot 
* */help* : visualizza la schermata di aiuto per il bot
* */info* : manda le informazioni relative all'account che ha utilizzato i comandi
* */permessi*: manda i permessi relativi all'account che ha utilizzato il comando
* */dice param1 param2*: visualizza il risultato di n lanci (param2) di un dado a n facce (param1)
* */roll*: stesso prinicpio di dice ma non ha bisogno di parametri
* */win num1 num2 num3 num4 num5*: ti permette di visualizzare la tua probabilità di vincita nel gioco del poker con dadi, durante l'ispezione dello gnomo
* */consiglia num1 num2 num3 num4 num5*: Invia un immagine con una tabella, ogni colonna della tabella ha un significato 
specifico:
    * Colonna 1: è composta da due numeri separati da una freccetta "->", il primo è il numero che viene consigliato di 
    cambiare mentre il secondo è uno dei sei numeri che potrebbe uscire
    * Colonna 2: nuova probabilità di vincita, semplicemete la probabilità di vincita in caso esca il secondo nuemro
    * Colonna 3: vecchia probabilità di vincita, con il numero corrente
    * Colonna 4: incremento o decremento di probabilità
* */attacchiBoss*: una volta aggiornato il database dall'admin in carica, questo comando ti permettere di scegliere tra 
vari formati di visualizzazione sul punteggio dei giocatori. Il punteggio dei giocatori è basato sul numero di attacchi 
che ogni giocatore nel team madre ha effettuato: +1 se non ha attaccato il boss Titan in tempo, + 2 per Phoenix. Come potrete capire
piu il punteggio di un giocatore è alto piu è alto il rischio di essere cacciati dal team madre. I formati di visualizzazione
sono i seguenti:
    * *Non attaccanti*: visualizza solamente i nickname dei membri che ancora non hanno attaccato
    * *Punteggio*: visualizza il punteggio di tutti i membri del team madre diviso a seconda del valore.
    * *Completa*: comando riservato solo agli admin
    * *Fine*: riporta il bot alle normali funzioni uscendo dalla schermata di visualizzazione
* */cercaCraft maggioreDi minoreDi* : Questo comande serve per ricercare oggetti a seconda dei punti craft. *Maggiore/MinoreDi*
devono essere due numeri (**NB** Puoi usare il comando anche senza il parametro *minoreDi*) in cui vuoi che sia compreso il valore
di punti craft. In seguito ti verrà chiesto se vuoi filtrare anche a seconda della rarità dell'oggetto [X, UE, E, L, U, UR o tutti] e 
a seconda della rinascita [r0, r1, r2] (**NB** scegliendo una rarità alta ti verranno mostrate anche quelle inferiori, per esempio scegliendo 
r1 vengono mostrati i risultati per r0 e r1; r2-> r0, r1 e r2).
* */compra*: ti permette di calcolare velocemente quanti scrigni comprare dall'emporio dato un budget per gli acquisti 
e le percentuali di scrigni da comprare (in ordine : [Legno, Ferro, Prezioso, Diamante, Leggendario, Epico])
* */rarita*: ti mostra la percentuale di oggetti divisi per rarità che ti mancano maggiormente (vedi CraftlootBot, rarità)
* */resetrarita* : resetta le rarita relative al tuo account, da usare ogni volta che fai acquisti all'emporio
* */helpvideo* : per quei comandi difficili da comprendere abbiamo creato dei video tutorial
* */artefatti* : invia la lista di artefatti
* */cheoresonotra hh:mm* : ti dice che ore saranno tra hh:mm (dove h sono le ore e m i minuti), un esempio sarebbe /cheoresonotra 7:45
* */talenti* : invia un pdf con tutti i necessari (compreso il costo totale) per i talenti
* */top* : mostra la classifica dei migliori gioatori in base a vari parametri (pc totali, pc settimanali, edosoldi, abilità, rango)

## CraftLootBot
Se Il bot riceve un messaggio inoltrato da @craftlootbot, precisamente un messaggio generato dal comando */lista oggetto* si attevierà
una sua funzione. Prima di tutto riceverete una serie di messaggi del tipo:

*/ricerca oggetto1, oggetto2, oggetto3*

Comodi da inoltrare direttamente a @lootplusbot. Inoltre verrete presentati con due scelte:
##### Annulla
Il bot libera la memoria e ritorna allo stato di partenza.
##### Stima
Per accedere a questa funzionalità dovrete aver prima inviato tutti, o quasi, i risultati di @lootbotplus dei comandi 
ricerca precedenti.
Stima ti permette di ottenere informazioni utili sulla ricerca dei tuoi oggetti:
* **Costo stimato**: totale del costo di craft per ogni oggetto (se comprato dal negozio) piu costo di craft
* **Tempo stimato**: un'approssimazione di quanto tempo impiegherai a comprare tutti gli oggetti
* **Comandi per negozio**: anche qui avrai l'opportunità di scegliere se visualizzare tutta le serie di comandi *@lootplusbot numeroNegozio*
, oppure andare avanti, basta premere "Si" o "No".

##### Rarità
Ogni volta che inoltri un messaggio da @craftlootbot dato dal comando /lista saranno salvate le rarità che 
ti mancano. Questo torna utile quando vuoi avere una stima delle quantià di scrigni da comprare.

## Top
Inoltrando al bot il messaggio "Giocatore" che ottieni da @lootbotplus, verrà aggiornata la lista dei top player e potrai visualizzare il tuo 
posto

## Boss (Admin only)
Per una maggiore facilità nella gestione degli attacchi al boss del team madre abbiamo implementato i seguenti comandi semplici e di 
inoltro per gli admin.

Per aggiornare i punteggi dei vostri membri secondo quanto detto sopra (+1 Titan, +2 Phoenix), inoltrate al bot il messaggio 
di @lootgamebot dato dal comando *Team*. Verrete presentati con un'alternativa relativa al boss da attaccare:
* Titan
* Phoenix

Una volta fatto cio sarete riamndati alla schermata di scelta per la visualizzazione delle informazioni, la stessa visualizzata 
dei normali utenti del bot. L'unica differenza sta nell'opzione **Completa** che permette di visualizzare la lista di giocatori separata in due 
parti:
* *Chi ha gia attaccato*, con nickname e punteggi associati
* *Chi non ha ancora attaccato*, con nickname, punteggi associati e possibilità di attaccare al momento (viene visualizzata la scritta in Cava/Missione con il relativo
tempo restante)

**NB**: se dopo aver inoltrato il messaggio del Team scegliete l'opzione "Fine" non vi sarà possibile usare "Completa". Dovrete 
ri-inoltrare il messaggio "Team" per potervi accedere (i messaggi duplicati non verranno salvati ma serviranno solamente per 
poter visualizzare "Completa" )

Inoltre sono presenti i comandi:
* */resetBoss"*: permette di resettare i punteggi di tutti gli utenti. Una volta resettati i punteggi vanno persi **per sempre**.
Per questo ti sarà chiesta la conferma 
* */pinBoss qualeBoss giorno ora*: ti permette di fissare un messaggio per l'attacco dei boss, dove:
    * *qualeBoss*: 0 -> Titan, 1 -> Phoenix
    * *giorno*: numero compreso tra 0 e 6, (0 -> Lunedi, 1 -> Martedi....6-> Domenica)
    * *ora* : un'ora qualsiasi
    
## Altri comandi Admin
Boss apparte ci sono altri comandi riservati ai soli admin:
* */utente username* : visualizza le informazioni correlate all'utente
* */utenti*: visualizza tutti gli utenti che stanno utilizzando il bot
* */registra utente permesso*: cambia i permessi di un utente (per id o per username) nel valore *permesso* [ tester, admin, loot_admin ,loot_user , banned]
* */sendtoall msg*: ti permette di inviare un messaggio *msg* a tutti gli utenti nel database
* */removeuser username* : rimuovi un utente dal bot 
* */svegliamadre msg*: manda un messaggio a tutti i membri del team madre (quelli che sono registrati con i comadni boss)

## Comandi Developer
* */sendtoall msg* : manda un messaggio a tutti quelli presenti nel database
* */deletefromall username* : cancella un utente da tutti i database del bot
* */chiblocca* : l'esecuzione termina quando un utente ha bloccato il bot, e stampa l'id dell'utente

