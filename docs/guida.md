# Guida a ContentExtractor

## Cosa fa

ContentExtractor trasforma un link, un post Instagram salvato o un argomento di ricerca in piccole proposte operative.
Ogni proposta riceve un giudizio: adottare oppure scartare.
Indica anche il repository che verrebbe modificato.
Il tool riempie una coda, ma non modifica mai gli altri repository.

## Come si apre

In produzione apri http://content-extractor.life.local.
La pagina è servita da dev-linux: il backend è un servizio systemd utente sulla porta 10053 e il frontend usa la porta 3387. È raggiungibile dalla LAN e da Tailscale e non richiede password.

Per avviare il backend in sviluppo:

```sh
cd backend && .venv/bin/python -m content_extractor_backend
```

Per avviare il frontend serve Node 20 o successivo:

```sh
cd frontend && npm run dev
```

## Casi d'uso passo per passo

### Mandare link dal gruppo Telegram
1. Apri il gruppo Telegram collegato a ContentExtractor e invia i link.
2. Se hai più link, mettili in un solo messaggio: è meglio di molti messaggi separati.
3. Il coordinatore li prende in carico e li aggiunge al flusso di ingestione.

### Ingerire un link a mano
1. Apri un terminale nell'ambiente Life.
2. Esegui:

```sh
python -m suite_learn_core ingest <url> --node contentExtractor --obiettivo "che cosa stai cercando"
```

3. Scrivi un obiettivo concreto, perché guida il giudizio delle proposte.

### Importare i salvati di Meta
1. Scarica da Meta l'export dei contenuti salvati in formato ZIP.
2. Esegui:

```sh
python -m suite_learn_core import-saved <export.zip> --node contentExtractor
```

3. Attendi che i contenuti entrino nella coda.

### Rivedere le proposte
1. Apri la pagina di ContentExtractor.
2. Apri una proposta e leggi il suggerimento e il repository indicato.
3. Se necessario, scegli uno o più progetti e aggiungi una nota di implementazione.
4. Premi **Approva** per adottarla oppure **Declina** per scartarla.
5. L'approvazione apre una issue GitHub nel repository di destinazione.

### Rigiudicare la coda
Esegui:

```sh
python -m suite_learn_core rejudge --node contentExtractor --obiettivo "nuovo obiettivo"
```

Il comando rigiudica solo le proposte ancora in attesa e non rilegge le fonti.

## Servizi LLM

Il nodo non sceglie più i modelli.
Ogni lavoro è un servizio `llm-run` dichiarato nel `config/llm-routing.json` di ciascuna istanza Life:
- `contentExtractor.estrazione`: tipo `estrazione`, livello `medio`;
- `contentExtractor.giudizio`: tipo `giudizio`, livello `medio`;
- `contentExtractor.ricerca`: tipo `testo-lungo`, livello `medio`;
- `contentExtractor.traduzione`: tipo `traduzione`, livello `facile`.

I modelli arrivano dalla matrice dell'istanza, `config/llm-code.json`, calcolata dai punteggi. Per cambiarli si modifica tipo o livello del servizio in `llm-routing.json`, mai il nome di un modello.
Il file `.env` del nodo imposta `AI_BACKEND=llm-run`.
La lettura delle immagini, come fotogrammi dei reel, slide dei caroselli e allegati, resta su `LEARN_LLM_LETTURA=gateway`, perché il router non trasporta immagini.
La documentazione completa è in `Life/docs/llm-routing.md`.

## Problemi comuni

- La pagina risponde 502: il servizio frontend è fermo.
- Un link non produce nulla: viene registrato come `failed` con `failure_reason`. È un record, non un bug.
- Una pagina blocca la lettura con 403 o richiede JavaScript: il sistema riprova con fetcher di riserva.
- Compare “Nessun motore LLM utilizzabile”: controlla `AI_BACKEND` e che il servizio sia dichiarato nell'istanza con `LIFE_INSTANCE_DIR=<istanza> Life/scripts/llm-run check`.
- Compare «coda esaurita» (uscita 5): tutti i modelli della cella hanno fallito. L'esecuzione si ferma e mostra i motivi.
