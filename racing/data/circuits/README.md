# Геометрии трасс ApexGrid

В каталоге хранится 23 контура трасс сезона 2026 и редакционные метаданные `metadata.json`. Каждый контур привязан к `Circuit.external_id` и имеет формат:

```json
{
  "slug": "suzuka",
  "viewBox": [0, 0, 500, 500],
  "path": "M…",
  "source": "https://github.com/f1db/f1db",
  "license": "CC BY 4.0"
}
```

Контуры сгенерированы скриптом `scripts/import_f1db_circuits.py` из SVG-активов F1DB commit `5487e45d4df4097080332f29a0513f275c1023cd`. Выбор конфигурации каждой трассы зафиксирован в `scripts/data/f1db-2026-circuits.json`.

Для повторной генерации:

```bash
python scripts/import_f1db_circuits.py \
  --source-dir /path/to/f1db/src/assets/circuits/black \
  --mapping scripts/data/f1db-2026-circuits.json \
  --output-dir racing/data/circuits
```

Исходные материалы: [F1DB](https://github.com/f1db/f1db), лицензия [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Изменения ApexGrid: из SVG извлечены `viewBox`/размеры и основной `path`, затем данные нормализованы в JSON.
