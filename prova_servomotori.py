#Importo le librerie necessarie
from flask import Flask, request
import RPi.GPIO as GPIO
import time

#Imposto il tipo di numerazione dei pin
GPIO.setmode(GPIO.BCM)

#PRIMO SERVOMOTORE (BIOLOGICO)

#Pin del primo servomotore
servo1_pin = 18
#Imposto il pin come output
GPIO.setup(servo1_pin, GPIO.OUT)
#Creo un oggetto PWM a 50 Hz
pwm1 = GPIO.PWM(servo1_pin, 50)
#Inizio con un duty cycle a 0%
pwm1.start(0)

#SECONDO SERVOMOTORE (PLASTICA)

#Pin secondo servomotore
servo2_pin = 23
#Imposto il pin come output
GPIO.setup(servo2_pin, GPIO.OUT)
#Creo un oggetto PWM a 50 Hz
pwm2 = GPIO.PWM(servo2_pin, 50)
#Inizio con un duty cycle a 0%
pwm2.start(0)

#Creo l'applicazione flask
app = Flask(__name__)

#Funzione per muovere il servomotore
def set_angle(pwm, pin, angle):
    #Calcolo la percentuale del segnale per ottenere l'angolo desiderato
    duty = 2 + (angle / 18)
    #Metto il pin a livello 3.3 V
    GPIO.output(pin, True)
    #Modifico il duty cycle
    pwm.ChangeDutyCycle(duty)
    #Aspetto mezzo secondo per dare il tempo al servomotore di muoversi
    time.sleep(0.5)
    #Metto il pin a livello più basso per spegnere l'impulso
    GPIO.output(pin, False)
    #Fermo il PWM per evitare vibrazioni
    pwm.ChangeDutyCycle(0)

#CLASSIFICAZIONE RIFIUTI

#Definisco un endpoint HTTP POST chiamato /move
@app.route('/move', methods=['POST'])
#Funzione da eseguire quando si riceve una richiesta
def move_servo():
    try:
        #Leggo la richiesta in formato JSON
        data = request.get_json()
        #Prendo il valore dell'angolo dalla richiesta altrimenti lo lascio a 0
        angle = int(data.get("angle", 0))
        #Prendo il valore material rendendolo tutto minuscolo
        material = data.get("material", "").lower()

        #Se il materiale è biologico
        if material == "biologico":
            #Scrivo un messaggio di conferma
            print("Classificato come biologico. Muovo primo servo.")
            #Se l'angolo richiesto è 180°
            if angle == 180:
                #Muovo il servomotore a 180°
                set_angle(pwm1, servo1_pin, 180)
                #Aspetto 10 secondi
                time.sleep(10)
                #Muovo il servomotore a 0°
                set_angle(pwm1, servo1_pin, 0)
            #Se la richiesta è 90°
            elif angle == 90:
                #Muovo il servomotore a 90°
                set_angle(pwm1, servo1_pin, 90)
            #Se la richiesta è 0°
            elif angle == 0:
                #Muovo il servomotore a 0°
                set_angle(pwm1, servo1_pin, 0)

        #Se il materiale è plastica
        elif material == "plastica":
            #Invio un messaggio di conferma
            print("Classificato come plastica. Muovo secondo servo.")
            #Se l'angolo richiesto è 180°
            if angle == 180:
                #Muovo il servomotore a 180°
                set_angle(pwm2, servo2_pin, 180)
                #Aspetto 10 secondi
                time.sleep(10)
                #Muovo il servomotore a 0°
                set_angle(pwm2, servo2_pin, 0)
            #Se la richiesta è 90°
            elif angle == 90:
                #Muovo il servomotore a 90°
                set_angle(pwm2, servo2_pin, 90)
            #Se la richiesta è 0°
            elif angle == 0:
                #Muovo il servomotore a 0°
                set_angle(pwm2, servo2_pin, 0)
        #Se il materiale non è riconosciuto restituisco un errore 400
        else:
            return "Materiale non riconosciuto", 400
        #Invio un messaggio di conferma
        return "Servo mosso correttamente", 200
    #Gestisco eventuali errori
    except Exception as e:
        return f"Errore: {e}", 500

#COMANDO /APRI

#Definisco un nuovo endpoint con richiesta HTTP POST chiamato /apri
@app.route('/apri', methods=['POST'])
#Funzione da eseguire quando si riceve una richiesta
def apri_servi():
    try:
        #Messaggio di conferma
        print("Comando /apri ricevuto: apro entrambi i servomotori a 180°")
        #Entrambi i servomotori si muovono a 180°
        set_angle(pwm1, servo1_pin, 180)
        set_angle(pwm2, servo2_pin, 180)
        #Messaggio di conferma
        return "Entrambi i servomotori aperti a 180°", 200
    #Gestisco eventuali errori
    except Exception as e:
        return f"Errore aprendo servomotori: {e}", 500

#COMANDO /CHIUDI

#Definisco un nuovo endpoint con richiesta HTTP POST chiamato /chiudi
@app.route('/chiudi', methods=['POST'])
#Funzione da eseguire quando si riceve una richiesta
def chiudi_servi():
    try:
        #Messaggio di conferma
        print("Comando /chiudi ricevuto: chiudo entrambi i servomotori a 0°")
        #Entrambi i servomotori si muovono a 0°
        set_angle(pwm1, servo1_pin, 0)
        set_angle(pwm2, servo2_pin, 0)
        #Messaggio di conferma
        return "Entrambi i servomotori chiusi a 0°", 200
    #Gestisco eventuali errori
    except Exception as e:
        return f"Errore chiudendo servomotori: {e}", 500

#Verifico l'esecuzione del file
if __name__ == '__main__':
    try:
        #Messaggio di conferma
        print("Servo server avviato. In attesa di comandi...")
        #Avvio il server Flask
        app.run(host='0.0.0.0', port=5000)
    #Quando il server si chiude fermo il PWM e libero tutti i PIN GPIO
    finally:
        pwm1.stop()
        pwm2.stop()
        GPIO.cleanup()
