import getpass
import hashlib  # Standardbibliotekets PBKDF2 afleder nøglemateriale fra passwordet.
import socket  # Opretter TCP-forbindelsen til serveren.
import threading  # Modtagelse skal kunne fortsætte, mens input() venter.

# Importen deler TCP-hjælpere; den starter ikke serveren.
from server import HOST, PORT, MAX_MESSAGE_SIZE, receive_message, send_message

# Offentligt, fælles salt: begge klienter skal aflede præcis samme nøgle.
SALT = b"mandatory-one-demo-salt"
# Gentagne beregninger gør passwordgæt dyrere; tallet følger opgavekravet.
KDF_ITERATIONS = 100_000
KEY_LENGTH = 32


def derive_key(password):
    """Begge klienter bruger samme offentlige salt og parametre."""
    if not password:
        raise ValueError("Password må ikke være tomt.")
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), SALT, KDF_ITERATIONS, dklen=KEY_LENGTH
    )


def xor_bytes(data, key):
    # ^ kombinerer bits. Modulo gentager nøglens bytes ved lange beskeder.
    # (message XOR key) XOR key = message. Genbrug af nøglen er USIKKERT.
    return bytes(value ^ key[index % len(key)] for index, value in enumerate(data))


def encrypt_message(message, key):
    """Omdan tekst til UTF-8-bytes, og XOR-krypter dem før afsendelse."""
    return xor_bytes(message.encode("utf-8"), key)


def decrypt_message(ciphertext, key):
    """Samme nøgle ophæver XOR; decode omdanner UTF-8-bytes til tekst."""
    return xor_bytes(ciphertext, key).decode("utf-8")


def receive_messages(connection, key, disconnected):
    try:
        while True:
            ciphertext = receive_message(connection)
            if ciphertext is None:
                break
            try:
                message = decrypt_message(ciphertext, key)
            except UnicodeDecodeError:
                print("\nKan ikke læse beskeden: forkert password eller ændrede data.")
                continue
            print(f"\n{message}\nBesked: ", end="", flush=True)
    except (OSError, ValueError) as error:
        if not disconnected.is_set():
            print(f"\nForbindelsesfejl: {error}")
    finally:
        if not disconnected.is_set():
            print("\nForbindelsen er lukket. Tryk Enter for at afslutte.", flush=True)
        disconnected.set()


def main():
    username = input("Brugernavn: ").strip()
    if not username:
        raise ValueError("Brugernavn må ikke være tomt.")
    key = derive_key(getpass.getpass("Fælles password: "))
    # TCP forbinder til den faste adresse; passwordet bliver lokalt i klienten.
    with socket.create_connection((HOST, PORT)) as connection:
        print("Forbundet. Undervisningsdemo med usikker XOR. Skriv /quit for at afslutte.")
        disconnected = threading.Event()
        # Modtagetråden viser beskeder, mens hovedtråden venter på input().
        receiver = threading.Thread(
            target=receive_messages, args=(connection, key, disconnected), daemon=True
        )
        receiver.start()
        try:
            while not disconnected.is_set():
                message = input("Besked: ")
                if message == "/quit" or disconnected.is_set():
                    break
                if not message:
                    continue
                ciphertext = encrypt_message(f"{username}: {message}", key)
                if len(ciphertext) > MAX_MESSAGE_SIZE:
                    print("Beskeden er for lang (maks. 65536 bytes inklusive navn).")
                    continue
                # Også brugernavnet krypteres. Password og nøgle sendes aldrig.
                send_message(connection, ciphertext)
        finally:
            disconnected.set()
            # shutdown vækker modtagetrådens recv(), så join() kan afslutte.
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            receiver.join()


if __name__ == "__main__":
    try:
        main()
    except ConnectionRefusedError:
        print("Forbindelsen blev afvist. Start server.py først.")
    except (KeyboardInterrupt, EOFError):
        print("\nKlienten er afsluttet.")
    except (OSError, ValueError) as error:
        print(f"Fejl: {error}")
