import socket
import threading  # Flere klienter skal kunne sende samtidig.

# socket giver TCP/IP-kommunikation uden eksterne biblioteker.

HOST = "127.0.0.1"
PORT = 5000
MAX_MESSAGE_SIZE = 65536
clients = {}
# Beskytter listen, når klienttråde tilføjes eller fjernes samtidig.
clients_lock = threading.Lock()


def receive_exact(connection, size):
    """TCP kan dele data op: læs alle ønskede bytes."""
    data = bytearray()
    while len(data) < size:
        chunk = connection.recv(size - len(data))
        if not chunk:
            if not data:
                return None
            raise ConnectionError("Forbindelsen sluttede midt i en besked.")
        data.extend(chunk)
    return bytes(data)


def receive_message(connection):
    # Læs headeren først: TCP bevarer ikke grænserne mellem afsendelser.
    header = receive_exact(connection, 4)
    if header is None:
        return None
    size = int.from_bytes(header, "big")
    if not 1 <= size <= MAX_MESSAGE_SIZE:
        raise ValueError("Ugyldig beskedlængde.")
    message = receive_exact(connection, size)
    if message is None:
        raise ConnectionError("Beskedens indhold mangler.")
    return message


def send_message(connection, message):
    if not 1 <= len(message) <= MAX_MESSAGE_SIZE:
        raise ValueError("Beskeden skal fylde mellem 1 og 65536 bytes.")
    # Fire bytes med længden efterfulgt af ciphertext.
    connection.sendall(len(message).to_bytes(4, "big") + message)


def broadcast(message, sender):
    # Kopien tillader, at andre tråde ændrer klientlisten under videresendelse.
    with clients_lock:
        recipients = list(clients.items())
    for connection, send_lock in recipients:
        if connection is sender:
            continue
        try:
            # Låsen forhindrer flere tråde i at blande data til samme modtager.
            with send_lock:
                send_message(connection, message)
        except OSError:
            pass  # Modtagerens egen tråd rydder op ved afbrydelse.


def handle_client(connection, address):
    print(f"Klient forbundet: {address}", flush=True)
    try:
        with connection:
            while True:
                ciphertext = receive_message(connection)
                if ciphertext is None:
                    break
                # Serveren hverken afleder nøgler eller dekrypterer indholdet.
                broadcast(ciphertext, connection)
    except (OSError, ValueError) as error:
        print(f"Forbindelsen til {address} sluttede: {error}", flush=True)
    finally:
        # Oprydning sker både ved normal lukning og ved fejl i forbindelsen.
        with clients_lock:
            clients.pop(connection, None)
        print(f"Klient frakoblet: {address}", flush=True)


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        # IPv4 og TCP: bind vælger lokal adresse, listen åbner for forbindelser.
        server.bind((HOST, PORT))
        server.listen()
        print(f"Serveren lytter på {HOST}:{PORT}", flush=True)
        while True:
            connection, address = server.accept()
            with clients_lock:
                clients[connection] = threading.Lock()
            # Hver klient håndteres, mens serveren fortsat accepterer forbindelser.
            threading.Thread(
                target=handle_client, args=(connection, address), daemon=True
            ).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServeren er stoppet.")
    except OSError as error:
        print(f"Serverfejl: {error}")
