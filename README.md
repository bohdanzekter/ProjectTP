# SIPL Language Toolkit

Інструментарій для мови програмування **SIPL** (Simple Imperative Programming Language) в межах курсового проєкту з дисципліни «Теорія програмування».

[![CI](https://github.com/bohdanzekter/ProjectTP/actions/workflows/ci.yml/badge.svg)]
(https://github.com/bohdanzekter/ProjectTP/actions/workflows/ci.yml)

## Обраний трек: «Interpreter + Visualization

| ID | Завдання | Бали | Статус |
|---|---|---|---|
| CORE-01 | Формальна специфікація SIPL (граматика, лексика, ≥10/≥10 тестів) | 0.5 | Виконано |
| CORE-02 | Парсер та типізоване AST з `SourceSpan` | 1.5 | Виконано |
| CORE-03 | Інтерпретатор SIPL (ліміт кроків, ≥80% покриття) | 2.0 | Виконано |
| CORE-04 | Подієва модель виконання та `trace` | 1.0 | Виконано |
| CORE-05 | CLI (`parse`, `check`, `run`, `trace`) + JSON-режим | 1.0 | Виконано |
| VIS-01 | Візуалізація дерева синтаксичного виводу (`Text`, `JSON`, `DOT/SVG`) | 1.5 | Виконано |
| VIS-02 | Візуалізація AST та порівняння `Parse Tree ↔ AST` (`SVG/HTML`) | 1.0 | Виконано |
| REL-01 | CI (GitHub Actions: lint, type-check, tests, build) | 0.5 | Виконано |
| REL-02 | GitHub Releases + SemVer + `CHANGELOG.md` | 0.5 | Виконано |
| REL-03 | Публікація Python-пакета в PyPI | 0.5 | Виконано |


## Встановлення

### З PyPI (у чистому середовищі)

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install sipl-toolkit-zekorfk