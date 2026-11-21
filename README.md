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

## Einrichtung (einmalig, etwa 1 Stunde)

### 1. Instagram auf Creator-Konto umstellen (2 Minuten)
Instagram-App → Einstellungen → Kontotyp und Tools → Zu professionellem Konto wechseln → Creator.

### 2. Meta-App anlegen (30 Minuten)
1. developers.facebook.com öffnen, mit Facebook anmelden, als Entwickler registrieren.
2. Meine Apps → App erstellen → Anwendungsfall „Nachrichten und Inhalte auf Instagram verwalten“ wählen.
3. In der App: Instagram → „API-Einrichtung mit Instagram-Login“.
4. Bei „Zugriffsschlüssel generieren“ dein Instagram-Konto hinzufügen und anmelden.
5. Den angezeigten **Token** kopieren und die **Instagram-Konto-ID** (Zahl) notieren.

Die Bezeichnungen bei Meta ändern sich manchmal. Wenn ein Menüpunkt anders heißt: Screenshot an Claude schicken.

### 3. Secrets in GitHub eintragen (10 Minuten)
Repository → Settings → Secrets and variables → Actions → New repository secret:

| Name | Inhalt |
|---|---|
| `IG_ACCESS_TOKEN` | der Token aus Schritt 2 |
| `IG_USER_ID` | die Instagram-Konto-ID |
| `GH_PAT` | GitHub-Token zum automatischen Erneuern (siehe unten) |

`GH_PAT` anlegen: github.com → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate. Nur dieses Repository auswählen, Berechtigung „Secrets: Read and write“. Ablauf: 1 Jahr.

### 4. Testen
Actions → „Instagram posten“ → Run workflow → Haken bei „Nur testen“ lassen. Zeigt an, was gepostet würde, ohne zu posten.

## Token
Der Instagram-Token gilt 60 Tage. Der Workflow „Instagram-Token erneuern“ verlängert ihn jeden Montag automatisch.

## Folien selbst erzeugen
```
python3 tools/make_slides.py slides.json queue/2026-11-24-thema/
```
Format von `slides.json` steht oben in `tools/make_slides.py`.
