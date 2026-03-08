"""
PII Stripper 核心模块

检测文本中的个人隐私信息（PII）并替换为占位符，
支持后续将占位符还原为原始值。
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 占位符标签映射（Presidio 实体类型 -> 用户友好标签）
ENTITY_LABEL_MAP: dict[str, str] = {
    "PERSON": "PERSON",
    "PHONE_NUMBER": "PHONE",
    "EMAIL_ADDRESS": "EMAIL",
    "CREDIT_CARD": "CREDIT_CARD",
    "LOCATION": "LOCATION",
    "ORGANIZATION": "ORG",
    "CN_PHONE": "PHONE",
    "CN_ID": "ID_CARD",
    "CN_BANK_CARD": "BANK_CARD",
    "URL": "URL",
    "IP_ADDRESS": "IP",
    "DATE_TIME": "DATE",
    "NRP": "NRP",
    "MEDICAL_LICENSE": "MEDICAL",
    "US_SSN": "SSN",
    "US_PASSPORT": "PASSPORT",
    "IBAN_CODE": "IBAN",
}

# 正则表达式模式（中文 PII 及通用格式）
REGEX_PATTERNS: list[tuple[str, str, float]] = [
    # 中国大陆手机号（以 1 开头，第二位 3-9，共 11 位）
    ("CN_PHONE", r"(?<!\d)1[3-9]\d{9}(?!\d)", 0.95),
    # 中国居民身份证（18 位，末位可为 X）
    ("CN_ID", r"(?<!\d)\d{17}[\dXx](?!\d)", 0.92),
    # 电子邮件地址
    ("EMAIL_ADDRESS", r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", 0.90),
    # IPv4 地址
    ("IP_ADDRESS", r"\b(?:\d{1,3}\.){3}\d{1,3}\b", 0.85),
]


@dataclass
class PIIEntity:
    """表示一个检测到的 PII 实体。"""
    text: str
    entity_type: str
    start: int
    end: int
    score: float


class PIIStripper:
    """
    PII 脱敏器。

    功能：
    1. 检测文本中的 PII 实体（手机号、身份证、邮箱、人名等）
    2. 将其替换为占位符（如 <PHONE_1>、<PERSON_1>）
    3. 在获得 AI 回复后，将占位符还原为原始值

    同一原始值始终使用相同占位符，确保 AI 理解上下文关联。
    """

    def __init__(self, use_nlp: bool = True):
        """
        初始化 PIIStripper。

        Args:
            use_nlp: 是否启用 Presidio + SpaCy NLP 识别（需要安装对应模型）。
                     禁用时仅使用正则表达式，适合轻量级场景。
        """
        self._use_nlp = use_nlp
        self._analyzer = None
        self._presidio_language = "en"
        self._placeholder_counter: dict[str, int] = {}
        self._placeholder_map: dict[str, str] = {}  # placeholder -> original
        self._value_map: dict[str, str] = {}         # original -> placeholder

        if use_nlp:
            self._init_presidio()

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    @property
    def mapping(self) -> dict[str, str]:
        """返回当前的 {占位符: 原始值} 映射表（只读副本）。"""
        return dict(self._placeholder_map)

    def strip(self, text: str) -> str:
        """
        将文本中的 PII 替换为占位符。

        Args:
            text: 待脱敏的原始文本。

        Returns:
            脱敏后的文本，PII 已被 <TYPE_N> 格式的占位符替代。
        """
        self._reset()
        entities = self._detect_entities(text)
        entities = self._resolve_overlaps(entities)
        return self._apply_replacements(text, entities)

    def restore(self, text: str) -> str:
        """
        将脱敏文本中的占位符还原为原始值。

        Args:
            text: 含有占位符的文本（通常是 AI 的回复）。

        Returns:
            还原了 PII 的文本。
        """
        result = text
        # 按占位符长度降序替换，避免短占位符被提前匹配
        for placeholder, original in sorted(
            self._placeholder_map.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        ):
            result = result.replace(placeholder, original)
        return result

    def strip_and_call(self, text: str, call_fn) -> str:
        """
        脱敏 → 调用处理函数 → 还原，一步完成。

        Args:
            text: 原始文本。
            call_fn: 接受脱敏文本并返回处理结果的可调用对象。

        Returns:
            还原 PII 后的处理结果。
        """
        anonymized = self.strip(text)
        response = call_fn(anonymized)
        return self.restore(response)

    # ------------------------------------------------------------------
    # 内部初始化
    # ------------------------------------------------------------------

    def _init_presidio(self) -> None:
        """初始化 Presidio 分析引擎，失败时降级为正则模式。"""
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
        except ImportError:
            logger.warning(
                "presidio-analyzer 未安装，已降级为正则模式。"
                "运行 `pip install presidio-analyzer` 可启用 NLP 识别。"
            )
            return

        # 依次尝试加载 SpaCy 模型
        model_candidates = [
            ("zh_core_web_sm", "zh"),
            ("en_core_web_sm", "en"),
            ("en_core_web_lg", "en"),
        ]
        nlp_config = None
        for model_name, lang_code in model_candidates:
            try:
                import spacy
                spacy.load(model_name)
                nlp_config = {
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": lang_code, "model_name": model_name}],
                }
                self._presidio_language = lang_code
                logger.info("已加载 SpaCy 模型：%s", model_name)
                break
            except OSError:
                continue

        if nlp_config is None:
            logger.warning(
                "未找到 SpaCy 模型，已降级为正则模式。\n"
                "运行以下命令安装中文模型：\n"
                "  python -m spacy download zh_core_web_sm"
            )
            return

        try:
            provider = NlpEngineProvider(nlp_configuration=nlp_config)
            nlp_engine = provider.create_engine()
            self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            self._add_custom_recognizers()
        except Exception as exc:
            logger.warning("Presidio 初始化失败（%s），已降级为正则模式。", exc)
            self._analyzer = None

    def _add_custom_recognizers(self) -> None:
        """向 Presidio 注册中文特定识别器。"""
        if self._analyzer is None:
            return

        try:
            from presidio_analyzer import PatternRecognizer, Pattern
        except ImportError:
            return

        custom_recognizers = [
            PatternRecognizer(
                supported_entity="CN_PHONE",
                patterns=[Pattern("cn_phone", r"(?<!\d)1[3-9]\d{9}(?!\d)", 0.95)],
            ),
            PatternRecognizer(
                supported_entity="CN_ID",
                patterns=[Pattern("cn_id", r"(?<!\d)\d{17}[\dXx](?!\d)", 0.92)],
            ),
            PatternRecognizer(
                supported_entity="CN_BANK_CARD",
                patterns=[Pattern("cn_bank_card", r"(?<!\d)\d{16,19}(?!\d)", 0.65)],
            ),
        ]
        for recognizer in custom_recognizers:
            self._analyzer.registry.add_recognizer(recognizer)

    # ------------------------------------------------------------------
    # 内部状态管理
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        """在每次 strip() 调用前重置内部状态。"""
        self._placeholder_counter = {}
        self._placeholder_map = {}
        self._value_map = {}

    def _make_placeholder(self, entity_type: str) -> str:
        """生成唯一占位符，如 <PHONE_1>、<PERSON_2>。"""
        label = ENTITY_LABEL_MAP.get(entity_type, entity_type)
        count = self._placeholder_counter.get(label, 0) + 1
        self._placeholder_counter[label] = count
        return f"<{label}_{count}>"

    # ------------------------------------------------------------------
    # 实体检测
    # ------------------------------------------------------------------

    def _detect_entities(self, text: str) -> list[PIIEntity]:
        """综合运用正则和 NLP 检测所有 PII 实体。"""
        entities: list[PIIEntity] = []
        entities.extend(self._detect_regex_entities(text))
        if self._analyzer:
            entities.extend(self._detect_presidio_entities(text))
        return entities

    def _detect_regex_entities(self, text: str) -> list[PIIEntity]:
        """使用正则表达式检测 PII 实体。"""
        entities: list[PIIEntity] = []
        for entity_type, pattern, score in REGEX_PATTERNS:
            for match in re.finditer(pattern, text):
                entities.append(PIIEntity(
                    text=match.group(),
                    entity_type=entity_type,
                    start=match.start(),
                    end=match.end(),
                    score=score,
                ))
        return entities

    def _detect_presidio_entities(self, text: str) -> list[PIIEntity]:
        """使用 Presidio + SpaCy 检测 NLP 级别的 PII 实体。"""
        entities: list[PIIEntity] = []
        try:
            results = self._analyzer.analyze(
                text=text,
                language=self._presidio_language,
                entities=[
                    "PERSON", "EMAIL_ADDRESS", "CREDIT_CARD", "PHONE_NUMBER",
                    "LOCATION", "ORGANIZATION", "URL", "IP_ADDRESS",
                    "DATE_TIME", "NRP", "US_SSN", "US_PASSPORT",
                    "IBAN_CODE", "MEDICAL_LICENSE",
                ],
                score_threshold=0.5,
            )
            for result in results:
                entities.append(PIIEntity(
                    text=text[result.start:result.end],
                    entity_type=result.entity_type,
                    start=result.start,
                    end=result.end,
                    score=result.score,
                ))
        except Exception as exc:
            logger.warning("Presidio 分析失败：%s", exc)
        return entities

    # ------------------------------------------------------------------
    # 冲突解决与替换
    # ------------------------------------------------------------------

    def _resolve_overlaps(self, entities: list[PIIEntity]) -> list[PIIEntity]:
        """
        解决重叠实体冲突。

        策略：按起始位置排序，遇到与已选实体重叠的实体时，
        优先保留置信度更高的那个（先到先得，同位置取高分）。
        """
        if not entities:
            return []

        # 先按起始位置升序，同位置按分数降序
        sorted_ents = sorted(entities, key=lambda e: (e.start, -e.score))

        result: list[PIIEntity] = []
        last_end = -1
        for entity in sorted_ents:
            if entity.start >= last_end:
                result.append(entity)
                last_end = entity.end
        return result

    def _apply_replacements(self, text: str, entities: list[PIIEntity]) -> str:
        """
        将实体逐一替换为占位符，构建脱敏后文本。

        相同原始值复用同一占位符。
        """
        parts: list[str] = []
        last_end = 0

        for entity in sorted(entities, key=lambda e: e.start):
            # 保留实体前的原始文本
            parts.append(text[last_end:entity.start])

            original = entity.text
            if original in self._value_map:
                placeholder = self._value_map[original]
            else:
                placeholder = self._make_placeholder(entity.entity_type)
                self._placeholder_map[placeholder] = original
                self._value_map[original] = placeholder

            parts.append(placeholder)
            last_end = entity.end

        # 保留末尾原始文本
        parts.append(text[last_end:])
        return "".join(parts)
