"""
支持 `python -m pii_stripper_middleware` 方式直接运行 CLI。
"""

from pii_stripper_middleware.cli import app

if __name__ == "__main__":
    app()
