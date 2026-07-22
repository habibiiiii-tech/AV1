# AV-Assistent V1

Erster lokaler Prototyp für Produktsuche bei GEALAN, GROWE und NÜSSING.

## Start unter Windows
1. Python 3.11+ installieren.
2. Diesen Ordner entpacken.
3. Eingabeaufforderung im Ordner öffnen.
4. `pip install -r requirements.txt`
5. `streamlit run app.py`
6. Der Browser öffnet den AV-Assistenten.

## Chromebook
Wenn Linux-Entwicklungsumgebung aktiviert ist, funktionieren dieselben Befehle.
Alternativ kann die App später auf einem internen Server gehostet werden.

## Wichtig
- V1 verwendet eine lokale SQLite-Datenbank (`av_assistent.db`).
- Öffentliche Webseiten werden beim ersten Start als Test-Wissensbasis eingelesen.
- PDF/TXT-Unterlagen können unter „Quellen & Dokumente“ ergänzt werden.
- Die Suche zeigt Belegstellen statt unbelegte KI-Antworten zu erzeugen.
- Fachhändler-Unterlagen später nur hochladen, wenn die betriebliche Nutzung/Verarbeitung erlaubt ist.
- ELO ist noch NICHT angebunden. Dafür benötigen wir später Informationen zu ELO-Version, API/Berechtigungen und Datenstruktur.
