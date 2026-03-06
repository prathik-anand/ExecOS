# Ruff Setup (Global — All Python Projects)

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting across all Python projects.
The config lives at the **user level** (`~/.config/ruff/ruff.toml`), so it applies automatically
to every project without needing a per-workspace config file.

---

## 1. Install Ruff

```bash
# Using pip
pip install ruff

# Using uv (preferred)
uv tool install ruff

# macOS with Homebrew
brew install ruff
```

Verify:

```bash
ruff --version
```

---

## 2. Create the Global Config

Create the directory and config file:

```bash
mkdir -p ~/.config/ruff
```

Then create `~/.config/ruff/ruff.toml` with the following content:

```toml
# Global Ruff config — applies to all projects unless overridden locally

line-length = 100
indent-width = 4
target-version = "py312"

[lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
    "N",    # pep8-naming
    "RUF",  # ruff-specific rules
    "S",    # flake8-bandit (security)
    "C90",  # McCabe complexity
    "T20",  # flake8-print (no print statements)
    "PTH",  # flake8-use-pathlib
    "ERA",  # eradicate (no commented-out code)
    "PL",   # Pylint
    "SIM",  # flake8-simplify
    "TRY",  # tryceratops (exception handling)
    "PERF", # perflint (performance)
]
ignore = [
    "E501",    # line too long (handled by formatter)
    "B008",    # do not perform function calls in default args (common in FastAPI)
    "S101",    # use of assert (needed in tests)
    "TRY003",  # avoid long messages in raise — often too strict
    "PLR0913", # too many arguments — common in FastAPI/service layers
    "PLR2004", # magic value comparison — too noisy
    "ERA001",  # commented-out code — allow during development
]

[lint.per-file-ignores]
"tests/**/*.py" = [
    "S",    # security rules too strict for tests
    "T20",  # allow print in tests
    "ANN",  # skip annotations in tests
]
"**/migrations/**/*.py" = [
    "E501", # long lines OK in Alembic migrations
    "N",    # naming conventions relaxed in migrations
]

[lint.isort]
known-first-party = ["app"]

[lint.mccabe]
max-complexity = 10

[lint.pylint]
max-args = 8
max-branches = 12

[format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

---

## 3. IDE Integration

### VS Code

Install the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff)
(`charliermarsh.ruff`), then add to your `settings.json`:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  }
}
```

The extension automatically picks up `~/.config/ruff/ruff.toml` — no extra config needed.

### PyCharm

Go to **Settings → Tools → External Tools** and add:

| Field   | Value                          |
|---------|-------------------------------|
| Program | `ruff`                         |
| Args    | `check --fix $FilePath$`       |
| Working | `$ProjectFileDir$`             |

For formatting, add a second tool with args: `format $FilePath$`

### Neovim (via `null-ls` or `conform.nvim`)

```lua
-- conform.nvim example
require("conform").setup({
  formatters_by_ft = {
    python = { "ruff_format" },
  },
})
```

---

## 4. CLI Usage

```bash
# Lint
ruff check .

# Lint and auto-fix
ruff check --fix .

# Format (Black-compatible)
ruff format .

# Check formatting without writing
ruff format --check .

# Lint a single file
ruff check path/to/file.py
```

---

## 5. How Config Resolution Works

Ruff looks for config in this order:

1. `ruff.toml` / `.ruff.toml` / `pyproject.toml` — walks up from the file being linted
2. Falls back to `~/.config/ruff/ruff.toml` if nothing found in the project tree

This means:
- **No project config** → global config applies automatically
- **Project has its own config** → project config wins (useful for overrides)
- Works the same whether triggered from CLI, VS Code, PyCharm, or any other tool

---

## 6. Formatter vs Black

The formatter (`ruff format`) is a Black-compatible drop-in replacement.
It produces identical output to Black with `line-length = 100`, `--skip-magic-trailing-comma` off.
No need to install or configure Black separately.
