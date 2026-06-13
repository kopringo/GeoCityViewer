# GeoCity Viewer

Projekt do przeglądania danych o zabudowie miejskiej na mapie. Umożliwia wizualizację budynków z plików GeoPackage oraz filtrowanie ich według roku budowy.

Aplikację można otworzyć pod adresem: [https://kopringo.github.io/GeoCityViewer/](https://kopringo.github.io/GeoCityViewer/)

## Struktura

- `pub/` — statyczna strona WWW (mapa Leaflet + OpenStreetMap)
- `data/` — pliki źródłowe GeoPackage (`.gpkg`)
- `gpkg_to_json.py` — konwersja danych GPKG do JSON

## Konwersja danych

Skrypt wymaga biblioteki GDAL (`python3-gdal`).

```bash
# Jeden plik → stdout
python3 gpkg_to_json.py data/elb/esipbudynki_1946_2000_t.gpkg

# Katalog z plikami .gpkg → plik wynikowy
python3 gpkg_to_json.py data/ -o pub/data/buildings.json

# Jeden plik → plik wynikowy
python3 gpkg_to_json.py data/elb/esipbudynki_po_2001_t.gpkg -o pub/data/buildings.json
```

Gdy podasz katalog, skrypt rekurencyjnie wyszuka wszystkie pliki `.gpkg` i połączy je w jeden zbiorczy JSON.

## Uruchomienie lokalne

```bash
cd pub
python3 -m http.server 8080
```

Następnie otwórz `http://localhost:8080`.

## Build (GitHub Pages)

Workflow `.github/workflows/pages.yml` uruchamia `gpkg_to_json.py` na katalogu `data/` i publikuje wynik wraz ze stroną z katalogu `pub/`.
