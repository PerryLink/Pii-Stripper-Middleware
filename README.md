<div align="center">

# Pii-Stripper-Middleware

**Automatically anonymize PII before sending text to an LLM, then restore it after the reply.**

*Ported into [dsh-mask](https://github.com/PerryLink/dsh-mask) — part of the PerryLink DSH Plugin Family.*

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

[English](README.md) · [简体中文](README.zh.md)

</div>

---

## What it does

Pii-Stripper-Middleware sits between your application and the LLM. Before a request is sent, it replaces personally identifiable information — phone numbers, national IDs, emails, names, and more — with reversible placeholders such as `<PHONE_1>`. The model only ever sees anonymized text; after the reply, the placeholders are restored to their original values.

**Your customer data never leaves your machine.**

## Features

- **Regex detection** — Chinese mobile numbers, 18-digit national IDs, email addresses, and IPv4 addresses
- **NLP recognition** — Microsoft Presidio + SpaCy for names, locations, organizations, credit cards, and more
- **Lossless restoration** — identical values always reuse the same placeholder, so results are 100% reversible
- **Multi-turn chat** — interactive REPL keeps conversation history anonymized
- **Proxy-friendly** — custom API base URL for any OpenAI-compatible endpoint
- **Python API** — integrate in two lines

## Quick start

```bash
pip install pii-stripper-middleware

# Optional NLP entity recognition
pip install "pii-stripper-middleware[nlp]"
python -m spacy download zh_core_web_sm   # or en_core_web_sm
```

## Usage

### CLI

```bash
# Local demo, no API key needed
pii-stripper demo

# Strip PII from text
pii-stripper strip "Contact John Doe at john@example.com, phone 13812345678"

# Strip, send to the model, then restore the reply (requires OPENAI_API_KEY)
pii-stripper chat "Write a thank-you letter to John Doe (13812345678)"

# Interactive multi-turn conversation
pii-stripper chat --interactive

# Show anonymization details
pii-stripper chat "..." --verbose

# Process a file
pii-stripper strip --file customer_data.txt --output cleaned.txt
```

The `chat` command accepts `--api-key`, `--base-url`, `--model` (default `gpt-4o-mini`), `--no-nlp`, and `--env-file`.

### Python API

```python
from pii_stripper_middleware import PIIStripper

stripper = PIIStripper()  # auto-detects SpaCy, falls back to regex

anonymized = stripper.strip("Client John's phone is 13812345678")
print(anonymized)          # "Client <PERSON_1>'s phone is <PHONE_1>"
print(stripper.mapping)    # {"<PERSON_1>": "John", "<PHONE_1>": "13812345678"}

restored = stripper.restore(anonymized)
print(restored)            # "Client John's phone is 13812345678"
```

## Development

```bash
poetry install
poetry run pytest
poetry run ruff check .
```

## License

[Apache License 2.0](LICENSE) © 2026 PerryLink
