# Mandatory Assignment One – Applied Cryptography

En terminalbaseret chat i Python, der demonstrerer TCP/IP, PBKDF2-HMAC-SHA256 og XOR. Flere klienter kommunikerer gennem en central server.

**Dette er en usikker undervisningsdemo. Brug den ikke til følsomme oplysninger.**

## Start i VS Code

Åbn projektmappen i VS Code. Python og uv skal være tilgængelige. Projektet bruger Python 3.13 via `.python-version` og har ingen eksterne Python-afhængigheder.

Kør først i projektmappen:

```powershell
uv sync
```

Åbn tre terminaler via **Terminal → New Terminal**. Alle terminaler skal stå i projektmappen, eksempelvis:

```powershell
cd C:\Users\moha3\crypto-mandatory
```

`cd` skifter mappe. `server.py` er en fil, så brug ikke `cd server.py`.

**Terminal 1 – server:**

```powershell
uv run server.py
```

**Terminal 2 – første klient:**

```powershell
uv run client.py
```

**Terminal 3 – anden klient:**

```powershell
uv run client.py
```

Indtast et brugernavn i hver klient og præcis samme fælles password. Aftal passwordet manuelt uden for chatten. Passwordet vises ikke under indtastning. Vent, til begge klienter er forbundet, og send derefter beskeder i begge retninger.

Skriv `/quit` for at afslutte en klient. Stop serveren med Ctrl+C. Hvis serveren afbrydes, kan klientens inputløkke stadig vente; skriv `/quit` eller brug Ctrl+C.

## Arkitektur

```text
Klient 1  <--- ciphertext over TCP --->  Server  <--- ciphertext over TCP --->  Klient 2
PBKDF2 + XOR                        127.0.0.1:5050                         PBKDF2 + XOR
```

Serveren videresender ciphertext til alle andre tilsluttede klienter. Den modtager hverken passwordet eller nøglen og dekrypterer ikke beskederne. Brugernavnet krypteres sammen med beskeden.

Serveren bruger en tråd pr. klient. Klienten bruger en separat modtagetråd, så den kan modtage beskeder, mens `input()` venter på brugerens tekst. Låse beskytter serverens klientliste og sikrer, at samtidige afsendelser til samme modtager ikke blandes sammen.

TCP er en byte-stream og bevarer ikke beskedgrænser. Derfor sendes hver besked som:

```text
[4 bytes længde, big-endian][ciphertext med den angivne længde]
```

`receive_exact()` samler bytes, indtil hele headeren eller beskeden er modtaget. Maksimal beskedstørrelse er 65536 bytes inklusive brugernavn og separator. Længdefeltet er ukrypteret.

## Nøgleafledning og XOR

`derive_key()` bruger `hashlib.pbkdf2_hmac()` med:

- SHA-256 som hashfunktion i HMAC.
- Det fælles, offentlige salt `b"mandatory-one-demo-salt"`.
- 100.000 iterationer.
- En afledt nøgle på 32 bytes.

PBKDF2 afleder nøglemateriale fra passwordet. Iterationerne gør hvert passwordgæt mere beregningstungt. Saltet er ikke hemmeligt; her er det fast for at gøre demonstrationen enkel. Samme password og parametre giver samme nøgle. SHA-256 er en hashfunktion, ikke selve krypteringen.

`encrypt_message()` omdanner tekst til UTF-8-bytes med `.encode()` og anvender XOR med nøglens bytes. Når nøglen slipper op, gentages den. `decrypt_message()` anvender samme XOR-operation og omdanner resultatet til tekst med `.decode()`:

```text
(besked XOR nøgle) XOR nøgle = besked
```

## Sikkerhedsbegrænsninger

Gentaget XOR-nøgle er usikkert. For to beskeder med samme nøgle gælder `C1 XOR C2 = P1 XOR P2`, hvilket afslører relationer mellem teksterne. Kendt tekst kan afsløre nøglemateriale. PBKDF2 fjerner ikke denne svaghed.

En rigtig One-Time Pad kræver en tilfældig, hemmelig nøgle, der er lige så lang som beskeden og kun bruges én gang. Denne løsning er hverken en sikker OTP eller en sikker end-to-end-krypteringsprotokol.

Der er ingen autentifikation eller integritetskontrol. Beskeder kan ændres, og brugernavne kan efterlignes. Forkert password kan give en UTF-8-fejl, men gyldig UTF-8 beviser ikke korrekt nøgle eller uændret indhold. Serveren kan se forbindelser, beskedlængder og tidspunkter.

Der er ingen beskedhistorik, offline-kø eller automatisk genforbindelse. En langsom modtager kan blokere videresendelse. Modtagne beskeder kan visuelt afbryde inputlinjen.

## Manuel test

1. Start serveren og to klienter med samme password.
2. Send flere beskeder fra klient 1 og svar fra klient 2 uden genstart.
3. Prøv danske tegn som `æøå` og en længere besked.
4. Kontrollér, at serveren kun viser forbindelsesstatus, ikke chattekst.
5. Afslut én klient med `/quit`; kontrollér, at serveren fortsætter.
6. Start klienten igen, og kontrollér, at beskeder kan udveksles.

Denne README-opdatering omfatter ikke en ny manuel chat- eller Wireshark-test. Tidligere testresultater for tidligere kodeversioner er ikke dokumentation for, at denne version er fuldt testet.

## Wireshark på Windows

1. Vælg loopback-interfacet, typisk **Adapter for loopback traffic capture**, fordi serveren kører på `127.0.0.1`.
2. Start optagelsen, og forbind derefter begge klienter.
3. Brug displayfilteret `tcp.port == 5050`.
4. Send en testbesked og vælg en pakke med TCP-data. Filteret `tcp.port == 5050 && tcp.len > 0` kan hjælpe.
5. Markér datafeltet og se ciphertext i **Packet Bytes**. De første fire bytes i en komplet indrammet besked er længden; resten er ciphertext. En besked kan være fordelt over flere TCP-pakker.
6. Brug eventuelt **Follow → TCP Stream** med hex-visning til at se den samlede strøm.
7. Tag selv et screenshot med filter, valgt pakke og datafelt til opgavens PDF. Beskriv jeres egne observationer.

Den aktuelle kode bruger **5050**, ikke den tidligere port 5000. Hvis porten ændres, skal filteret følge med. At teksten ikke umiddelbart kan læses i optagelsen er ikke bevis for sikker kryptering.

## Filer og gennemgang

- `client.py`: brugerinput, nøgleafledning, XOR og modtagelse.
- `server.py`: TCP-indramning, forbindelser og videresendelse. Klienten importerer også TCP-hjælpefunktioner herfra; importen starter ikke serveren.
- `pyproject.toml`, `uv.lock` og `.python-version`: projektkonfiguration til uv.
- `.gitignore`: holder lokalt miljø og Python-cache ude af Git.

Læs først `derive_key()`, `xor_bytes()`, `encrypt_message()` og `decrypt_message()`. Følg derefter beskeden gennem `send_message()`, serverens `handle_client()` og `broadcast()` og til sidst klientens `receive_messages()`.

## Aflevering

Afleverings-ZIP'en skal kun indeholde `server.py`, `client.py` og `documentation.pdf`. PDF'en udarbejdes separat og må højst fylde to sider. Medtag ikke `.venv`, `.git`, cachefiler eller uv-konfiguration i ZIP'en. Denne opdatering opretter ikke PDF eller ZIP.
