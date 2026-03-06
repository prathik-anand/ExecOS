# Developer Setup — Linting & Formatting

This project enforces consistent code style automatically on save. Follow the steps below once per machine.

---

## 1. Install VS Code Extensions

Install these extensions:

| Extension ID | Purpose |
|---|---|
| `charliermarsh.ruff` | Python linting + formatting |
| `esbenp.prettier-vscode` | TypeScript / JS / JSON / CSS formatting |
| `dbaeumer.vscode-eslint` | TypeScript / React linting |
| `ms-python.python` | Python language support |

Install via Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`):

```
ext install charliermarsh.ruff esbenp.prettier-vscode dbaeumer.vscode-eslint ms-python.python
```

---

## 2. Configure VS Code User Settings

Open Command Palette → **Preferences: Open User Settings (JSON)** and add:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.eslint": "explicit",
      "source.organizeImports": "never"
    }
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.eslint": "explicit"
    }
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[json]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[css]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "eslint.workingDirectories": ["./frontend"],
  "eslint.validate": ["javascript", "typescript", "typescriptreact"],
  "editor.rulers": [100]
}
```

After this, every file save automatically formats and fixes lint issues — no manual commands needed.

---

## 3. Install Project Dependencies

### Python (Backend)

```bash
cd backend
uv sync
```

### Node (Frontend)

```bash
cd frontend
npm install
```

---

## What Gets Enforced

### Backend (Python)

Config lives in `backend/pyproject.toml` under `[tool.ruff]`.

| Rule set | What it catches |
|---|---|
| `E` / `W` | PEP 8 style errors and warnings |
| `F` | Undefined names, unused imports |
| `I` | Import order (isort) |
| `B` | Common bug patterns |
| `UP` | Outdated Python syntax |
| `N` | Naming conventions |
| `S` | Security issues (bandit) |
| `SIM` | Simplifiable code |
| `C90` | Function complexity |
| `T20` | No `print()` statements |
| `PL` | Pylint rules |

Formatter: Black-compatible (double quotes, 100 char line length, trailing commas).

### Frontend (TypeScript / React)

Config lives in `frontend/eslint.config.js` (ESLint 9 flat config) and `frontend/.prettierrc`.

| Tool | What it catches |
|---|---|
| `@typescript-eslint` (type-aware) | Type errors, unsafe patterns, unused vars |
| `eslint-plugin-react` | React best practices, JSX correctness |
| `eslint-plugin-react-hooks` | Hooks rules (deps arrays, call order) |
| `eslint-plugin-jsx-a11y` | Accessibility issues |
| `eslint-plugin-import-x` | Import order, no cycles, no duplicates |
| Prettier | Consistent formatting (100 char line, double quotes, semicolons) |

---

## Run on All Files at Once

### Backend

```bash
cd backend
source .venv/bin/activate

# Format + lint fix
ruff format . && ruff check --fix .

# Check only (no changes)
ruff check .
ruff format --check .
```

### Frontend

```bash
cd frontend

# Format all files
npm run format

# Lint + auto-fix
npm run lint:fix

# Check only (no changes)
npm run format:check
npm run lint

# Type check
npm run typecheck
```

---

## Other IDEs

### PyCharm / WebStorm

**Ruff (Python):**
- Install the [Ruff plugin](https://plugins.jetbrains.com/plugin/20574-ruff)
- Settings → Tools → Ruff → enable "Run on save"
- Config is auto-read from `backend/pyproject.toml`

**Prettier (Frontend):**
- Settings → Languages & Frameworks → JavaScript → Prettier
- Set path to `frontend/node_modules/.bin/prettier`
- Enable "On save"

**ESLint (Frontend):**
- Settings → Languages & Frameworks → JavaScript → Code Quality Tools → ESLint
- Select "Automatic ESLint configuration"

---

## Global Ruff Config (Optional)

If you work on multiple Python projects and want ruff to apply everywhere without per-project config, create `~/.config/ruff/ruff.toml`. See [ruff-setup.md](ruff-setup.md) for the full config.

This project's `pyproject.toml` takes precedence over the global config when inside the repo.
