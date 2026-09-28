#!/usr/bin/env python3
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


SOURCE_URL = "https://github.com/f1db/f1db"
SOURCE_LICENSE = "CC BY 4.0"


class CircuitImportError(ValueError):
    pass


def _number(value: str) -> int | float:
    try:
        number = float(value)
    except ValueError as error:
        raise CircuitImportError(f"Некорректное число в viewBox: {value}") from error
    return int(number) if number.is_integer() else number


def _read_mapping(path: Path) -> dict[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CircuitImportError(f"Не удалось прочитать mapping: {path}") from error
    if not isinstance(payload, dict) or not payload:
        raise CircuitImportError("Mapping должен быть непустым JSON-объектом.")

    mapping: dict[str, str] = {}
    used_files: set[str] = set()
    for slug, filename in payload.items():
        if not isinstance(slug, str) or not slug or not isinstance(filename, str):
            raise CircuitImportError("Mapping содержит некорректную запись.")
        if filename in used_files:
            raise CircuitImportError(f"Файл указан более одного раза: {filename}")
        mapping[slug] = filename
        used_files.add(filename)
    return mapping


def _extract_svg(svg_path: Path) -> tuple[list[int | float], str]:
    if not svg_path.is_file():
        raise CircuitImportError(f"SVG не найден: {svg_path}")
    try:
        root = ET.parse(svg_path).getroot()
    except (ET.ParseError, OSError) as error:
        raise CircuitImportError(f"Не удалось прочитать SVG: {svg_path}") from error

    raw_view_box = root.attrib.get("viewBox", "").replace(",", " ").split()
    if not raw_view_box and root.attrib.get("width") and root.attrib.get("height"):
        raw_view_box = ["0", "0", root.attrib["width"], root.attrib["height"]]
    if len(raw_view_box) != 4:
        raise CircuitImportError(
            f"SVG не содержит viewBox или размеры: {svg_path}"
        )
    view_box = [_number(item) for item in raw_view_box]

    paths = [
        element.attrib["d"].strip()
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "path" and element.attrib.get("d", "").strip()
    ]
    if not paths:
        raise CircuitImportError(f"SVG не содержит path: {svg_path}")
    primary_path = max(paths, key=len)
    return view_box, primary_path


def import_circuits(
    source_dir: Path,
    mapping_path: Path,
    output_dir: Path,
) -> list[Path]:
    mapping = _read_mapping(mapping_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for slug, filename in sorted(mapping.items()):
        view_box, path = _extract_svg(source_dir / filename)
        payload = {
            "slug": slug,
            "viewBox": view_box,
            "path": path,
            "source": SOURCE_URL,
            "license": SOURCE_LICENSE,
        }
        destination = output_dir / f"{slug}.json"
        destination.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        created.append(destination)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Подготовить SVG-трассы F1DB для ApexGrid")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()
    created = import_circuits(
        arguments.source_dir,
        arguments.mapping,
        arguments.output_dir,
    )
    print(f"Создано файлов: {len(created)}")


if __name__ == "__main__":
    main()
