#!/usr/bin/env python3
"""Odczyt GeoPackage i zapis warstw, kolumn i danych jako JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from osgeo import ogr

DEFAULT_INPUT = "data"
DEFAULT_OUTPUT = None

PROPERTY_FIELDS = (
    "identyfikator_budynku",
    "rok_zakonczenia_budowy",
    "_dzialka_identyfikator_egb",
)

OGR_FIELD_TYPES = {
    ogr.OFTInteger: "Integer",
    ogr.OFTIntegerList: "IntegerList",
    ogr.OFTReal: "Real",
    ogr.OFTRealList: "RealList",
    ogr.OFTString: "String",
    ogr.OFTStringList: "StringList",
    ogr.OFTWideString: "WideString",
    ogr.OFTWideStringList: "WideStringList",
    ogr.OFTBinary: "Binary",
    ogr.OFTDate: "Date",
    ogr.OFTTime: "Time",
    ogr.OFTDateTime: "DateTime",
    ogr.OFTInteger64: "Integer64",
    ogr.OFTInteger64List: "Integer64List",
}


def field_type_name(field_def: ogr.FieldDefn) -> str:
    return OGR_FIELD_TYPES.get(field_def.GetType(), str(field_def.GetType()))


def field_value(feature: ogr.Feature, field_idx: int):
    if feature.IsFieldNull(field_idx):
        return None

    field_type = feature.GetFieldDefnRef(field_idx).GetType()
    if field_type == ogr.OFTInteger:
        return feature.GetFieldAsInteger(field_idx)
    if field_type == ogr.OFTInteger64:
        return feature.GetFieldAsInteger64(field_idx)
    if field_type == ogr.OFTReal:
        return feature.GetFieldAsDouble(field_idx)
    return feature.GetFieldAsString(field_idx)


def layer_columns(layer_def: ogr.LayerDefn) -> list[dict]:
    columns = []
    for i in range(layer_def.GetFieldCount()):
        field_def = layer_def.GetFieldDefn(i)
        if field_def.GetName() not in PROPERTY_FIELDS:
            continue
        columns.append(
            {
                "name": field_def.GetName(),
                "type": field_type_name(field_def),
                "width": field_def.GetWidth(),
                "precision": field_def.GetPrecision(),
            }
        )
    return columns


def layer_features(layer: ogr.Layer, layer_def: ogr.LayerDefn) -> list[dict]:
    features = []
    layer.ResetReading()
    for feature in layer:
        properties = {}
        for i in range(layer_def.GetFieldCount()):
            name = layer_def.GetFieldDefn(i).GetName()
            if name in PROPERTY_FIELDS:
                properties[name] = field_value(feature, i)

        geometry = feature.GetGeometryRef()
        features.append(
            {
                "id": feature.GetFID(),
                "geometry": json.loads(geometry.ExportToJson()) if geometry else None,
                "properties": properties,
            }
        )
    return features


def read_gpkg(gpkg_path: Path) -> dict:
    dataset = ogr.Open(str(gpkg_path), 0)
    if dataset is None:
        raise RuntimeError(f"Nie można otworzyć pliku: {gpkg_path}")

    layers = []
    for layer_idx in range(dataset.GetLayerCount()):
        layer = dataset.GetLayerByIndex(layer_idx)
        layer_def = layer.GetLayerDefn()
        geom_field = (
            layer_def.GetGeomFieldDefn(0).GetName()
            if layer_def.GetGeomFieldCount() > 0
            else None
        )

        layers.append(
            {
                "name": layer.GetName(),
                "geometry_type": ogr.GeometryTypeToName(layer_def.GetGeomType()),
                "geometry_column": geom_field,
                "feature_count": layer.GetFeatureCount(),
                "columns": layer_columns(layer_def),
                "features": layer_features(layer, layer_def),
            }
        )

    return {
        "source": str(gpkg_path),
        "layer_count": len(layers),
        "layers": layers,
    }


def find_gpkg_files(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() != ".gpkg":
            raise ValueError(f"Oczekiwano pliku .gpkg, otrzymano: {path}")
        return [path]

    if not path.is_dir():
        raise FileNotFoundError(f"Nie znaleziono ścieżki: {path}")

    gpkg_files = sorted(path.rglob("*.gpkg"))
    if not gpkg_files:
        raise FileNotFoundError(f"Brak plików .gpkg w katalogu: {path}")
    return gpkg_files


def merge_results(results: list[dict]) -> dict:
    if len(results) == 1:
        return results[0]

    merged_features = []
    merged_columns = []
    geometry_type = None
    geometry_column = None
    sources = []

    for result in results:
        sources.append(result["source"])
        for layer in result["layers"]:
            if geometry_type is None:
                geometry_type = layer["geometry_type"]
                geometry_column = layer["geometry_column"]
            if not merged_columns:
                merged_columns = layer["columns"]
            merged_features.extend(layer["features"])

    return {
        "sources": sources,
        "source_count": len(sources),
        "layer_count": 1,
        "layers": [
            {
                "name": "budynki",
                "geometry_type": geometry_type,
                "geometry_column": geometry_column,
                "feature_count": len(merged_features),
                "columns": merged_columns,
                "features": merged_features,
            }
        ],
    }


def read_input(path: Path) -> dict:
    gpkg_files = find_gpkg_files(path)
    results = [read_gpkg(gpkg_file) for gpkg_file in gpkg_files]
    return merge_results(results)


def write_result(result: dict, output: Path | None) -> None:
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if output is None:
        sys.stdout.write(payload)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Odczyt plików GeoPackage i zapis danych jako JSON"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=DEFAULT_INPUT,
        help=f"Plik .gpkg lub katalog z plikami .gpkg (domyślnie: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT,
        help="Plik JSON wynikowy (domyślnie: stdout)",
    )
    args = parser.parse_args()

    ogr.UseExceptions()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    result = read_input(input_path)
    write_result(result, output_path)


if __name__ == "__main__":
    main()
