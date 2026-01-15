#Importo le librerie necessarie
import os
from telegram import Bot
import asyncio
import telegram
#Token di Telegram
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'
#Creo un'istanza del bot Telegram
bot = Bot(token=TELEGRAM_TOKEN)

#CHAT ID

#Funzione get_chat_id
def get_chat_id():
    #Se esiste il file chat_id
    if os.path.exists("chat_id.txt"):
        #Apro il file in modalità lettura
        with open("chat_id.txt", "r") as f:
            #Leggo il chat_id
            return f.read().strip()
    #Se il file non esiste restituisco None
    return None

#INVIO MESSAGGI

# Funzione invia_messaggio corretta
async def invia_messaggio(testo: str):
    chat_id = get_chat_id()
    if not chat_id:
        print("Nessun chat_id trovato. Scrivi prima al bot per registrarti con /start.")
        return
    try:
        await bot.send_message(chat_id=chat_id, text=testo)
        print(f"Messaggio inviato: {testo}")
    except Exception as e:
        print(f"Errore durante l'invio del messaggio: {e}")


#Ottengo le informazioni del bot (non necessario) per debugging
async def mostra_info_bot():
    me = await bot.get_me()
    print(f"Bot info: {me.username} (ID: {me.id})")

#INVIO MESSAGGIO QUANDO SMARTBIN E' PIENO

#Funzione controlla_e_notifica
async def controlla_e_notifica(contatori):
    try:
        #Inizializzo la chat id
        chat_id = None
        #Se il file chat_id.txt esiste
        if os.path.exists("chat_id.txt"):
            #Apro il file in modalità lettura
            with open("chat_id.txt", "r") as f:
                #Assegno la lettura del file alla variabile chat_id
                chat_id = f.read().strip()
        #Se il chat_id non esiste esco dalla funzione
        if not chat_id:
            return
        #Per ogni elemento del dizionario contatori
        for classe_predetta, count in contatori.items():
            #Se il numero di rifiuti è maggiore o uguale a 10
            if count >= 10:
                #Invio un messaggio di avviso
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"Attenzione! Sono stati classificati {count} rifiuti di tipo '{classe_predetta}'. Forse è ora di svuotare SmartBin!"
                )
    #Gestisco l'errore
    except Exception as e:
        print(f"[ERRORE Telegram] Errore durante l'invio della notifica: {e}")


#Eseguo il codice
if __name__ == "__main__":
    asyncio.run(mostra_info_bot())