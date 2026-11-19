# SIPL Language Toolkit

Інструментарій для мови програмування **SIPL** (Simple Imperative Programming Language) в межах курсового проєкту з дисципліни «Теорія програмування».

## Обраний трек: «Interpreter + Visualization

| ID | Завдання | Бали | Статус |
|---|---|---|---|
| CORE-01 | Формальна специфікація SIPL (граматика, лексика, ≥10/≥10 тестів) | 0.5 | В процесі |
| CORE-02 | Парсер та типізоване AST з `SourceSpan` | 1.5 | Заплановано |
| CORE-03 | Інтерпретатор SIPL (ліміт кроків, ≥80% покриття) | 2.0 | Заплановано |
| CORE-04 | Подієва модель виконання та `trace` | 1.0 | Заплановано |
| CORE-05 | CLI (`parse`, `check`, `run`, `trace`) + JSON-режим | 1.0 | Заплановано |
| VIS-01 | Візуалізація дерева синтаксичного виводу (`Text`, `JSON`, `DOT/SVG`) | 1.5 | Заплановано |
| VIS-02 | Візуалізація AST та порівняння `Parse Tree ↔ AST` (`SVG/HTML`) | 1.0 | Заплановано |
| REL-01 | CI (GitHub Actions: lint, type-check, tests, build) | 0.5 | Заплановано |
| REL-02 | GitHub Releases + SemVer + `CHANGELOG.md` | 0.5 | Заплановано |
| REL-03 | Публікація Python-пакета в PyPI | 0.5 | Заплановано |


## Встановлення для розробки (у `.venv`)

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
pytest

#### Встанови пакети у `.venv`
Переконайся, що `.venv` активоване, і виконай:
```bash
pip install -e ".[dev]"