<div align="center">

# Pii-Stripper-Middleware

**在发送文本给 LLM 之前自动脱敏个人隐私信息，收到回复后自动还原。**

*已移植至 [dsh-mask](https://github.com/PerryLink/dsh-mask) —— 属于 PerryLink DSH 插件家族。*

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

[English](README.md) · [简体中文](README.zh.md)

</div>

---

## 功能简介

Pii-Stripper-Middleware 位于你的应用与 LLM 之间。发送请求前，它会将个人隐私信息替换为可逆占位符；模型只能看到脱敏后的文本，收到回复后占位符会被还原。

```
你输入的原始文本：
  "帮我起草一封道歉邮件给客户张三，他的手机是 13812345678"

↓ 自动脱敏（真正发给模型的内容）

  "帮我起草一封道歉邮件给客户 <PERSON_1>，他的手机是 <PHONE_1>"

↓ 模型返回（含占位符）

  "尊敬的 <PERSON_1>，感谢您一直以来的支持……如有疑问请拨打 <PHONE_1>"

↓ 自动还原（你看到的最终回复）

  "尊敬的 张三，感谢您一直以来的支持……如有疑问请拨打 13812345678"
```

**你的客户数据从未离开本地。**

## 核心特性

- **正则检测** —— 中国大陆手机号、18 位身份证、邮箱、IPv4 地址
- **NLP 识别** —— 集成 Microsoft Presidio + SpaCy，识别人名、地名、组织机构、信用卡等
- **无损还原** —— 相同原始值始终复用同一占位符，100% 可逆
- **多轮对话** —— 内置交互式 REPL，历史上下文自动脱敏存储
- **代理友好** —— 支持自定义 API Base URL，适配各类 OpenAI 兼容代理
- **Python API** —— 两行代码集成进任意 Python 项目

## 快速开始

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

### 配置 API Key（三种方式）

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

### 与 OpenAI 集成

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

## CLI 参考

```
命令：
  strip   仅脱敏文本（不调用 AI）
  chat    脱敏后与 OpenAI 对话
  demo    本地演示，无需 API Key

strip 选项：
  TEXT                   要处理的文本
  --file, -f PATH        输入文件路径
  --output, -o PATH      输出文件路径
  --show-mapping         显示替换映射表（默认开启）
  --no-nlp               禁用 NLP，仅使用正则
  --env-file PATH        .env 文件路径

chat 选项：
  TEXT                   发送给 AI 的文本
  --model, -m TEXT       模型名称（默认 gpt-4o-mini）
  --interactive, -i      交互式对话模式
  --api-key TEXT         OpenAI API Key
  --base-url TEXT        API Base URL（代理 / 兼容端点）
  --no-nlp               禁用 NLP
  --verbose, -v          显示脱敏详情
  --env-file PATH        .env 文件路径
```

## 技术栈

| 组件 | 库 |
|------|----|
| CLI 框架 | [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) |
| NLP / 实体识别 | [Microsoft Presidio](https://microsoft.github.io/presidio/) + [SpaCy](https://spacy.io/) |
| LLM 集成 | [OpenAI Python SDK](https://github.com/openai/openai-python) |
| 打包工具 | [Poetry](https://python-poetry.org/) |
| 测试框架 | [pytest](https://pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/) |
| 代码检查 | [Ruff](https://docs.astral.sh/ruff/) |

## 隐私声明

- **数据不落盘** —— 原始 PII 仅在内存中保存，随进程结束释放。
- **发给 AI 的内容** —— 只包含占位符，真实敏感信息从不离开本地。
- **历史对话** —— 交互模式下，历史记录中存储的也是脱敏后的文本。

## 开发

```bash
poetry install
poetry run pytest
poetry run ruff check .
```

## 相关项目

- [dsh-mask](https://github.com/PerryLink/dsh-mask) —— 本项目被移植进的 DSH 插件
- [PerryLink](https://github.com/PerryLink) —— PerryLink DSH 插件家族

## 许可证

[Apache License 2.0](LICENSE) © 2026 PerryLink
