# Developer Documentation

This folder contains guides and information **for developers only**. 
The main documentation for users and contributors is in `/docs/`.

## Contents

- **[SETUP.md](./SETUP.md)** - Local development environment setup
- **[SECRETS.md](./SECRETS.md)** - Managing secrets and API keys
- **[WORKFLOW-ISSUES.md](./WORKFLOW-ISSUES.md)** - CI/CD troubleshooting
- **[NOTES.md](./NOTES.md)** - Personal dev notes and TODOs

## Quick Start for Developers

```bash
cp .env.example .env
# Edit .env with your credentials
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```

See [SETUP.md](./SETUP.md) for detailed instructions.
