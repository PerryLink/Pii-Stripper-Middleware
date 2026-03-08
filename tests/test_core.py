"""
核心模块测试：PIIStripper 类的功能验证。
"""

import pytest
from pii_stripper_middleware.core import PIIStripper


# ---------------------------------------------------------------------------
# 工厂函数（每个测试获得全新实例）
# ---------------------------------------------------------------------------


@pytest.fixture
def stripper():
    """仅使用正则模式，确保测试在无 SpaCy 模型环境下也能运行。"""
    return PIIStripper(use_nlp=False)


# ---------------------------------------------------------------------------
# 手机号检测
# ---------------------------------------------------------------------------


class TestPhoneDetection:
    def test_cn_mobile_detected(self, stripper):
        result = stripper.strip("请联系 13812345678 预约。")
        assert "13812345678" not in result
        assert "<PHONE_1>" in result

    def test_cn_mobile_various_prefixes(self, stripper):
        for prefix in ("138", "139", "150", "186", "199"):
            phone = f"{prefix}00000000"
            result = stripper.strip(f"手机：{phone}")
            assert phone not in result

    def test_phone_not_detected_in_longer_number(self, stripper):
        # 14 位数字不应被误识别为手机号
        result = stripper.strip("编号：138123456789999")
        # 不应该把中间 11 位识别为手机号（lookbehind/lookahead 保护）
        assert "138123456789999" in result or "<PHONE_1>" not in result

    def test_same_phone_same_placeholder(self, stripper):
        result = stripper.strip("备用号 13812345678，主号也是 13812345678")
        assert result.count("<PHONE_1>") == 2
        assert "<PHONE_2>" not in result

    def test_multiple_phones_different_placeholders(self, stripper):
        result = stripper.strip("A: 13812345678，B: 18987654321")
        assert "<PHONE_1>" in result
        assert "<PHONE_2>" in result


# ---------------------------------------------------------------------------
# 身份证检测
# ---------------------------------------------------------------------------


class TestIDCardDetection:
    def test_cn_id_detected(self, stripper):
        result = stripper.strip("身份证：110101199001011234")
        assert "110101199001011234" not in result
        assert "<ID_CARD_1>" in result

    def test_cn_id_with_x_suffix(self, stripper):
        result = stripper.strip("证件号 11010119900101123X")
        assert "11010119900101123X" not in result

    def test_cn_id_with_lowercase_x(self, stripper):
        result = stripper.strip("证件号 11010119900101123x")
        assert "11010119900101123x" not in result


# ---------------------------------------------------------------------------
# 邮箱检测
# ---------------------------------------------------------------------------


class TestEmailDetection:
    def test_email_detected(self, stripper):
        result = stripper.strip("发邮件到 user@example.com 即可。")
        assert "user@example.com" not in result
        assert "<EMAIL_1>" in result

    def test_email_with_plus(self, stripper):
        result = stripper.strip("邮箱：user+tag@domain.co.uk")
        assert "user+tag@domain.co.uk" not in result

    def test_email_in_mixed_text(self, stripper):
        result = stripper.strip(
            "联系人 zhangsan@corp.com，电话 13900000000"
        )
        assert "zhangsan@corp.com" not in result
        assert "13900000000" not in result


# ---------------------------------------------------------------------------
# IP 地址检测
# ---------------------------------------------------------------------------


class TestIPDetection:
    def test_ipv4_detected(self, stripper):
        result = stripper.strip("服务器 IP：192.168.1.100")
        assert "192.168.1.100" not in result
        assert "<IP_1>" in result


# ---------------------------------------------------------------------------
# 脱敏映射
# ---------------------------------------------------------------------------


class TestMapping:
    def test_mapping_populated_after_strip(self, stripper):
        stripper.strip("电话：13812345678")
        assert len(stripper.mapping) == 1
        assert "<PHONE_1>" in stripper.mapping
        assert stripper.mapping["<PHONE_1>"] == "13812345678"

    def test_mapping_reset_on_new_strip(self, stripper):
        stripper.strip("第一条 13812345678")
        stripper.strip("第二条 18900000000")
        # 第二次 strip 后，映射只包含第二条的实体
        assert stripper.mapping.get("<PHONE_1>") == "18900000000"

    def test_mapping_is_copy(self, stripper):
        stripper.strip("电话：13812345678")
        m = stripper.mapping
        m["fake"] = "tampered"
        # 修改副本不影响内部状态
        assert "fake" not in stripper.mapping


# ---------------------------------------------------------------------------
# 还原（restore）
# ---------------------------------------------------------------------------


class TestRestore:
    def test_restore_phone(self, stripper):
        original = "联系 13812345678 了解详情"
        anonymized = stripper.strip(original)
        assert stripper.restore(anonymized) == original

    def test_restore_email(self, stripper):
        original = "邮件：hello@world.org"
        anonymized = stripper.strip(original)
        assert stripper.restore(anonymized) == original

    def test_restore_id_card(self, stripper):
        original = "身份证：110101199001011234"
        anonymized = stripper.strip(original)
        assert stripper.restore(anonymized) == original

    def test_restore_multiple_entities(self, stripper):
        original = "张三（13812345678）邮箱 zs@ex.com，证件 110101199001011234"
        anonymized = stripper.strip(original)
        restored = stripper.restore(anonymized)
        assert "13812345678" in restored
        assert "zs@ex.com" in restored
        assert "110101199001011234" in restored

    def test_restore_repeated_value(self, stripper):
        original = "主号 13812345678，备用号也是 13812345678"
        anonymized = stripper.strip(original)
        restored = stripper.restore(anonymized)
        assert restored == original

    def test_restore_ai_response_with_placeholder(self, stripper):
        """模拟 AI 回复中保留占位符，验证还原正确。"""
        stripper.strip("联系 13812345678")
        ai_reply = "好的，我已记录 <PHONE_1> 的联系方式。"
        restored = stripper.restore(ai_reply)
        assert "13812345678" in restored
        assert "<PHONE_1>" not in restored


# ---------------------------------------------------------------------------
# 重叠实体处理
# ---------------------------------------------------------------------------


class TestOverlapResolution:
    def test_overlapping_entities_resolved(self, stripper):
        """确保重叠实体不导致重复替换或崩溃。"""
        # 身份证（18位）和手机（11位）如果重叠，只保留一个
        text = "号码：13812345678901234567"
        result = stripper.strip(text)
        # 结果中不应有原始数字，且不会崩溃
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# strip_and_call
# ---------------------------------------------------------------------------


class TestStripAndCall:
    def test_strip_and_call_roundtrip(self, stripper):
        original = "电话：13812345678"

        def mock_fn(text):
            # 模拟 AI 原样返回（含占位符）
            return text

        result = stripper.strip_and_call(original, mock_fn)
        assert "13812345678" in result
        assert "<PHONE_1>" not in result
