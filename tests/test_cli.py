"""
CLI 集成测试。
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from pii_stripper_middleware.cli import app

runner = CliRunner()


class TestDemoCommand:
    def test_demo_runs_successfully(self):
        result = runner.invoke(app, ["demo"])
        assert result.exit_code == 0
        # 应包含脱敏后的结果
        assert "PHONE" in result.output or "EMAIL" in result.output or "演示" in result.output

    def test_demo_output_contains_panel(self):
        result = runner.invoke(app, ["demo"])
        assert result.exit_code == 0
        assert "脱敏" in result.output or "原始" in result.output


class TestStripCommand:
    def test_strip_phone_number(self):
        result = runner.invoke(app, ["strip", "联系 13812345678", "--no-nlp"])
        assert result.exit_code == 0
        assert "13812345678" not in result.output
        assert "PHONE" in result.output

    def test_strip_email(self):
        result = runner.invoke(app, ["strip", "邮件 hello@world.org", "--no-nlp"])
        assert result.exit_code == 0
        assert "hello@world.org" not in result.output

    def test_strip_no_input_exits_with_error(self):
        result = runner.invoke(app, ["strip"])
        assert result.exit_code != 0

    def test_strip_file_not_exist(self, tmp_path):
        result = runner.invoke(app, ["strip", "--file", str(tmp_path / "nonexistent.txt")])
        assert result.exit_code != 0

    def test_strip_file_input(self, tmp_path):
        input_file = tmp_path / "input.txt"
        input_file.write_text("电话 13812345678", encoding="utf-8")
        result = runner.invoke(app, ["strip", "--file", str(input_file), "--no-nlp"])
        assert result.exit_code == 0
        assert "PHONE" in result.output

    def test_strip_output_file(self, tmp_path):
        output_file = tmp_path / "output.txt"
        result = runner.invoke(
            app,
            ["strip", "电话 13812345678", "--no-nlp", "--output", str(output_file)],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "13812345678" not in content


class TestChatCommand:
    def test_chat_no_input_no_interactive_exits_with_error(self):
        result = runner.invoke(app, ["chat", "--api-key", "sk-test"])
        assert result.exit_code != 0

    def test_chat_no_api_key_exits_with_error(self):
        import os
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = runner.invoke(app, ["chat", "hello"])
            assert result.exit_code != 0

    def test_chat_single_message(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "收到您的 <PHONE_1> 信息。"
        mock_client.chat.completions.create.return_value = mock_response

        with patch("pii_stripper_middleware.cli.get_openai_client", return_value=mock_client):
            result = runner.invoke(
                app,
                ["chat", "联系 13812345678", "--no-nlp", "--api-key", "sk-test"],
            )
        assert result.exit_code == 0
        # AI 回复中的占位符应被还原
        assert "13812345678" in result.output
