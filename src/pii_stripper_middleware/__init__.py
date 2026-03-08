"""
pii-stripper-middleware

一个轻量级 PII 脱敏中间件，在将用户数据发送给 LLM 之前
自动识别并替换个人隐私信息（姓名、手机号、身份证等），
AI 回复后再将占位符还原为原始值。
"""

from pii_stripper_middleware.core import PIIStripper

__version__ = "0.1.0"
__all__ = ["PIIStripper"]
