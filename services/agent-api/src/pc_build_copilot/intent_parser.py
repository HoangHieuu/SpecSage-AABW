import re
import unicodedata

from pc_build_copilot.models import BuildIntent, Clarification, UseCase


GAME_ALIASES = {
    "valorant": "Valorant",
    "lmht": "LMHT",
    "lien minh": "LMHT",
    "liên minh": "LMHT",
    "league": "League of Legends",
    "lol": "League of Legends",
    "cs2": "Counter-Strike 2",
    "counter-strike": "Counter-Strike 2",
    "pubg": "PUBG",
    "cyberpunk": "Cyberpunk 2077",
    "genshin": "Genshin Impact",
    "fortnite": "Fortnite",
    "dota": "Dota 2",
}

APP_ALIASES = {
    "premiere": "Adobe Premiere Pro",
    "after effects": "Adobe After Effects",
    "photoshop": "Adobe Photoshop",
    "blender": "Blender",
    "autocad": "AutoCAD",
    "solidworks": "SolidWorks",
    "local llm": "Local LLM",
    "llm": "Local LLM",
}

BRANDS = ["Intel", "AMD", "NVIDIA", "ASUS", "MSI", "Gigabyte", "Corsair"]
COMPONENT_PATTERN = re.compile(
    r"\b(?:RTX|GTX|RX|Ryzen|Core i[3579]|i[3579])[\w\s.-]{0,16}\b",
    re.IGNORECASE,
)


def parse_intent(message: str, preset: UseCase | None = None) -> tuple[BuildIntent, Clarification]:
    normalized = _normalize(message)
    use_case = preset or _detect_use_case(normalized)
    budget_min, budget_max, interpretation = _parse_budget(normalized)
    intent = BuildIntent(
        raw_text=message,
        use_case=use_case,
        budget_min=budget_min,
        budget_max=budget_max,
        budget_interpretation=interpretation,
        target_games=_find_aliases(normalized, GAME_ALIASES),
        target_apps=_find_aliases(normalized, APP_ALIASES),
        performance_targets=_parse_performance_targets(message),
        form_factor=_parse_form_factor(normalized),
        brand_preferences=_parse_brands(message),
        noise_preferences=_parse_noise_preference(normalized),
        aesthetic_preferences=_parse_aesthetic_preference(normalized),
        mentioned_components=_parse_components(message),
        safe_defaults=_safe_defaults(use_case),
    )
    return intent, _next_clarification(intent, normalized)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).lower()
    return re.sub(r"\s+", " ", normalized).strip()


def _detect_use_case(text: str) -> UseCase:
    if any(token in text for token in ["gaming", "game", "chơi", "valorant", "lmht"]):
        return UseCase.GAMING
    if any(token in text for token in ["đồ họa", "do hoa", "creator", "premiere", "blender"]):
        return UseCase.CREATOR
    if any(token in text for token in ["văn phòng", "van phong", "office", "excel"]):
        return UseCase.OFFICE
    if any(token in text for token in ["sinh viên", "student", "học tập", "hoc tap"]):
        return UseCase.STUDENT
    if any(token in text for token in ["local llm", "ai", "machine learning", "llm"]):
        return UseCase.AI
    if "stream" in text:
        return UseCase.STREAMING
    if any(token in text for token in ["mini itx", "compact", "nhỏ gọn", "nho gon"]):
        return UseCase.COMPACT
    return UseCase.UNKNOWN


def _parse_budget(text: str) -> tuple[int | None, int | None, str | None]:
    range_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(triệu|tr|m|k|000|vnd)?\s*(?:-|đến|toi|tới|~)\s*(\d+(?:[.,]\d+)?)\s*(triệu|tr|m|k|000|vnd)?",
        text,
    )
    if range_match:
        suffix = range_match.group(2) or range_match.group(4)
        if suffix is None and not _has_budget_keyword(text):
            return None, None, None
        low = _money_to_vnd(range_match.group(1), suffix)
        high = _money_to_vnd(range_match.group(3), suffix)
        return low, high, "explicit_range"

    if "tầm trung" in text or "tam trung" in text:
        return 18_000_000, 25_000_000, "phrase:tầm trung -> 18-25 triệu"

    number_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(triệu|tr|m|k|000|vnd)", text)
    if not number_match:
        plain_match = re.search(r"\b(\d{7,})\b", text)
        if not plain_match:
            return None, None, None
        number_match = plain_match

    suffix = number_match.group(2) if number_match.lastindex and number_match.lastindex >= 2 else None
    amount = _money_to_vnd(number_match.group(1), suffix)
    if any(token in text for token in ["dưới", "duoi", "under", "không quá", "toi da", "tối đa"]):
        return None, amount, "upper_bound"
    if any(token in text for token in ["trên", "tren", "ít nhất", "it nhat", "at least"]):
        return amount, None, "lower_bound"
    if any(token in text for token in ["khoảng", "khoang", "tầm", "tam", "around"]):
        return int(amount * 0.9), int(amount * 1.1), "approximate:+/-10%"
    return None, amount, "single_max"


def _money_to_vnd(raw_value: str, suffix: str | None) -> int:
    value = float(raw_value.replace(",", "."))
    suffix = suffix or ""
    if suffix in {"triệu", "tr", "m"}:
        return int(value * 1_000_000)
    if suffix == "k":
        return int(value * 1_000)
    if suffix in {"000", "vnd"} or value >= 1_000_000:
        return int(value)
    return int(value * 1_000_000)


def _has_budget_keyword(text: str) -> bool:
    return any(
        token in text
        for token in ["ngân sách", "ngan sach", "budget", "khoảng", "khoang", "tầm", "tam"]
    )


def _find_aliases(text: str, aliases: dict[str, str]) -> list[str]:
    found = []
    for needle, label in aliases.items():
        if needle in text and label not in found:
            found.append(label)
    return found


def _parse_performance_targets(message: str) -> list[str]:
    targets = []
    for match in re.finditer(r"\b(?:\d{3,4}p|[1248]k|\d{2,3}\s*(?:fps|hz))\b", message, re.IGNORECASE):
        targets.append(re.sub(r"\s+", "", match.group(0)))
    for quality in ["Low", "Medium", "High", "Ultra"]:
        if re.search(rf"\b{quality}\b", message, re.IGNORECASE):
            targets.append(quality)
    return list(dict.fromkeys(targets))


def _parse_form_factor(text: str) -> str | None:
    if "mini itx" in text or "mini-itx" in text:
        return "Mini-ITX"
    if "micro atx" in text or "m-atx" in text or "matx" in text:
        return "Micro-ATX"
    if "atx" in text:
        return "ATX"
    if "nhỏ gọn" in text or "nho gon" in text or "compact" in text:
        return "compact"
    return None


def _parse_brands(message: str) -> list[str]:
    found = []
    for brand in BRANDS:
        if re.search(rf"\b{re.escape(brand)}\b", message, re.IGNORECASE):
            found.append(brand)
    return found


def _parse_noise_preference(text: str) -> str | None:
    if any(token in text for token in ["êm", "em", "yên tĩnh", "quiet", "silent"]):
        return "quiet"
    return None


def _parse_aesthetic_preference(text: str) -> str | None:
    if "rgb" in text:
        return "rgb"
    if any(token in text for token in ["trắng", "white"]):
        return "white"
    if any(token in text for token in ["đen", "black"]):
        return "black"
    return None


def _parse_components(message: str) -> list[str]:
    components = [match.group(0).strip() for match in COMPONENT_PATTERN.finditer(message)]
    return list(dict.fromkeys(components))


def _safe_defaults(use_case: UseCase) -> list[str]:
    if use_case == UseCase.GAMING:
        return ["Ưu tiên GPU", "Ổ SSD NVMe cho game", "RAM tối thiểu 16GB"]
    if use_case == UseCase.CREATOR:
        return ["RAM tối thiểu 32GB", "Ưu tiên VRAM và NVMe"]
    if use_case == UseCase.OFFICE:
        return ["Ưu tiên độ ổn định", "Có thể dùng iGPU nếu phù hợp"]
    if use_case == UseCase.AI:
        return ["Ưu tiên VRAM", "RAM tối thiểu 32GB"]
    return ["Giữ cấu hình an toàn", "Không tạo build khi thiếu ngân sách"]


def _next_clarification(intent: BuildIntent, text: str) -> Clarification:
    if intent.budget_max is None and intent.budget_min is None:
        return Clarification(
            field="budget",
            question="Ngân sách dự kiến của bạn là bao nhiêu triệu đồng?",
            required=True,
        )
    if intent.use_case == UseCase.UNKNOWN:
        return Clarification(
            field="use_case",
            question="Bạn dùng PC chủ yếu cho gaming, đồ họa, văn phòng hay AI/local LLM?",
            required=True,
        )
    if intent.use_case == UseCase.GAMING and not intent.target_games and "bỏ qua" not in text and "skip" not in text:
        return Clarification(
            field="target_games",
            question="Bạn muốn ưu tiên game nào và màn hình 1080p hay 1440p?",
            required=False,
        )
    if intent.use_case == UseCase.CREATOR and not intent.target_apps and "bỏ qua" not in text and "skip" not in text:
        return Clarification(
            field="target_apps",
            question="Bạn dùng phần mềm chính nào, ví dụ Premiere, Blender hay Photoshop?",
            required=False,
        )
    return Clarification()
