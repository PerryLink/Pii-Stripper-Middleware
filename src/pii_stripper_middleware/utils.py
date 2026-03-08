"""
工具函数模块：环境变量加载、OpenAI 客户端创建、对话封装。
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_env(env_file: Optional[Path] = None) -> None:
    """
    加载 .env 文件中的环境变量。

    Args:
        env_file: 指定 .env 文件路径；若为 None，自动在当前目录及父目录中查找。
    """
    try:
        from dotenv import load_dotenv
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
    except ImportError:
        logger.debug("python-dotenv 未安装，跳过 .env 加载。")


def get_openai_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
):
    """
    创建并返回 OpenAI 客户端实例。

    API Key 查找顺序：
    1. 函数参数 `api_key`
    2. 环境变量 `OPENAI_API_KEY`

    Base URL 查找顺序：
    1. 函数参数 `base_url`
    2. 环境变量 `OPENAI_BASE_URL`（适用于代理或兼容端点）

    Raises:
        ValueError: 未能找到有效的 API Key。
        ImportError: openai 库未安装。
    """
    from openai import OpenAI

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "未找到 OpenAI API 密钥。请通过以下任一方式提供：\n"
            "  1. CLI 参数：--api-key YOUR_KEY\n"
            "  2. 环境变量：export OPENAI_API_KEY=YOUR_KEY\n"
            "  3. 项目根目录 .env 文件：OPENAI_API_KEY=YOUR_KEY"
        )

    url = base_url or os.getenv("OPENAI_BASE_URL")

    kwargs: dict = {"api_key": key}
    if url:
        kwargs["base_url"] = url

    return OpenAI(**kwargs)


def chat_completion(
    client,
    message: str,
    model: str = "gpt-4o-mini",
    system_prompt: Optional[str] = None,
    history: Optional[list[dict]] = None,
) -> str:
    """
    向 OpenAI Chat Completions API 发送请求。

    Args:
        client: OpenAI 客户端实例。
        message: 当前用户消息。
        model: 使用的模型名称。
        system_prompt: 系统提示词（可选）。
        history: 历史对话列表，格式为 [{"role": ..., "content": ...}, ...]。

    Returns:
        AI 回复的文本内容。
    """
    messages: list[dict] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content
