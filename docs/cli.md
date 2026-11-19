# SIPL CLI та JSON-контракт

Після встановлення пакета доступна консольна команда `sipl` (або `python -m sipl.cli`).

## Команди

- `sipl parse <file> [--json]` — розбір програми та вивід типізованого AST.
- `sipl check <file> [--json]` — перевірка синтаксичної коректності файлу.
- `sipl run <file> [--state JSON] [--state-file PATH] [--set NAME=INT ...] [--max-steps N] [--json]` — виконання програми на заданому початковому стані.
- `sipl trace <file> [--state JSON] [--state-file PATH] [--set NAME=INT ...] [--max-steps N] [--json]` — виконання програми зі збором повної подійної траси (`trace`).

Пріоритет задання початкових змінних: `--state-file` $\to$ `--state` $\to$ `--set` (кожен наступний перевизначає попередній).

## Коди завершення (Exit Codes)

| Код | Значення |
|---|---|
| `0` | Успішне виконання |
| `1` | Синтаксична/лексична помилка (`SiplSyntaxError`) |
| `2` | Помилка часу виконання (`UndefinedVariableError`, `StepLimitExceededError`) |
| `3` | Помилка вхідних даних CLI (файл не знайдено, невалідний JSON стану тощо) |

## JSON-схема відповідей (`--json`)

### Успіх (`ok: true`)
- **parse:** `{"ok": true, "command": "parse", "file": "...", "ast": {...}}`
- **check:** `{"ok": true, "command": "check", "file": "...", "valid": true}`
- **run:** `{"ok": true, "command": "run", "file": "...", "steps": N, "final_state": {"Var": 123}}`
- **trace:** `{"ok": true, "command": "trace", "file": "...", "steps": N, "final_state": {...}, "trace": [...]}`

### Помилка (`ok: false`)
```json
{
  "ok": false,
  "command": "run",
  "file": "program.sipl",
  "error": {
    "type": "UndefinedVariableError",
    "message": "Undefined variable 'Y'",
    "span": {
      "file": "program.sipl",
      "start_line": 2,
      "start_col": 10,
      "end_line": 2,
      "end_col": 11
    },
    "step": 1
  }
}