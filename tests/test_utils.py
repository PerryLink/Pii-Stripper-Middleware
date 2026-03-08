"""
工具函数测试。
"""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestGetOpenAIClient:
    def test_raises_without_api_key(self):
        from pii_stripper_middleware.utils import get_openai_client

        with patch.dict(os.environ, {}, clear=True):
            # 确保环境变量中没有 OPENAI_API_KEY
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(ValueError, match="API 密钥"):
                get_openai_client()

    def test_uses_env_api_key(self):
        from pii_stripper_middleware.utils import get_openai_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            with patch("pii_stripper_middleware.utils.OpenAI") as mock_openai:
                mock_openai.return_value = MagicMock()
                client = get_openai_client()
                mock_openai.assert_called_once_with(api_key="sk-test-key")

    def test_uses_arg_api_key(self):
        from pii_stripper_middleware.utils import get_openai_client

        with patch("pii_stripper_middleware.utils.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            get_openai_client(api_key="sk-arg-key")
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs["api_key"] == "sk-arg-key"

    def test_uses_base_url(self):
        from pii_stripper_middleware.utils import get_openai_client

        with patch("pii_stripper_middleware.utils.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            get_openai_client(api_key="sk-key", base_url="https://proxy.example.com/v1")
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs["base_url"] == "https://proxy.example.com/v1"

    def test_arg_key_overrides_env(self):
        from pii_stripper_middleware.utils import get_openai_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key"}):
            with patch("pii_stripper_middleware.utils.OpenAI") as mock_openai:
                mock_openai.return_value = MagicMock()
                get_openai_client(api_key="sk-override-key")
                call_kwargs = mock_openai.call_args[1]
                assert call_kwargs["api_key"] == "sk-override-key"


class TestChatCompletion:
    def test_basic_call(self):
        from pii_stripper_middleware.utils import chat_completion

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Hello!"
        mock_client.chat.completions.create.return_value = mock_response

        result = chat_completion(mock_client, "Hi", model="gpt-4o-mini")
        assert result == "Hello!"

    def test_system_prompt_included(self):
        from pii_stripper_middleware.utils import chat_completion

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"
        mock_client.chat.completions.create.return_value = mock_response

        chat_completion(mock_client, "msg", system_prompt="You are helpful.")
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert messages[0] == {"role": "system", "content": "You are helpful."}

    def test_history_included(self):
        from pii_stripper_middleware.utils import chat_completion

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"
        mock_client.chat.completions.create.return_value = mock_response

        history = [
            {"role": "user", "content": "prev question"},
            {"role": "assistant", "content": "prev answer"},
        ]
        chat_completion(mock_client, "new question", history=history)
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert {"role": "user", "content": "prev question"} in messages
