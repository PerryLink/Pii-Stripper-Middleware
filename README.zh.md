<div align="center">

# Pii-Stripper-Middleware

**在发送文本给 LLM 之前自动脱敏个人隐私信息，收到回复后自动还原。**

*已移植至 [dsh-mask](https://github.com/PerryLink/dsh-mask) —— 属于 PerryLink DSH 插件家族。*

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

[English](README.md) · [简体中文](README.zh.md)

</div>

---

## 功能简介

Pii-Stripper-Middleware 位于你的应用与 LLM 之间。发送请求前，它会将个人隐私信息——手机号、身份证号、邮箱、姓名等——替换为可逆占位符（如 `<PHONE_1>`）。模型只能看到脱敏后的文本；收到回复后，占位符会被还原为原始值。

**你的客户数据从未离开本地。**

## 核心特性

- **正则检测** —— 中国大陆手机号、18 位身份证号、邮箱地址、IPv4 地址
- **NLP 识别** —— 集成 Microsoft Presidio + SpaCy，识别人名、地名、组织机构、信用卡等
- **无损还原** —— 相同原始值始终复用同一占位符，结果 100% 可逆
- **多轮对话** —— 交互式 REPL 中对话历史始终以脱敏形式存储
- **代理友好** —— 支持自定义 API Base URL，适配任意 OpenAI 兼容端点
- **Python API** —— 两行代码即可集成

## 快速开始

```bash
pip install pii-stripper-middleware

# 可选：NLP 实体识别
pip install "pii-stripper-middleware[nlp]"
python -m spacy download zh_core_web_sm   # 或 en_core_web_sm
```

## 使用指南

### 命令行

```bash
# 本地演示，无需 API Key
pii-stripper demo

# 仅脱敏文本
pii-stripper strip "联系张三，手机 13812345678，邮箱 zs@example.com"

# 脱敏后发送给模型，再还原回复（需要 OPENAI_API_KEY）
pii-stripper chat "帮我给张三（13812345678）写一封感谢信"

# 交互式多轮对话
pii-stripper chat --interactive

# 显示脱敏详情
pii-stripper chat "..." --verbose

# 处理文件
pii-stripper strip --file customer_data.txt --output cleaned.txt
```

`chat` 命令支持 `--api-key`、`--base-url`、`--model`（默认 `gpt-4o-mini`）、`--no-nlp` 和 `--env-file`。

### Python API

```python
from pii_stripper_middleware import PIIStripper

stripper = PIIStripper()  # 自动检测 SpaCy，失败则降级为正则模式

anonymized = stripper.strip("客户张三的手机是 13812345678")
print(anonymized)          # "客户 <PERSON_1> 的手机是 <PHONE_1>"
print(stripper.mapping)    # {"<PERSON_1>": "张三", "<PHONE_1>": "13812345678"}

restored = stripper.restore(anonymized)
print(restored)            # "客户张三的手机是 13812345678"
```

## 开发

```bash
poetry install
poetry run pytest
poetry run ruff check .
```

## 许可证

[Apache License 2.0](LICENSE) © 2026 PerryLink
