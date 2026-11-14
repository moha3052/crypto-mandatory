
import hashlib
import getpass
import socket
import threading

# Vi genbruger serverens TCP-funktioner
from server import (
    HOST,
    PORT,
    MAX_MESSAGE_SIZE,
    send_message,
    receive_message
)

# Samme salt skal bruges hos begge klienter
SALT = b"mandatory-one-demo-salt"

# Antal iterationer i PBKDF2
ITERATIONS = 100000


def derive_key(password):
    # PBKDF2 afleder en nøgle fra passwordet
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        SALT,
        ITERATIONS,
        dklen=32
    )


def xor_bytes(data, key):
    # XOR sammenligner bits fra data og nøgle.
    # Modulo gentager nøglen, når den slipper op.
    # Dette er kun en USIKKER undervisningsdemo.
    result = []

    for i in range(len(data)):
        encrypted_byte = data[i] ^ key[i % len(key)]
        result.append(encrypted_byte)

    return bytes(result)


def encrypt_message(message, key):
    # Konverter tekst til bytes
    message_bytes = message.encode("utf-8")

    # XOR laver ciphertext
    return xor_bytes(message_bytes, key)


def decrypt_message(ciphertext, key):
    # Samme XOR-operation genskaber bytes
    decrypted_bytes = xor_bytes(ciphertext, key)

    # Konverter bytes tilbage til tekst
    return decrypted_bytes.decode("utf-8")


def receive_messages(connection, key):
    # Modtag beskeder fra serveren
    while True:
        try:
            ciphertext = receive_message(connection)

            if ciphertext is None:
                print("\nServeren er afbrudt")
                break

            # Dekrypter den modtagne besked
            message = decrypt_message(ciphertext, key)

            print(f"\n{message}\nBesked: ", end="", flush=True)

        except UnicodeDecodeError:
            # Forkert nøgle kan give ugyldig UTF-8.
            # Men gyldig UTF-8 beviser ikke korrekt nøgle.
            print("\nBeskeden kunne ikke læses")

        except (OSError, ValueError):
            print("\nForbindelsen er lukket")
            break


def main():
    username = input("Brugernavn: ")

    # Passwordet vises ikke i terminalen
    password = getpass.getpass("Fælles password: ")

    if not username or not password:
        print("Brugernavn og password må ikke være tomme")
        return

    # Afled en nøgle ved hjælp af PBKDF2
    key = derive_key(password)

    # Opret TCP-forbindelsen
    with socket.socket(
        socket.AF_INET, socket.SOCK_STREAM
    ) as client:

        client.connect((HOST, PORT))

        print("Forbundet til serveren!")
        print("Skriv /quit for at afslutte.")
        print("OBS: XOR er kun en usikker undervisningsdemo.")

        # Modtag beskeder i en separat tråd
        thread = threading.Thread(
            target=receive_messages,
            args=(client, key),
            daemon=True
        )

        thread.start()

        while True:
            message = input("Besked: ")

            if message == "/quit":
                break

            if not message:
                continue

            # Tilføj brugerens navn
            full_message = f"{username}: {message}"

            # Krypter inden afsendelse
            ciphertext = encrypt_message(
                full_message, key
            )

            if len(ciphertext) > MAX_MESSAGE_SIZE:
                print("Beskeden er for lang")
                continue

            # Send kun ciphertext
            send_message(client, ciphertext)

        # Luk forbindelsen, når brugeren afslutter
        try:
            client.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except ConnectionRefusedError:
        print("Start server.py først")
    except (KeyboardInterrupt, EOFError):
        print("\nKlienten er afsluttet")
    except OSError as error:
        print(f"Forbindelsesfejl: {error}")
