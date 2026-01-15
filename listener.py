#Importo le librerie necessarie
import os
import io
import requests
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import json
#Importo carica_contatori
from app import carica_contatori


#Definisco il token del bot
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'
#Indirizzo IP di RaspberryPi
RPI_SERVER = "YOUR_RPI_SERVER_ADDRESS_HERE"
#Stato iniziale dei coperchi
cop_state = {"stato": "chiusi"}
#File per i conteggi
COUNTER_FILE = "contatori_notifica.csv"
#Classi del modello
CLASSI = ["biologico", "plastica"]

#IMPAGINAZIONE PDF

#Definisco una classe
class PDFReport(FPDF):
    #Definisco l'intestazione del PDF
    def header(self):
        #Definisco il font
        self.set_font('Arial', 'B', 16)
        #Creo una cella larga come tutta la pagina alta dieci punti con testo centrato. Vado a capo
        self.cell(0, 10, 'Storico Smaltimento Rifiuti', ln=True, align='C')
        #Aggiungo uno spazio sotto
        self.ln(5)

    #Definisco il piè di pagina
    def footer(self):
        #Sposto il cursore a 15 punti dal basso
        self.set_y(-15)
        #Definisco il font
        self.set_font('Arial', 'I', 8)
        #Creo una cella con il numero di pagina corrente
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

#COMANDO /START

#Funzione da eseguire quando l'utente invia il messaggio /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Ottiene il chat_id dell'utente che ha inviato il comando
    chat_id = update.effective_chat.id
    #Salvo il chat_id in un file txt
    with open("chat_id.txt", "w") as f:
        f.write(str(chat_id))
    #Invio un messaggio di benvenuto
    await context.bot.send_message(chat_id=chat_id, text="Benvenuto su SmartBin! "
                                                          "SmartBin è un bidone intelligente per la raccolta differenziata di biologico e plastica.\n"
                                                          "Ti aiuterà a smaltire i rifiuti in modo semplice, veloce ed intuitivo.\n\n"
                                                          "Scrivi `/istruzioni` per saperne di più.")

#COMANDO /ISTRUZIONI

#Funzione /istruzioni
async def istruzioni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Messaggio da inviare
    testo = (
        "Ciao! Ecco come funziona SmartBin:\n"
        "Avvicina il rifiuto alla telecamera per il riconoscimento.\n"
        "SmartBin aprirà automaticamente il coperchio corrispondente:\n"
        "🔵 Plastica\n🟢 Biologico\n\n"
        "SmartBin ti avviserà quando è il momento di svuotarlo"
        "Comandi utili:\n"
        "`/storico giorno` (o settimana, mese, anno)\n"
        "`/apri` per aprire tutti i coperchi e svuotare SmartBin\n"
        "`/chiudi` per chiuderli\n"
    )
    #Invio il messaggio
    await context.bot.send_message(chat_id=update.effective_chat.id, text=testo, parse_mode="Markdown")

#COMANDO APRI

#Funzione /apri
async def apri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Ottengo l'id della chat
    chat_id = update.effective_chat.id
    #Uso una variabile globale per registrare se i coperchi sono aperti o chiusi
    global cop_state
    #Controllo se i coperchi sono aperti
    if cop_state["stato"] == "aperti":
        #In caso siano aperti, avviso l'utente ed esce dalla funzione
        await context.bot.send_message(chat_id=chat_id, text="♻️ I coperchi sono già aperti e SmartBin è pronto per essere svuotato!\nScrivi /chiudi per chiuderli.")
        return

    try:
        #Invio una richiesta HTTP POST al server di RaspberryPi per far muovere entrambi i servomotori
        response = requests.post(f"{RPI_SERVER}/apri", timeout=5)
        #Controllo se la risposta è 200
        if response.status_code == 200:
            #Aggiorno lo stato dei coperchi
            cop_state["stato"] = "aperti"
            #Salvo lo stato dei coperchi sul file json
            salva_stato_coperchi("aperti")
            #Mostro che sono stati aperti
            print("[DEBUG] Risposta OK dal server, ora azzero contatori")
            #Azzero il contatore dei rifiuti
            azzera_contatori()
            contatori = carica_contatori()
            #Mando un messaggio che informa che i coperchi sono stati aperti
            await context.bot.send_message(chat_id=chat_id, text="Coperchi aperti.")
        #Gestisco l'errore
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"Errore nell'apertura: {response.text}")
    #Gestisco gli errori di connessione
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"Connessione fallita: {e}")

#COMANDO /CHIUDI

#Funzione per comando /chiudi
async def chiudi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Ottengo l'id della chat
    chat_id = update.effective_chat.id
    #Accedo alla variabile globale sullo stato dei coperchi
    global cop_state
    #Se i coperchi sono già chiusi, avviso l'utente ed interrompo la funzione
    if cop_state["stato"] == "chiusi":
        await context.bot.send_message(chat_id=chat_id, text="♻️ I coperchi sono già stati chiusi.\nScrivi /apri per svuotarli.")
        return

    try:
        #Invio una richiesta HTTP POST al server di RaspberryPi
        response = requests.post(f"{RPI_SERVER}/chiudi", timeout=5)
        #Verifico che la risposta sia 200
        if response.status_code == 200:
            #Aggiorno lo stato dei coperchi
            cop_state["stato"] = "chiusi"
            #Salvo lo stato dei coperchi
            salva_stato_coperchi("chiusi")
            #Invio un messaggio per indicare che i coperchi sono chiusi
            await context.bot.send_message(chat_id=chat_id, text="Coperchi chiusi.")
        #Gestisco gli errori
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"Errore nella chiusura: {response.text}")
    #Gestisco gli errori
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"Connessione fallita: {e}")

#COMANDO /STORICO

#Funzione comando /storico
async def storico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Ottengo l'id della chat
    chat_id = update.effective_chat.id
    #Se l'utente non specifica il periodo di suo interesse
    if len(context.args) == 0:
        #Definisco messaggio di errore
        testo = ("Per favore specifica il periodo come parametro:\n"
                 "/storico giorno\n/storico settimana\n/storico mese\n/storico anno\n")
        #Invio messaggio
        await context.bot.send_message(chat_id=chat_id, text=testo)
        return
    #Ottiengo e normalizzo il periodo indicato
    periodo = context.args[0].lower()
    #Se il file dello storico non esiste invio un messaggio di errore
    if not os.path.exists("storico.csv"):
        await context.bot.send_message(chat_id=chat_id, text="Nessun dato storico disponibile.")
        return
    #Carico il file csv assegnando i nomi alle colonne
    df = pd.read_csv("storico.csv", names=["datetime", "classe"])
    #Confermo la colonna datetime in oggetti
    df["datetime"] = pd.to_datetime(df["datetime"])
    #Ottengo data e ora attuali
    adesso = datetime.now()
    #Definisco periodo giorno
    if periodo == "giorno":
        inizio = adesso - timedelta(days=1)
    #Definisco periodo settimana
    elif periodo == "settimana":
        inizio = adesso - timedelta(weeks=1)
    #Definisco periodo mese
    elif periodo == "mese":
        inizio = adesso - timedelta(days=30)
    #Definisco periodo anno
    elif periodo == "anno":
        inizio = adesso - timedelta(days=365)
    #Gestisco i messaggi invalidi
    else:
        await context.bot.send_message(chat_id=chat_id, text="Periodo non valido. Usa giorno, settimana, mese o anno.")
        return
    #Filtro i dati che rientrano nel periodo di interesse
    filtrato = df[df["datetime"] >= inizio]
    #Se lo storico è vuoto avviso l'utente
    if filtrato.empty:
        await context.bot.send_message(chat_id=chat_id, text="Nessun dato storico per questo periodo.")
        return
    #Conto quanti rifiuti per tipo sono stati smaltiti
    conteggi = filtrato['classe'].value_counts()
    #Inserisco un riepilogo testo
    riepilogo_testo = "Conteggio pezzi smaltiti per classe:\n"
    for classe, count in conteggi.items():
        riepilogo_testo += f"- {classe}: {count}\n"
    #Imposto la dimensione del grafico
    plt.figure(figsize=(10, 8))
    #Definisco grafico a torta
    plt.subplot(2,1,1)
    conteggi.plot.pie(autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors, textprops={'fontsize': 10})
    plt.title("Distribuzione classi", fontsize=14)
    plt.ylabel('')
    #Definisco grafico a barre
    plt.subplot(2,1,2)
    conteggi.plot.bar(color='skyblue')
    plt.title("Conteggio classi", fontsize=14)
    plt.xlabel("Classe")
    plt.ylabel("Numero di pezzi")

    plt.tight_layout()
    #Salvo il grafico in memoria come immagine PNG
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    plt.close()
    img_buffer.seek(0)
    #Creo un nuovo PDF
    pdf = PDFReport()
    pdf.add_page()
    #Definisco il titolo
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Storico rifiuti - Periodo: {periodo.capitalize()}", ln=True, align='C')
    #Inserisco il riepilogo testuale
    pdf.ln(8)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, riepilogo_testo)
    pdf.ln(5)
    #Definisco la tabella
    pdf.set_fill_color(70, 130, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(60, 10, "Data e Ora", border=1, align='C', fill=True)
    pdf.cell(60, 10, "Classe", border=1, align='C', fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    fill = False
    pdf.set_font("Arial", '', 10)
    #Aggiungo al massimo 20 righe
    max_righe = 20
    for i, row in filtrato.head(max_righe).iterrows():
        if fill:
            pdf.set_fill_color(230, 230, 230)
        else:
            pdf.set_fill_color(255, 255, 255)

        pdf.cell(60, 10, row['datetime'].strftime("%Y-%m-%d %H:%M:%S"), border=1, fill=True)
        pdf.cell(60, 10, row['classe'], border=1, fill=True)
        pdf.ln()
        fill = not fill
    #Se ci sono più di 20 righe scrivo che ce ne sono altre
    if len(filtrato) > max_righe:
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, f"... e altri {len(filtrato) - max_righe} record", ln=True)
    #Salvo i grafici su file temporanei PNG
    img_path = "grafici_storico.png"
    with open(img_path, "wb") as f:
        f.write(img_buffer.read())

    pdf.ln(10)
    #Inserisco l'immagine
    pdf.image(img_path, x=15, w=180)
    #Salvo il PDF
    pdf_path = f"storico_{periodo}.pdf"
    pdf.output(pdf_path)
    #Elimino l'immagine temporanea
    os.remove(img_path)
    #Invio il PDF come documento all'utente
    with open(pdf_path, "rb") as f:
        await context.bot.send_document(chat_id=chat_id, document=f, filename=pdf_path,
                                       caption=f"Storico rifiuti per il periodo: {periodo}")

    os.remove(pdf_path)

#CONTATORE RIFIUTI

#Funzione azzera contatori
def azzera_contatori():
    # Creo un dataframe con tutte le classi e conteggio iniziale a zero
    df = pd.DataFrame({
        'classe': CLASSI,
        'conteggio': [0] * len(CLASSI)
    })
    # Salvo nel file CSV
    df.to_csv(COUNTER_FILE, index=False)
    print("[DEBUG] File contatori_notifica.csv azzerato e reinizializzato con zeri.")

#STATO DEI COPERCHI

#Funzione salva_stato_coperchi
def salva_stato_coperchi(stato):
    #Apro o creo il file stato_coperchi in modalità scrittura
    with open("stato_coperchi.json", "w") as f:
        #Scrivo un dizionario con la chiave stato
        json.dump({"stato": stato}, f)


#Funzione principale
def main():
    #Inizializzo il bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    #Comando /start
    app.add_handler(CommandHandler("start", start))
    #Comando /istruzioni
    app.add_handler(CommandHandler("istruzioni", istruzioni))
    #Comando /apri
    app.add_handler(CommandHandler("apri", apri))
    #Comando /chiudi
    app.add_handler(CommandHandler("chiudi", chiudi))
    #Comando /storico
    app.add_handler(CommandHandler("storico", storico))

    #Stampo un messaggio per indicare che il bot è in ascolto
    print("Bot in ascolto...")
    #Faccio partire il loop di ascolto
    app.run_polling()

#Eseguo il codice
if __name__ == '__main__':
    main()

