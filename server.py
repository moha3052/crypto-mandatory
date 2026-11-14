
import socket
import threading

# Serverens adresse og port
HOST = "127.0.0.1"
PORT = 5050

# Maksimal størrelse på en besked
MAX_MESSAGE_SIZE = 65536

# Liste over tilsluttede klienter
clients = []
clients_lock = threading.Lock()


def receive_exact(connection, size):
    # TCP kan dele en besked op i flere dele.
    # Derfor læser vi, indtil alle bytes er modtaget.
    data = b""

    while len(data) < size:
        chunk = connection.recv(size - len(data))

        if not chunk:
            return None

        data += chunk

    return data


def receive_message(connection):
    # De første 4 bytes fortæller beskedens længde
    header = receive_exact(connection, 4)

    if header is None:
        return None

    size = int.from_bytes(header, "big")

    if size < 1 or size > MAX_MESSAGE_SIZE:
        raise ValueError("Ugyldig beskedlængde")

    return receive_exact(connection, size)


def send_message(connection, message):
    # Send først længden og derefter selve beskeden
    header = len(message).to_bytes(4, "big")
    connection.sendall(header + message)


def broadcast(message, sender):
    # Send ciphertext til alle andre klienter
    with clients_lock:
        recipients = list(clients)

    for client, send_lock in recipients:
        if client != sender:
            try:
                with send_lock:
                    send_message(client, message)
            except OSError:
                pass


def handle_client(connection, address):
    print(f"Klient forbundet: {address}")

    try:
        while True:
            # Modtag krypterede bytes
            message = receive_message(connection)

            if message is None:
                break

            # Serveren dekrypterer ikke beskeden
            broadcast(message, connection)

    except (OSError, ValueError) as error:
        print(f"Klientfejl: {error}")

    finally:
        # Fjern klienten ved afbrydelse
        with clients_lock:
            clients[:] = [
                item for item in clients
                if item[0] != connection
            ]

        connection.close()
        print(f"Klient afbrudt: {address}")


def main():
    # AF_INET = IPv4
    # SOCK_STREAM = TCP
    with socket.socket(
        socket.AF_INET, socket.SOCK_STREAM
    ) as server:

        server.bind((HOST, PORT))
        server.listen()

        print(f"Server startet på {HOST}:{PORT}")

        while True:
            # Vent på en klient
            connection, address = server.accept()

            with clients_lock:
                clients.append(
                    (connection, threading.Lock())
                )

            # Hver klient får sin egen tråd
            thread = threading.Thread(
                target=handle_client,
                args=(connection, address),
                daemon=True
            )

            thread.start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stoppet")
