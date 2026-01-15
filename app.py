#Importo le librerie necessarie
import tensorflow as tf
import numpy as np
import json
import cv2
import time
import csv
from datetime import datetime
import asyncio
import requests
import os
#Importo la funzione controlla_e_notifica dal file telegram_bot.py
from telegram_bot import controlla_e_notifica


#Percorso del modello di classificazione
MODELLO_PATH = "Modello Classificazione Rifiuti.h5"
#Classi del modello
CLASSI = ["biologico", "plastica"]
#Percorso del file dello storico
STORICO_PATH = "storico.csv"
#Indirizzo IP RaspberryPi
RPI_IP = "YOUR_RPI_IP_ADDRESS_HERE"
#Indirizzo per richieste POST in modo da far muovere i servo motori
SERVO_URL = f"http://{RPI_IP}:5000/move"
#Soglia massima di rifiuti
SOGLIA = 10
#Token Telegram
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'

#CONTEGGIO RIFIUTI

#Funzione carica contatori
def carica_contatori():
    #Creo un dizionario in cui il numero di rifiuti per classe parte da 0
    contatori = {classe: 0 for classe in CLASSI}
    #Verifico l'esistenza del file csv
    if os.path.exists("contatori_notifica.csv"):
        #Apro il file in modalità lettura
        with open("contatori_notifica.csv", "r") as f:
            #Leggo il file riga per riga
            reader = csv.DictReader(f)
            #Per ogni riga del file
            for row in reader:
                #Prendo il valore della chiave classe e conteggio aggiornando il dizionario
                contatori[row['classe']] = int(row['conteggio'])
    #Restituisco il dizionario aggiornato
    return contatori

#Funzione salva_contatori
def salva_contatori(contatori):
    #Apro il file csv in modalità scrittura
    with open("contatori_notifica.csv", "w", newline="") as f:
        #Definisco uno scrittore in grado di scrivere colonne come classe e conteggio
        writer = csv.DictWriter(f, fieldnames=["classe", "conteggio"])
        #Scrivo la riga di intestazione
        writer.writeheader()
        #Per ogni coppia all'interno del dizionario
        for classe, count in contatori.items():
            #Scrivo una riga con la classe e il numero corrispondente
            writer.writerow({"classe": classe, "conteggio": count})

#CONTROLLO SE I COPERCHI SONO APERTI

#Funzione coperchi_aperti
def coperchi_aperti():
    try:
        #Controllo se esiste il file stato_coperchi.json
        if os.path.exists("stato_coperchi.json"):
            #Apro il file in modalità lettura
            with open("stato_coperchi.json", "r") as f:
                #Leggo il contenuto del file e lo trasformo in un dizionario
                stato = json.load(f)
                #Se lo stato è aperto, restituisco True
                return stato.get("stato") == "aperti"
    #Gestisco gli errori
    except Exception as e:
        print(f"[ERRORE] Lettura stato coperchi: {e}")
    #Se il file non esiste allora i coperchi sono chiusi e restituisco False
    return False

#GESTIONE DELLO STORICO DEI RIFIUTI

#Funzione salva_storico
def salva_storico(classe_predetta):
    #Prendo data e ora correnti, trasformando il tutto in una stringa
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #Apro il file dello storico in modo da aggiungere righe senza cancellare quelle già esistenti
    with open(STORICO_PATH, "a", newline="") as f:
        #Creo un oggetto per scrivere
        writer = csv.writer(f)
        #Scrivo una riga con la data e la classe predetta
        writer.writerow([timestamp, classe_predetta])
    #Stampo un messaggio che confermi l'aggiornamento dello storico
    print(f"Storico aggiornato: {classe_predetta} alle {timestamp}")

#GESTIONE MOVIMENTO DEI SERVOMOTORI

#Funzione muovi_servo
def muovi_servo(classe):
    try:
        #Messaggio per confermare che il servo si sta per muovere
        print(f"Spostamento servo per '{classe}' in corso...")
        #Definisco un dizionario contenente l'angolo (180°) e la classe
        payload = {"angle": 180, "material": classe}
        #Invio una richiesta HTTP POST al server di RaspberryPi per muovere il servo
        requests.post(SERVO_URL, json=payload, timeout=2)
        #Aspetto due secondi per permettere al servo di terminare il movimento
        time.sleep(2)
        #Invio una richiesta HTTP POST al server di raspberryPi per far tornare il servo alla posizione iniziale
        requests.post(SERVO_URL, json={"angle": 0, "material": classe}, timeout=2)
        #Stampo una conferma
        print("Servo riportato alla posizione iniziale.")
    #Gestisco possibili errori
    except Exception as e:
        print(f"Errore nel movimento del servo '{classe}':", e)

#ACQUISIZIONE E PREPROCESSAMENTO DELL'IMMAGINE

#Funzione acquisisci_immagine
def acquisisci_immagine():
    #Apro la webcam
    camera = cv2.VideoCapture(0)
    #Se la webcam non si apre correttamente interrompo la funzione
    if not camera.isOpened():
        raise RuntimeError("Errore: impossibile accedere alla webcam.")
    #Aspetto due secondi per assicurarmi che sia tutto stabile
    time.sleep(2)
    #Scatto una foto
    ret, frame = camera.read()
    #Chiudo la webcam
    camera.release()
    #Se non si è riusciti a scattare la foto si solleva un errore
    if not ret or frame is None:
        raise RuntimeError("Errore: impossibile catturare un'immagine dalla webcam.")
    return frame

#Funzione preprocessa_immagine
def preprocessa_immagine(img):
    #Ridimensiono l'immagine
    img_ridimensionata = cv2.resize(img, (224, 224))
    #Converto l'immagine in un array numpy
    img_array = np.array(img_ridimensionata) / 255.0
    #Aggiungo una dimensione all'array per simulare un batch di immagini
    img_array = np.expand_dims(img_array, axis=0)
    #Restituisco l'immagine preprocessata
    return img_array

#RILEVAZIONE OGGETTO

#Funzione rileva_movimento
def rileva_movimento(soglia=500000):
    #Apro la webcam
    camera = cv2.VideoCapture(0)
    #Se la webcam non si apre c'è un errore
    if not camera.isOpened():
        raise RuntimeError("Errore: impossibile accedere alla webcam.")
    #Aspetto due secondi per stabilizzare
    time.sleep(2)
    #Scatto una prima foto
    ret1, frame1 = camera.read()
    #Aspetto un secondo
    time.sleep(1)
    #Scatto una seconda foto
    ret2, frame2 = camera.read()
    #Chiudo la webcam
    camera.release()

    #Se una delle due immagini non è valida sollevo un errore
    if not ret1 or not ret2 or frame1 is None or frame2 is None:
        raise RuntimeError("Errore durante la cattura dei frame.")

    #Calcolo la differenza assoluta fra le due foto
    diff = cv2.absdiff(frame1, frame2)
    #Converto l'immagine di differenza in bianco e nero
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    #Applico un filtro per ridurre il rumore
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    #Creo un'immagine binaria
    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    #Stampo il valore del movimento rilevato
    movimento = np.sum(thresh)

    #Stampo il valore del movimento rilevato
    print(f"Valore movimento: {movimento}")
    #Restituisco True se il movimento è maggiore della soglia stabilita
    return movimento > soglia

#FUNZIONE PRINCIPALE

#Funzione loop_continuo
async def loop_continuo():
    #Carico il modello
    modello = tf.keras.models.load_model(MODELLO_PATH)
    modello.summary()
    #Stampo un messaggio di avvio
    print("Sistema avviato. In attesa di oggetti da classificare...")
    #Inizio un ciclo infinito
    while True:
        try:
            #Se i coperchi sono aperti il sistema si ferma temporaneamente
            if coperchi_aperti():
                print("Coperchi aperti - classificazione in pausa...")
                time.sleep(2)
                continue
            #Stampo un messaggio di scansione
            print("Scansione movimento in corso...")
            #Controllo la presenza di movimento
            if rileva_movimento():
                print("Oggetto rilevato. Acquisizione in corso...")
                #Scatto una foto dell'oggetto
                immagine = acquisisci_immagine()
                #Preprocesso l'immagine
                input_modello = preprocessa_immagine(immagine)
                #Do l'input al modello
                predizione = modello.predict(input_modello)
                #Trovo l'indice di classe più alto
                indice_classe = np.argmax(predizione)
                #Traduco l'indice in testo
                classe_predetta = CLASSI[indice_classe]
                #Stampo la classe rilevata
                print(f"Classe rilevata: {classe_predetta}")
                print(f"Output grezzo del modello: {predizione}")
                print(f"Classe scelta (indice): {indice_classe}")

                #Salvo il tutto nello storico
                salva_storico(classe_predetta)
                #Muovo il servomotore corrispondente
                muovi_servo(classe_predetta)
                #Carico il contatore dei rifiuti
                contatori = carica_contatori()
                #Aumento di uno il contatore della classe rilevata
                contatori[classe_predetta] += 1
                #Salvo l'aggiornamento
                salva_contatori(contatori)

                #Se il numero di rifiuti di una classe ha superato la soglia
                await controlla_e_notifica(contatori)
                #Aspetto cinque secondi per ripartire
                print("Attesa per nuovo oggetto...")
                time.sleep(5)
            #Se non rilevo movimento aspetto un secondo e riprovo
            else:
                time.sleep(1)
        #Gestisco gli errori
        except Exception as e:
            print("Errore nel loop:", e)
            time.sleep(2)
#Eseguo il programma
if __name__ == "__main__":
    asyncio.run(loop_continuo())
