# pii-stripper-middleware

> Automatically anonymize PII before sending to LLMs, seamlessly restore it after.

[![Tests](https://github.com/PerryLink/pii-stripper-middleware/actions/workflows/test.yml/badge.svg)](https://github.com/PerryLink/pii-stripper-middleware/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/pii-stripper-middleware.svg)](https://badge.fury.io/py/pii-stripper-middleware)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

---

## How It Works

```
Original input:
  "Draft an apology email to client John Doe, his phone is +1-800-555-0100"

↓ Auto-anonymized (what actually gets sent to OpenAI)

  "Draft an apology email to client <PERSON_1>, his phone is <PHONE_1>"

↓ OpenAI responds (with placeholders)

  "Dear <PERSON_1>, thank you for your patience... please call <PHONE_1>"

↓ Auto-restored (what you actually see)

  "Dear John Doe, thank you for your patience... please call +1-800-555-0100"
```

**Your customer data never leaves your machine.**

---

## Features

- **Regex detection** — Chinese mobile numbers, 18-digit national IDs, email addresses, IPv4
- **NLP recognition** — Microsoft Presidio + SpaCy for names, locations, organizations, credit cards, and more
- **Lossless restoration** — identical values always reuse the same placeholder, 100% reversible
- **Multi-turn chat** — built-in interactive REPL; conversation history is always stored anonymized
- **Proxy-friendly** — supports custom API base URL for any OpenAI-compatible endpoint
- **Python API** — integrate into any Python project in two lines

---

## Installation

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

---

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

**Configure API Key (three ways)**

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

**Integrated with OpenAI**

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

---

## Supported PII Types

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

---

## CLI Reference

```
pii-stripper --help

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

---

## Project Structure

```
pii-stripper-middleware/
├── .github/
│   └── workflows/
│       ├── test.yml          # CI: multi-platform × multi-Python tests
│       └── publish.yml       # CD: publish to PyPI
├── src/
│   └── pii_stripper_middleware/
│       ├── __init__.py       # Public API: PIIStripper
│       ├── __main__.py       # python -m pii_stripper_middleware
│       ├── cli.py            # Typer CLI (strip / chat / demo)
│       ├── core.py           # PIIStripper core logic
│       └── utils.py          # OpenAI client, env helpers
├── tests/
│   ├── test_core.py          # Core unit tests
│   ├── test_cli.py           # CLI integration tests
│   └── test_utils.py         # Utility tests
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE                   # Apache 2.0
├── README.md
└── pyproject.toml            # Poetry project config
```

---

## Tech Stack

| Component | Library |
|-----------|---------|
| CLI framework | [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) |
| NLP / entity recognition | [Microsoft Presidio](https://microsoft.github.io/presidio/) + [SpaCy](https://spacy.io/) |
| LLM integration | [OpenAI Python SDK](https://github.com/openai/openai-python) |
| Packaging | [Poetry](https://python-poetry.org/) |
| Testing | [pytest](https://pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/) |
| Linting | [Ruff](https://docs.astral.sh/ruff/) |

---

## Privacy

- **No disk writes** — raw PII is held only in memory and released when the process exits.
- **What AI receives** — only placeholder tokens; real sensitive values never leave your machine.
- **Conversation history** — in interactive mode, history stores anonymized text only.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and how to submit a pull request.

---

## License

[Apache License 2.0](LICENSE) © 2026 Chance Dean (novelnexusai@outlook.com)

---

---

# pii-stripper-middleware（中文文档）

> 自动脱敏中间件——在发送数据给 LLM 前自动替换敏感信息，回复后无缝还原。

---

## 工作原理

```
你输入的原始文本：
  "帮我起草一封道歉邮件给客户张三，他的手机是 13812345678"

↓ 自动脱敏（真正发给 OpenAI 的内容）

  "帮我起草一封道歉邮件给客户 <PERSON_1>，他的手机是 <PHONE_1>"

↓ OpenAI 返回（含占位符）

  "尊敬的 <PERSON_1>，感谢您一直以来的支持……如有疑问请拨打 <PHONE_1>"

↓ 自动还原（你看到的最终回复）

  "尊敬的 张三，感谢您一直以来的支持……如有疑问请拨打 13812345678"
```

**你的客户数据从未离开本地。**

---

## 核心特性

- **正则检测** — 中国大陆手机号、18 位身份证、邮箱、IPv4 地址
- **NLP 识别** — 集成 Microsoft Presidio + SpaCy，识别人名、地名、组织机构等
- **无损还原** — 相同原始值始终复用同一占位符，AI 回复后 100% 还原
- **多轮对话** — 内置交互式 REPL，历史上下文自动脱敏存储
- **代理友好** — 支持自定义 API Base URL，适配各类 OpenAI 兼容代理
- **Python API** — 两行代码集成进任意 Python 项目

---

## 安装

**基础安装（正则模式，无需 SpaCy）**

```bash
pip install pii-stripper-middleware
```

**完整安装（含 NLP 实体识别）**

```bash
pip install "pii-stripper-middleware[nlp]"

# 下载中文 SpaCy 模型（推荐）
python -m spacy download zh_core_web_sm

# 或英文模型
python -m spacy download en_core_web_sm
```

**使用 Poetry**

```bash
poetry add pii-stripper-middleware
# 含 NLP 支持
poetry add "pii-stripper-middleware[nlp]"
```

---

## 使用指南

### 命令行

```bash
# 本地演示（无需 API Key）
pii-stripper demo

# 仅脱敏文本，查看效果
pii-stripper strip "联系张三，手机 13812345678，邮箱 zs@example.com"

# 脱敏后发给 AI（需要 OPENAI_API_KEY）
export OPENAI_API_KEY=sk-...
pii-stripper chat "帮我给客户张三（13812345678）写一封感谢信"

# 交互式多轮对话
pii-stripper chat --interactive

# 显示脱敏详情
pii-stripper chat "..." --verbose

# 处理文件
pii-stripper strip --file customer_data.txt --output cleaned.txt
```

**配置 API Key（三种方式）**

```bash
# 方式 1：环境变量
export OPENAI_API_KEY=sk-your-key

# 方式 2：.env 文件（项目根目录）
echo "OPENAI_API_KEY=sk-your-key" > .env

# 方式 3：命令行参数
pii-stripper chat "..." --api-key sk-your-key

# 使用自定义代理（兼容 OpenAI API 的任意端点）
pii-stripper chat "..." --base-url https://your-proxy.com/v1
```

### Python API

```python
from pii_stripper_middleware import PIIStripper

stripper = PIIStripper()  # 自动检测 SpaCy 模型，失败降级为正则模式

# 脱敏
original = "客户张三的手机是 13812345678，身份证 110101199001011234"
anonymized = stripper.strip(original)
print(anonymized)
# → "客户 <PERSON_1> 的手机是 <PHONE_1>，身份证 <ID_CARD_1>"

# 查看映射表
print(stripper.mapping)
# → {"<PERSON_1>": "张三", "<PHONE_1>": "13812345678", "<ID_CARD_1>": "110101199001011234"}

# 还原
restored = stripper.restore(anonymized)
print(restored)
# → "客户张三的手机是 13812345678，身份证 110101199001011234"
```

**与 OpenAI 集成**

```python
from openai import OpenAI
from pii_stripper_middleware import PIIStripper

client = OpenAI(api_key="sk-...")
stripper = PIIStripper()

user_message = "帮我给客户张三（13812345678）写一封道歉信"

def call_ai(text):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": text}],
    )
    return resp.choices[0].message.content

# 一步完成：脱敏 → 调用 AI → 还原
result = stripper.strip_and_call(user_message, call_ai)
print(result)  # AI 回复，张三和手机号已自动还原
```

---

## 支持的 PII 类型

| 类型 | 占位符 | 检测方式 | 示例 |
|------|--------|----------|------|
| 中国手机号 | `<PHONE_N>` | 正则 | `13812345678` |
| 中国身份证 | `<ID_CARD_N>` | 正则 | `110101199001011234` |
| 电子邮件 | `<EMAIL_N>` | 正则 | `user@example.com` |
| IPv4 地址 | `<IP_N>` | 正则 | `192.168.1.1` |
| 人名 | `<PERSON_N>` | NLP* | `张三`, `John Doe` |
| 地名 | `<LOCATION_N>` | NLP* | `北京`, `Shanghai` |
| 组织机构 | `<ORG_N>` | NLP* | `腾讯`, `OpenAI` |
| 信用卡号 | `<CREDIT_CARD_N>` | NLP* | `4111 1111 1111 1111` |
| 银行卡号 | `<BANK_CARD_N>` | NLP* | `6222 0000 0000 0000` |

> *NLP 类型需要安装 `[nlp]` 额外依赖和 SpaCy 模型。

---

## 项目结构

```
pii-stripper-middleware/
├── .github/
│   └── workflows/
│       ├── test.yml          # CI：多平台 × 多 Python 版本测试
│       └── publish.yml       # CD：发布到 PyPI
├── src/
│   └── pii_stripper_middleware/
│       ├── __init__.py       # 公开 API：PIIStripper
│       ├── __main__.py       # python -m pii_stripper_middleware
│       ├── cli.py            # Typer CLI（strip / chat / demo）
│       ├── core.py           # PIIStripper 核心逻辑
│       └── utils.py          # OpenAI 客户端、环境变量工具
├── tests/
│   ├── test_core.py          # 核心功能单元测试
│   ├── test_cli.py           # CLI 集成测试
│   └── test_utils.py         # 工具函数测试
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE                   # Apache 2.0
├── README.md
└── pyproject.toml            # Poetry 项目配置
```

---

## 技术栈

| 组件 | 库 |
|------|----|
| CLI 框架 | [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) |
| NLP / 实体识别 | [Microsoft Presidio](https://microsoft.github.io/presidio/) + [SpaCy](https://spacy.io/) |
| LLM 集成 | [OpenAI Python SDK](https://github.com/openai/openai-python) |
| 打包工具 | [Poetry](https://python-poetry.org/) |
| 测试框架 | [pytest](https://pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/) |
| 代码检查 | [Ruff](https://docs.astral.sh/ruff/) |

---

## 隐私声明

- **数据不落盘**：原始 PII 仅在内存中保存，随进程结束释放。
- **发给 AI 的内容**：只包含占位符，真实敏感信息从不离开本地。
- **历史对话**：交互模式下，历史记录中存储的也是脱敏后的文本。

---

## 贡献

请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发环境搭建、代码规范和提交 Pull Request 的流程。

---

## 许可证

[Apache License 2.0](LICENSE) © 2026 Chance Dean (novelnexusai@outlook.com)
