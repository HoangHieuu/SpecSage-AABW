from pc_build_copilot.intent_parser import parse_intent
from pc_build_copilot.models import UseCase


def test_parse_vietnamese_gaming_intent_with_mixed_terms() -> None:
    intent, clarification = parse_intent(
        "PC gaming 25 triệu chơi Valorant và LMHT 144Hz RTX 5060 Ti"
    )

    assert intent.use_case == UseCase.GAMING
    assert intent.budget_max == 25_000_000
    assert "Valorant" in intent.target_games
    assert "LMHT" in intent.target_games
    assert "144Hz" in intent.performance_targets
    assert "RTX 5060 Ti" in intent.mentioned_components
    assert clarification.field is None


def test_parse_monitor_as_mentioned_component() -> None:
    intent, clarification = parse_intent(
        "PC gaming 30 triệu chơi Cyberpunk 2077 1440p Ultra kèm màn hình 144Hz"
    )

    assert intent.use_case == UseCase.GAMING
    assert "monitor" in intent.mentioned_components
    assert {"1440p", "144Hz", "Ultra"} <= set(intent.performance_targets)
    assert clarification.field is None


def test_parse_office_multi_monitor_count() -> None:
    intent, clarification = parse_intent(
        "Máy văn phòng khoảng 20 triệu chạy Excel và 2 màn hình, ưu tiên êm"
    )

    assert intent.use_case == UseCase.OFFICE
    assert intent.monitor_count == 2
    assert "monitor" in intent.mentioned_components
    assert intent.noise_preferences == "quiet"
    assert clarification.field is None


def test_parse_streaming_app_and_llm_model_class_targets() -> None:
    streaming_intent, _ = parse_intent("PC stream OBS 25 triệu")
    llm_intent, _ = parse_intent("PC AI local LLM 13B 40 triệu")

    assert streaming_intent.use_case == UseCase.STREAMING
    assert "OBS Studio" in streaming_intent.target_apps
    assert "Streaming" in streaming_intent.target_apps
    assert llm_intent.use_case == UseCase.AI
    assert "Local LLM" in llm_intent.target_apps
    assert "13B" in llm_intent.performance_targets


def test_missing_budget_returns_one_required_question() -> None:
    intent, clarification = parse_intent("PC gaming chơi Valorant")

    assert intent.use_case == UseCase.GAMING
    assert clarification.field == "budget"
    assert clarification.required is True
    assert "Ngân sách" in (clarification.question or "")


def test_approximate_budget_maps_to_range() -> None:
    intent, clarification = parse_intent("Máy văn phòng khoảng 20 triệu, ưu tiên êm")

    assert intent.use_case == UseCase.OFFICE
    assert intent.budget_min == 18_000_000
    assert intent.budget_max == 22_000_000
    assert intent.noise_preferences == "quiet"
    assert clarification.field is None


def test_midrange_phrase_has_documented_interpretation() -> None:
    intent, clarification = parse_intent("PC tầm trung cho Photoshop")

    assert intent.budget_min == 18_000_000
    assert intent.budget_max == 25_000_000
    assert intent.budget_interpretation == "phrase:tầm trung -> 18-25 triệu"
    assert "Adobe Photoshop" in intent.target_apps
    assert clarification.field == "use_case"
