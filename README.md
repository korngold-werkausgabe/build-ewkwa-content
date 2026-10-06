# Build Content Pipeline

Automated process for creating Edirom edition XAR files from structured XML documents.

## Installation as a Submodule

To integrate this repository into a volume project (series/volume repository) as a submodule:

```bash
# In the root of the volume repo
git submodule add <repo-url> build-ewkwa-content
cd build-ewkwa-content

# Copy the build script into the project root
cp template_build-ewkwa-content.sh ../build-ewkwa-content.sh
cd ..

# Use it from the project root
./build-ewkwa-content.sh
```

## Required Documents and Structure

### Directory Overview

The project expects the following folders in the **project root**:

```
.
├── frbr-tree.xml                    # Main directory with work overview (required)
├── Edirom-Config/                   # Configuration files
├── Quellenuebersicht/               # Source directory XML files
├── Textkritische-Anmerkungen/       # Text-critical annotation XML files
├── Konkordanzen/                    # Concordance CSV files
├── Quellen/                         # Source/manuscript XML files
├── Druckfahnen/                     # (Optional) galley proofs / proof sheets
└── build-xar/                       # (Auto-generated) output directory for XAR files
```

### 1. frbr-tree.xml (Required)

**Location**: Project root  
**Description**: Main document containing the work overview and the structure of all opus groups

**MEI-XML structure**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<mei xmlns="http://www.music-encoding.org/ns/mei">
  <meiHead>
    <fileDesc>
      <titleStmt>
        <title type="volume">Title of the edition</title>
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

### 2. Quellenuebersicht/ (With kb_sources_*.xml)

**Location**: `Quellenuebersicht/`  
**Files**: `kb_sources_op09-1.xml`, `kb_sources_op14.xml`, etc.  
**Description**: Source indexes for each opus group

**XML format**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sources>
  <source xml:id="source1">
    <identifier>Signature</identifier>
    <title>Title of the source</title>
    <!-- additional metadata -->
  </source>
</sources>
```

### 3. Textkritische-Anmerkungen/ (With tka_*.xml)

**Location**: `Textkritische-Anmerkungen/`  
**Files**: `tka_op09-1.xml`, `tka_op14-1.xml`, etc.  
**Description**: Text-critical comments and annotations

**XML format**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<annotations>
  <note xml:id="tka1">
    <label>1.1</label>
    <desc>Text-critical comment...</desc>
  </note>
</annotations>
```

### 4. Konkordanzen/ (With .csv files)

**Location**: `Konkordanzen/`  
**Files**: `op09-1_Konkordanz.csv`, `op14-1_Konkordanz.csv`, etc.  
**Description**: Concordances between different sources/versions

**CSV format**:
```
# [mdiv]_[measure]
edition,siglumA,siglumB,siglumC
1_1,1_1,1_1,1_1
```

### 5. Quellen

**Location**: `Quellen/`  
**Files**: `A-Wn_MS51588-4-01.xml`, `US-Wc_KC06-02.xml`, etc.  
**Description**: MEI-encoded sources/manuscripts

### 6. Edirom-Config

**Location**: `Edirom-Config/`  
**Files**: `nav.xml` or, for multiple works, `[edition-slug]-nav.xml`  
**Description**: Navigation structures and work properties

**XML format**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ediromFile viewType="map">
  <work type="collection" title="Work">
    <!-- Navigation and links -->
  </work>
</ediromFile>
```

## Build Process

### Automatic Build (Recommended)

```bash
./build-ewkwa-content.sh
```

What happens:
1. **Docker image is built** with all dependencies
2. **Python script runs**: `prepare-content.py` processes the XML files
3. **Edirom packaging**: Generates the XAR file
4. **Output**: The XAR file is saved in `build-xar/`
5. **Logs**: `prepare-content.log` is stored in `build-xar/`

### Output

After a successful build:
- `build-xar/*.xar` - Final Edirom edition (deployable)
- `build-xar/prepare-content.log` - Build log with error messages

## Development

For direct debugging in the container:

`.env` determines which repositories the data is pulled from.

```bash
# Start the development container with docker-compose
docker compose -f build-edirom/dev.docker-compose.yml up -d

# Open a bash shell in the container
docker compose -f build-edirom/dev.docker-compose.yml exec dev bash

# Run the Python script directly (for debugging)
python build-edirom/main.py
```

## Troubleshooting

- **XAR file is empty**: Check `prepare-content.log` for errors in the Python script
- **Build fails**: Rebuild the Docker image: `docker build -f build-ewkwa-content/build-edirom/Dockerfile.dev -t edirom-content-builder:local .`
- **Permission errors**: `chmod +x ./build-ewkwa-content.sh`

## Dev-Env
`docker compose -f build-edirom/dev.docker-compose.yml exec dev python /app/build-ewkwa-content/main.py`
