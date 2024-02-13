# Raspberry Pi Pico Weather Station - Systemy czasu rzeczywistego

import network
import socket
from time import sleep
from machine import ADC, Pin
import dht
import utime
import _thread


# Konfiguracja WiFi
ssid = "ssid"
password = "password"
#Konfiguracja pinow
dht_pin = machine.Pin(16)
dht_sensor = dht.DHT11(dht_pin)
photo_pin = ADC(Pin(26))

# Zakres wartosci dla fotorezystora
wartosc_min = 0
wartosc_max = 65535

# Odczyt danych z czujnika DHT11
def read_dht_data():
    try:
        dht_sensor.measure()
        temperature_celsius = dht_sensor.temperature()
        humidity_percent = dht_sensor.humidity()
        return temperature_celsius, humidity_percent
    except Exception as e:
        print("Błąd odczytu danych z czujnika DHT11:", str(e))
        return "Błąd odczytu", "Błąd odczytu"

# Odczyt danych z fotorezystora
def read_light():
    try:
        light = photo_pin.read_u16()
        light = 100 - ((light - wartosc_min) / (wartosc_max - wartosc_min)) * 100
        return light
    except Exception as e:
        print("Błąd odczytu danych z fotorezystora:", str(e))
        return "Błąd odczytu"

# Czyszczenie pliku na starcie procesu
def clear_file():
    try:
        with open("sensor_data.txt", "w") as file:
            file.write("czas;temperatura;wilgotnosc;jasnosc\n")  # Pisanie pustego ciągu, aby wyczyścić zawartość pliku
        print("Plik został wyczyszczony.")
    except OSError as e:
        print("Błąd czyszczenia pliku:", str(e))

# Cykliczny zapis do pliku i logowanie do konsoli danych
def write_to_file(temperature, humidity, light):
    time = utime.localtime()
    print(f"\nZapis do pliku -> Data {time[1]:02d}.{time[2]:02d} Czas {time[3]:02d}:{time[4]:02d}:{time[5]:02d} Temperatura: {temperature} °C, Wilgotnosc: {humidity} %, jasnosc: {light:.1f} %")
    with open("sensor_data.txt", "a") as file:
       file.write(f"{time[0]}-{time[1]:02d}-{time[2]:02d} {time[3]:02d}:{time[4]:02d}:{time[5]:02d};{temperature};{humidity};{light:.1f}\n")

# Generowanie HTML -> mozliwosc pobrania pliku txt z zapisanymi danymi
def webpage():
    light = read_light()
    dht_data = read_dht_data()
    if dht_data:
        temperature, humidity = dht_data
    print("\n-------------------------------------------------")
    print("Jasność:", "{:.1f}%".format(light))
    print("Temperatura:", "{:.1f}%".format(temperature))
    print("Wilgotność:", "{:.1f}%".format(humidity))
    write_to_file(temperature, humidity, light)
    # Template HTML
    html = f"""
        <!DOCTYPE html>
        <html>
        <p>Temperatura {temperature} C</p>
        <p>Wilgotnosc {humidity}%</p>
        <p>Jasnosc {light:.1f}%</p>
        <a href="./download" download="sensor_data.txt">
            <button>Pobierz dane</button>
        </a>
        <p></p>
        <a href="./" >
            <button>Odswiez</button>
        </a>

        </body>
        </html>
        """
    return str(html)

# Funkcja łączenia z siecią WiFi
def connect():
    # Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Czekam na połączenie...')
        sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Połączono z adresem IP: {ip}')
    return ip

# Funkcja zapisujaca dane cyklicznie w osobnym watku
def save_data_periodically():
    while True:
        # Odczyt danych z fotorezystora i czujnika DHT11
        dht_data = read_dht_data()
        light = read_light()
        if dht_data:
            temperature, humidity = dht_data
            write_to_file(temperature, humidity, light)

        # Odczekanie podanej ilosci sekund przed kolejnym zapisem
        utime.sleep(10)

# Funkcja obsługujaca zadanie pobrania danych
def download_data():
    try:
        with open("sensor_data.txt", "r") as file:
            file_content = file.read()
        response = ("HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Disposition: attachment; "
                    "filename=sensor_data.txt\r\n\r\n")
        response += file_content

        return response
    except OSError as e:
        print("Błąd odczytu pliku:", str(e))
        return "HTTP/1.0 500 Internal Server Error\r\n\r\nInternal Server Error"

# Obsluga zadania HTTP


# Funkcja otwierająca gniazdo sieciowe
def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    return connection

# Funkcja obsługująca serwer HTTP
def serve(connection):
    # Start a web server
    while True:
        client = connection.accept()[0]
        request = client.recv(1024)
        request = str(request)
        try:
            request = request.split()[1]
        except IndexError:
            pass

        if request == "/":
            # Obsługa standardowego żądania
            response = webpage()
        elif request == "/download":
            # Obsługa żądania pobrania danych
            response = download_data()
        else:
            # Obsługa innych przypadków (np. 404 Not Found)
            response = "HTTP/1.0 404 Not Found\r\n\r\n404 Not Found"
        client.sendall(response.encode())
        client.close()

# Uruchomienie funkcji zapisujacej dane do pliku w osobnym watku
save_data_thread = _thread.start_new_thread(save_data_periodically, ())

try:
    # Nadpisanie pliku, polaczenie z siecia i uruchomienie serwera
    clear_file()
    ip = connect()
    connection = open_socket(ip)
    serve(connection)
except KeyboardInterrupt:
    machine.reset()

