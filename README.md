# Build Content Pipeline

Automatisierter Prozess zum Erstellen von Edirom-Edition XAR-Dateien aus strukturierten XML-Dokumenten.

## Installation als Submodule

Um dieses Repository in einem Bandprojekt (Serie/Band-Repository) als Submodule zu integieren:

```bash
# Im Root des Bandrepos
git submodule add <repo-url> build-ewkwa-content
cd build-ewkwa-content

# Das Build-Script in den Projektroot kopieren
cp template_build-ewkwa-content.sh ../build-ewkwa-content.sh
cd ..

# Vom Projektroot aus verwenden
./build-ewkwa-content.sh
```

## Erforderliche Dokumente und Struktur

### Verzeichnisübersicht

Das Projekt erwartet folgende Ordner in der **Projektroot**:

```
.
├── frbr-tree.xml                    # Hauptverzeichnis mit Werkübersicht (erforderlich)
├── Edirom-Config/                   # Konfigurationsdateien
├── Quellenuebersicht/               # Quellenverzeichnis XMLs
├── Textkritische-Anmerkungen/       # Textkritische Anmerkungen XMLs
├── Konkordanzen/                    # Konkordanz-CSV Dateien
├── Quellen/                         # Quellen/Handschriften XMLs
├── Druckfahnen/                     # (Optional) Druckfahnen/Galleyproofs
└── build-xar/                       # (Auto-generiert) Ausgabeverzeichnis der XAR-Dateien
```

### 1. frbr-tree.xml (Erforderlich)

**Ort**: Projektroot  
**Beschreibung**: Hauptdokument mit der Werkübersicht und Struktur aller Opusgruppen

**MEI-XML Struktur**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<mei xmlns="http://www.music-encoding.org/ns/mei">
  <meiHead>
    <fileDesc>
      <titleStmt>
        <title type="volume">Titel der Edition</title>
      </titleStmt>
      <pubStmt>
        <identifier type="volSlug">volume-identifier</identifier>
      </pubStmt>
    </fileDesc>
    <workList>
      <work type="collection" xml:id="work1">
        <relationList>
          <relation rel="hasPart" plist="#nav1 ..." />
        </relationList>
        <componentList>
          <work type="singleton" xml:id="work1-1"> ... </work>
        </componentList>
      </work>
    </workList>
  </meiHead>
</mei>
```

### 2. Quellenuebersicht/ (Mit kb_sources_*.xml)

**Ort**: `Quellenuebersicht/`  
**Dateien**: `kb_sources_op09-1.xml`, `kb_sources_op14.xml`, etc.  
**Beschreibung**: Quellenverzeichnisse für jede Opusgruppe

**XML-Format**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sources>
  <source xml:id="source1">
    <identifier>Signatur</identifier>
    <title>Titel der Quelle</title>
    <!-- weitere Metadaten -->
  </source>
</sources>
```

### 3. Textkritische-Anmerkungen/ (Mit tka_*.xml)

**Ort**: `Textkritische-Anmerkungen/`  
**Dateien**: `tka_op09-1.xml`, `tka_op14-1.xml`, etc.  
**Beschreibung**: Textkritische Kommentare und Anmerkungen

**XML-Format**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<annotations>
  <note xml:id="tka1">
    <label>1.1</label>
    <desc>Textkritischer Kommentar...</desc>
  </note>
</annotations>
```

### 4. Konkordanzen/ (Mit .csv Dateien)

**Ort**: `Konkordanzen/`  
**Dateien**: `op09-1_Konkordanz.csv`, `op14-1_Konkordanz.csv`, etc.  
**Beschreibung**: Konkordanzen zwischen verschiedenen Quellen/Versionen

**CSV-Format**:
```
# [mdiv]_[measure]
edition,siglumA,siglumB,siglumC
1_1,1_1,1_1,1_1
```

### 5. Quellen

**Ort**: `Quellen/`  
**Dateien**: `A-Wn_MS51588-4-01.xml`, `US-Wc_KC06-02.xml`, etc.  
**Beschreibung**: MEI-kodierte Quellen/Handschriften


### 6. Edirom-Config

**Ort**: `Edirom-Config/`  
**Dateien**: `nav.xml` oder bei mehreren Werken `[edition-slug]-nav.xml`
**Beschreibung**: Navigationsstrukturen und Eigenschaften der Werke

**XML-Format**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ediromFile viewType="map">
  <work type="collection" title="Werk">
    <!-- Navigation und Verknüpfungen -->
  </work>
</ediromFile>
```

## Build-Prozess

### Automatischer Build (Empfohlen)

```bash
./build-ewkwa-content.sh
```

Was passiert:
1. **Docker Image wird gebaut** mit allen Abhängigkeiten
2. **Python-Skript läuft**: `prepare-content.py` verarbeitet die XMLs
3. **Edirom-Packaging**: Generiert die XAR-Datei
4. **Output**: XAR-Datei landet in `build-xar/`
5. **Logs**: `prepare-content.log` wird in `build-xar/` gespeichert

### Ausgabe

Nach erfolgreichem Build:
- `build-xar/*.xar` - Fertige Edirom-Edition (deployable)
- `build-xar/prepare-content.log` - Build-Log mit Fehlermeldungen

## Development

Für direktes Debugging im Container:

```bash
# Entwicklungscontainer mit docker-compose starten
docker compose -f build-ewkwa-content/build-edirom/docker-compose.dev.yml up -d

# Bash im Container öffnen
docker compose -f build-ewkwa-content/build-edirom/docker-compose.dev.yml exec dev bash

# Python-Skript direkt ausführen (zum Debuggen)
python build-ewkwa-content/build-edirom/prepare-content.py
```

## Troubleshooting

- **XAR-Datei ist leer**: Check `prepare-content.log` für Fehler im Python-Skript
- **Build schlägt fehl**: Docker-Image rebuild: `docker build -f build-ewkwa-content/build-edirom/Dockerfile.dev -t edirom-content-builder:local .`
- **Berechtigungsfehler**: `chmod +x ./build-ewkwa-content.sh`