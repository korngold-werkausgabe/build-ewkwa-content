# Build Content Pipeline

## Build Edirom

### As Submodule

If the repository is integrated as submodules in a volume repository, the start script must be created once from the root of the main repository.

```bash
cp build-edirom-content/build-edirom-content.sh build-edirom-content.sh 
```

## Development
Build Container with all dependencies 
```bash
docker compose -f build-ewkwa-content/build-edirom/docker-compose.dev.yml up -d
```
Run bash in container
```bash
docker compose -f build-ewkwa-content/build-edirom/docker-compose.dev.yml exec dev bash
```
Start script in container
```bash
python build-ewkwa-content/build-edirom/prepare-content.py 
```