<div align="center">

# Pii-Stripper-Middleware

**Automatically anonymize PII before sending text to an LLM, then restore it after the reply.**

*Ported into [dsh-mask](https://github.com/PerryLink/dsh-mask) — part of the PerryLink DSH Plugin Family.*

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

[English](README.md) · [简体中文](README.zh.md)

</div>

---

## What it does

Pii-Stripper-Middleware sits between your application and the LLM. Before a request is sent, it replaces personally identifiable information with reversible placeholders; the model only ever sees anonymized text, and the placeholders are restored after the reply.

```
Original input:
  "Draft an apology email to client John Doe, his phone is +1-800-555-0100"

↓ Auto-anonymized (what actually gets sent to the model)

  "Draft an apology email to client <PERSON_1>, his phone is <PHONE_1>"

↓ Model responds (with placeholders)

  "Dear <PERSON_1>, thank you for your patience... please call <PHONE_1>"

↓ Auto-restored (what you actually see)

  "Dear John Doe, thank you for your patience... please call +1-800-555-0100"
```

**Your customer data never leaves your machine.**

## Features

- **Regex detection** — Chinese mobile numbers, 18-digit national IDs, email addresses, IPv4 addresses
- **NLP recognition** — Microsoft Presidio + SpaCy for names, locations, organizations, credit cards, and more
- **Lossless restoration** — identical values always reuse the same placeholder, 100% reversible
- **Multi-turn chat** — built-in interactive REPL; conversation history is always stored anonymized
- **Proxy-friendly** — supports a custom API base URL for any OpenAI-compatible endpoint
- **Python API** — integrate into any Python project in two lines

## Quick start

**Basic (regex mode, no SpaCy required)**

```bash
pip install pii-stripper-middleware
```

**Full (with NLP entity recognition)**

```bash
pip install "pii-stripper-middleware[nlp]"

# Download Chinese SpaCy model (recommended)
python -m spacy download zh_core_web_sm

# Or English model
python -m spacy download en_core_web_sm
```

**Using Poetry**

```bash
poetry add pii-stripper-middleware
# With NLP support
poetry add "pii-stripper-middleware[nlp]"
```

## Usage

### CLI

```bash
# Local demo — no API key needed
pii-stripper demo

# Strip PII from text and inspect the result
pii-stripper strip "Contact John Doe at john@example.com, phone 13812345678"

# Strip then send to AI (requires OPENAI_API_KEY)
export OPENAI_API_KEY=sk-...
pii-stripper chat "Write a thank-you letter to John Doe (13812345678)"

# Interactive multi-turn conversation
pii-stripper chat --interactive

# Show anonymization details
pii-stripper chat "..." --verbose

# Process a file
pii-stripper strip --file customer_data.txt --output cleaned.txt
```

### Configure the API key (three ways)

```bash
# 1. Environment variable
export OPENAI_API_KEY=sk-your-key

# 2. .env file in project root
echo "OPENAI_API_KEY=sk-your-key" > .env

# 3. CLI flag
pii-stripper chat "..." --api-key sk-your-key

# Custom proxy (any OpenAI-compatible endpoint)
pii-stripper chat "..." --base-url https://your-proxy.com/v1
```

### Python API

```python
from pii_stripper_middleware import PIIStripper

stripper = PIIStripper()  # auto-detects SpaCy model; falls back to regex

# Strip
original = "Client John's phone is 13812345678, ID: 110101199001011234"
anonymized = stripper.strip(original)
print(anonymized)
# → "Client <PERSON_1>'s phone is <PHONE_1>, ID: <ID_CARD_1>"

# Inspect the mapping
print(stripper.mapping)
# → {"<PERSON_1>": "John", "<PHONE_1>": "13812345678", "<ID_CARD_1>": "110101199001011234"}

# Restore
restored = stripper.restore(anonymized)
print(restored)
# → "Client John's phone is 13812345678, ID: 110101199001011234"
```

### Integrated with OpenAI

```python
from openai import OpenAI
from pii_stripper_middleware import PIIStripper

client = OpenAI(api_key="sk-...")
stripper = PIIStripper()

user_message = "Write an apology letter to John Doe (13812345678)"

def call_ai(text):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": text}],
    )
    return resp.choices[0].message.content

# One call: strip → AI → restore
result = stripper.strip_and_call(user_message, call_ai)
print(result)  # AI reply with real name and phone number restored
```

## Supported PII types

| Type | Placeholder | Detection | Example |
|------|-------------|-----------|---------|
| Chinese mobile | `<PHONE_N>` | Regex | `13812345678` |
| Chinese national ID | `<ID_CARD_N>` | Regex | `110101199001011234` |
| Email address | `<EMAIL_N>` | Regex | `user@example.com` |
| IPv4 address | `<IP_N>` | Regex | `192.168.1.1` |
| Person name | `<PERSON_N>` | NLP* | `John Doe`, `张三` |
| Location | `<LOCATION_N>` | NLP* | `Beijing`, `上海` |
| Organization | `<ORG_N>` | NLP* | `OpenAI`, `腾讯` |
| Credit card | `<CREDIT_CARD_N>` | NLP* | `4111 1111 1111 1111` |
| Bank card | `<BANK_CARD_N>` | NLP* | `6222 0000 0000 0000` |

> *NLP types require the `[nlp]` extra and a SpaCy model.

## CLI reference

```
Commands:
  strip   Strip PII from text (no AI call)
  chat    Strip PII then chat with OpenAI
  demo    Local demo, no API key needed

strip options:
  TEXT                   Text to process
  --file, -f PATH        Input file path
  --output, -o PATH      Output file path
  --show-mapping         Print replacement mapping (default: on)
  --no-nlp               Disable NLP, use regex only
  --env-file PATH        Path to .env file

chat options:
  TEXT                   Message to send to AI
  --model, -m TEXT       Model name (default: gpt-4o-mini)
  --interactive, -i      Interactive conversation mode
  --api-key TEXT         OpenAI API key
  --base-url TEXT        API base URL (proxy / compatible endpoint)
  --no-nlp               Disable NLP
  --verbose, -v          Show anonymization details
  --env-file PATH        Path to .env file
```

## Tech stack

| Component | Library |
|-----------|---------|
| CLI framework | [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) |
| NLP / entity recognition | [Microsoft Presidio](https://microsoft.github.io/presidio/) + [SpaCy](https://spacy.io/) |
| LLM integration | [OpenAI Python SDK](https://github.com/openai/openai-python) |
| Packaging | [Poetry](https://python-poetry.org/) |
| Testing | [pytest](https://pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/) |
| Linting | [Ruff](https://docs.astral.sh/ruff/) |

## Privacy

- **No disk writes** — raw PII is held only in memory and released when the process exits.
- **What AI receives** — only placeholder tokens; real sensitive values never leave your machine.
- **Conversation history** — in interactive mode, history stores anonymized text only.

## Development

```bash
poetry install
poetry run pytest
poetry run ruff check .
```

## Related

- [dsh-mask](https://github.com/PerryLink/dsh-mask) — the DSH plugin this project was ported into
- [PerryLink](https://github.com/PerryLink) — the PerryLink DSH plugin family

## License

[Apache License 2.0](LICENSE) © 2026 PerryLink
