# Instagram-Poster

Postet Karussells automatisch auf Instagram. Läuft kostenlos auf GitHub Actions, dein PC muss nicht an sein.

## So funktioniert es

1. Ein Post ist ein Ordner in `queue/`, zum Beispiel `queue/2026-11-24-blutzucker/`.
2. Darin liegen die Folien (`01.jpg`, `02.jpg`, ...) und eine `post.json`:
   ```json
   {"publish_at": "2026-11-24T18:30:00+01:00", "caption": "Text mit #hashtags"}
   ```
3. Jede Stunde schaut GitHub nach, ob ein Post fällig ist, und veröffentlicht ihn.
4. Danach wandert der Ordner nach `posted/`. Bei einem Fehler landet er in `failed/` mit einer `result.json`, und GitHub schickt dir eine Mail.

Freigabe: Was in `queue/` liegt, wird gepostet. Willst du einen Post nicht, lösch den Ordner vor dem Termin.

## Einrichtung

Instagram-Zugang über die Meta-App (Unified Login, Systemnutzer-Token, läuft nie ab).

Secrets in GitHub eintragen: Repository → Settings → Secrets and variables → Actions → New repository secret

| Name | Inhalt |
|---|---|
| `IG_ACCESS_TOKEN` | Token aus der Meta-App (beginnt mit EAA) |
| `IG_USER_ID` | Instagram-Konto-ID (Zahl) |

Testen: Actions → „Instagram posten“ → Run workflow → Haken bei „Nur testen“ lassen.

Token kompromittiert? In business.facebook.com/settings → Nutzer → Systemnutzer den Token entfernen und in der Meta-App einen neuen erzeugen.

## Folien selbst erzeugen
```
python3 tools/make_slides.py slides.json queue/2026-11-24-thema/
```
Format von `slides.json` steht oben in `tools/make_slides.py`.
