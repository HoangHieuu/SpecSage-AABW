from __future__ import annotations

import re
import unicodedata

from pc_build_copilot.build_models import OptimizerBudgetAllocation
from pc_build_copilot.compatibility_models import BuildSlot
from pc_build_copilot.models import BuildIntent, UseCase


BASE_BUDGET_WEIGHTS: dict[UseCase, dict[BuildSlot, int]] = {
    UseCase.GAMING: {
        BuildSlot.VGA: 45,
        BuildSlot.CPU: 18,
        BuildSlot.MAINBOARD: 10,
        BuildSlot.RAM: 8,
        BuildSlot.STORAGE: 7,
        BuildSlot.PSU: 6,
        BuildSlot.CASE: 6,
    },
    UseCase.CREATOR: {
        BuildSlot.VGA: 28,
        BuildSlot.CPU: 22,
        BuildSlot.MAINBOARD: 10,
        BuildSlot.RAM: 18,
        BuildSlot.STORAGE: 12,
        BuildSlot.PSU: 5,
        BuildSlot.CASE: 5,
    },
    UseCase.AI: {
        BuildSlot.VGA: 45,
        BuildSlot.CPU: 14,
        BuildSlot.MAINBOARD: 9,
        BuildSlot.RAM: 18,
        BuildSlot.STORAGE: 6,
        BuildSlot.PSU: 5,
        BuildSlot.CASE: 3,
    },
    UseCase.STREAMING: {
        BuildSlot.VGA: 34,
        BuildSlot.CPU: 22,
        BuildSlot.MAINBOARD: 10,
        BuildSlot.RAM: 12,
        BuildSlot.STORAGE: 8,
        BuildSlot.PSU: 7,
        BuildSlot.CASE: 7,
    },
    UseCase.OFFICE: {
        BuildSlot.VGA: 4,
        BuildSlot.CPU: 26,
        BuildSlot.MAINBOARD: 14,
        BuildSlot.RAM: 14,
        BuildSlot.STORAGE: 18,
        BuildSlot.PSU: 10,
        BuildSlot.CASE: 14,
    },
    UseCase.STUDENT: {
        BuildSlot.VGA: 8,
        BuildSlot.CPU: 24,
        BuildSlot.MAINBOARD: 14,
        BuildSlot.RAM: 16,
        BuildSlot.STORAGE: 18,
        BuildSlot.PSU: 8,
        BuildSlot.CASE: 12,
    },
    UseCase.COMPACT: {
        BuildSlot.VGA: 28,
        BuildSlot.CPU: 20,
        BuildSlot.MAINBOARD: 16,
        BuildSlot.RAM: 10,
        BuildSlot.STORAGE: 8,
        BuildSlot.PSU: 8,
        BuildSlot.CASE: 10,
    },
    UseCase.UNKNOWN: {
        BuildSlot.VGA: 20,
        BuildSlot.CPU: 22,
        BuildSlot.MAINBOARD: 13,
        BuildSlot.RAM: 14,
        BuildSlot.STORAGE: 13,
        BuildSlot.PSU: 8,
        BuildSlot.CASE: 10,
    },
}

PRIORITY_LABELS_VI = {
    "gpu": "ưu tiên GPU/VGA",
    "quiet": "ưu tiên vận hành êm",
    "rgb": "ưu tiên RGB/thẩm mỹ",
}


def build_budget_allocation(intent: BuildIntent) -> OptimizerBudgetAllocation:
    overrides = priority_overrides_for_intent(intent)
    weights = _apply_priority_overrides(
        BASE_BUDGET_WEIGHTS.get(intent.use_case, BASE_BUDGET_WEIGHTS[UseCase.UNKNOWN]),
        overrides,
    )
    target_amounts = {}
    if intent.budget_max:
        target_amounts = {
            slot.value: intent.budget_max * weight // 100
            for slot, weight in weights.items()
        }

    notes = [
        f"Chiến lược ngân sách dùng preset {intent.use_case.value} với tổng trọng số 100%.",
    ]
    if overrides:
        labels = ", ".join(PRIORITY_LABELS_VI[item] for item in overrides)
        notes.append(f"Đã áp dụng override từ intent: {labels}.")
    if intent.mentioned_components and any(
        component.lower() in {"monitor", "màn hình", "man hinh"}
        for component in intent.mentioned_components
    ):
        notes.append(
            "Monitor/peripheral được nhận diện nhưng chưa tự trừ ngân sách vì catalog monitor chưa được curate."
        )

    return OptimizerBudgetAllocation(
        use_case=intent.use_case.value,
        budget_max_vnd=intent.budget_max,
        weights={slot.value: weight for slot, weight in weights.items()},
        target_amounts_vnd=target_amounts,
        reserved_peripherals_vnd=0,
        reserved_services_vnd=0,
        notes_vi=notes,
    )


def priority_overrides_for_intent(intent: BuildIntent) -> list[str]:
    text = _normalize(intent.raw_text)
    overrides: list[str] = []
    if (
        re.search(r"(uu tien|ưu tiên).{0,24}(vga|gpu|card|nvidia|rtx)", text)
        or "NVIDIA" in intent.brand_preferences
    ):
        overrides.append("gpu")
    if intent.noise_preferences == "quiet" or re.search(
        r"(uu tien|ưu tiên).{0,24}(em|êm|im lang|im lặng|quiet|silent)",
        text,
    ):
        overrides.append("quiet")
    if intent.aesthetic_preferences == "rgb" or re.search(
        r"(uu tien|ưu tiên).{0,24}(rgb|led|den mau|đèn màu)",
        text,
    ):
        overrides.append("rgb")
    return list(dict.fromkeys(overrides))


def priority_labels_vi(overrides: list[str]) -> list[str]:
    return [PRIORITY_LABELS_VI[item] for item in overrides if item in PRIORITY_LABELS_VI]


def _apply_priority_overrides(
    base_weights: dict[BuildSlot, int],
    overrides: list[str],
) -> dict[BuildSlot, int]:
    weights = dict(base_weights)
    if "gpu" in overrides and BuildSlot.VGA in weights:
        weights[BuildSlot.VGA] += 8
        _discount(weights, [BuildSlot.CASE, BuildSlot.STORAGE, BuildSlot.PSU], 8)
    if "quiet" in overrides:
        weights[BuildSlot.PSU] = weights.get(BuildSlot.PSU, 0) + 4
        weights[BuildSlot.CASE] = weights.get(BuildSlot.CASE, 0) + 3
        _discount(weights, [BuildSlot.VGA, BuildSlot.STORAGE], 7)
    if "rgb" in overrides:
        weights[BuildSlot.CASE] = weights.get(BuildSlot.CASE, 0) + 4
        _discount(weights, [BuildSlot.STORAGE, BuildSlot.PSU], 4)
    return _normalize_weights(weights)


def _discount(weights: dict[BuildSlot, int], slots: list[BuildSlot], amount: int) -> None:
    remaining = amount
    for slot in slots:
        if remaining <= 0:
            break
        available = max(0, weights.get(slot, 0) - 2)
        reduction = min(available, remaining)
        weights[slot] = weights.get(slot, 0) - reduction
        remaining -= reduction


def _normalize_weights(weights: dict[BuildSlot, int]) -> dict[BuildSlot, int]:
    total = sum(weights.values())
    if total <= 0:
        return weights
    normalized = {
        slot: max(1, round(weight * 100 / total))
        for slot, weight in weights.items()
    }
    delta = 100 - sum(normalized.values())
    if delta:
        largest_slot = max(normalized, key=lambda slot: normalized[slot])
        normalized[largest_slot] += delta
    return normalized


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).lower()
    return re.sub(r"\s+", " ", normalized).strip()
