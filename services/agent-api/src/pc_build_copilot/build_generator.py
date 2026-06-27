from __future__ import annotations

from collections.abc import Iterable
from uuid import uuid4

from pc_build_copilot.build_models import (
    BudgetStatus,
    BuildArtifact,
    BuildItem,
    BuildStatus,
    MockCartPayload,
)
from pc_build_copilot.catalog_models import CatalogSku, CatalogSnapshot, ComponentCategory
from pc_build_copilot.compatibility_models import BuildSlot
from pc_build_copilot.compatibility_rules import validate_build_compatibility
from pc_build_copilot.models import BuildIntent, UseCase
from pc_build_copilot.performance_profile import generate_performance_profile


REQUIRED_BASE_SLOTS = (
    BuildSlot.CPU,
    BuildSlot.MAINBOARD,
    BuildSlot.RAM,
    BuildSlot.STORAGE,
    BuildSlot.PSU,
    BuildSlot.CASE,
)


def generate_build_artifact(
    *,
    build_session_id: str,
    intent: BuildIntent,
    catalog: CatalogSnapshot,
) -> BuildArtifact:
    selected = _select_skus(intent, catalog.items)
    build_id = f"build_{uuid4().hex}"
    compatibility_report = validate_build_compatibility(
        build_id=build_id,
        selected_skus={slot: sku.sku for slot, sku in selected.items()},
        catalog=catalog,
    )
    total_price = sum(item.price_vnd for item in selected.values())
    budget_status, budget_gap = _budget_status(total_price, intent.budget_max)
    can_approve = compatibility_report.can_approve and budget_status != BudgetStatus.OVER_BUDGET
    status = _build_status(compatibility_report.can_approve, budget_status)
    performance_profile = generate_performance_profile(intent=intent, selected_skus=selected)

    items = [
        BuildItem(
            slot=slot,
            sku=item.sku,
            name=item.name,
            category=item.category,
            price_vnd=item.price_vnd,
            url=item.url,
            brand=item.brand,
            specs_confidence=item.specs_confidence,
            explanation_vi=_item_explanation(slot, item, intent),
        )
        for slot, item in selected.items()
    ]

    warnings = [
        *_budget_warnings(total_price, intent.budget_max, budget_gap),
        *performance_profile.warnings_vi,
    ]
    if not compatibility_report.can_approve:
        warnings.append("Cấu hình có lỗi tương thích mức block nên chưa thể duyệt.")

    return BuildArtifact(
        build_id=build_id,
        build_session_id=build_session_id,
        intent_snapshot=intent,
        catalog_version=catalog.snapshot_version,
        rules_version=compatibility_report.rules_version,
        total_price_vnd=total_price,
        budget_max_vnd=intent.budget_max,
        budget_gap_vnd=budget_gap,
        budget_status=budget_status,
        status=status,
        can_approve=can_approve,
        items=items,
        compatibility_report=compatibility_report,
        performance_profile=performance_profile,
        explanations_vi=_build_explanations(intent, total_price, budget_status, catalog),
        warnings_vi=warnings,
        mock_cart_payload=MockCartPayload(
            items=[{"sku": item.sku, "url": item.url} for item in selected.values()]
        ),
    )


def _select_skus(
    intent: BuildIntent, catalog_items: Iterable[CatalogSku]
) -> dict[BuildSlot, CatalogSku]:
    by_category: dict[ComponentCategory, list[CatalogSku]] = {}
    for item in catalog_items:
        if item.stock_quantity <= 0:
            continue
        by_category.setdefault(item.category, []).append(item)

    selected: dict[BuildSlot, CatalogSku] = {}
    for slot in REQUIRED_BASE_SLOTS:
        selected[slot] = _cheapest(by_category.get(_category_for_slot(slot), []), slot)

    if _requires_discrete_gpu(intent, selected.get(BuildSlot.CPU)):
        selected[BuildSlot.VGA] = _cheapest(by_category.get(ComponentCategory.VGA, []), BuildSlot.VGA)

    return selected


def _cheapest(items: list[CatalogSku], slot: BuildSlot) -> CatalogSku:
    if not items:
        raise ValueError(f"Catalog snapshot has no in-stock candidate for {slot.value}.")
    return min(items, key=lambda item: (item.price_vnd, item.sku))


def _category_for_slot(slot: BuildSlot) -> ComponentCategory:
    return ComponentCategory(slot.value)


def _requires_discrete_gpu(intent: BuildIntent, cpu: CatalogSku | None) -> bool:
    if intent.use_case in {UseCase.GAMING, UseCase.CREATOR, UseCase.AI, UseCase.STREAMING}:
        return True
    if cpu and cpu.specs.get("integrated_graphics") is False:
        return True
    return False


def _budget_status(total_price: int, budget_max: int | None) -> tuple[BudgetStatus, int]:
    if budget_max is None:
        return BudgetStatus.UNKNOWN_BUDGET, 0
    if total_price > budget_max:
        return BudgetStatus.OVER_BUDGET, total_price - budget_max
    return BudgetStatus.WITHIN_BUDGET, 0


def _build_status(compat_can_approve: bool, budget_status: BudgetStatus) -> BuildStatus:
    if not compat_can_approve:
        return BuildStatus.BLOCKED
    if budget_status == BudgetStatus.OVER_BUDGET:
        return BuildStatus.OVER_BUDGET
    return BuildStatus.GENERATED


def _build_explanations(
    intent: BuildIntent,
    total_price: int,
    budget_status: BudgetStatus,
    catalog: CatalogSnapshot,
) -> list[str]:
    use_case = _use_case_label(intent.use_case)
    explanation = [
        (
            f"Cấu hình được tạo từ catalog snapshot {catalog.snapshot_version} "
            f"cho nhu cầu {use_case}."
        ),
        (
            "Các linh kiện đều là SKU trong catalog cục bộ, có link sản phẩm và "
            "giá snapshot để kiểm tra lại."
        ),
        (
            "Tương thích được kiểm tra bằng rule engine trước khi cho phép duyệt build."
        ),
    ]
    if budget_status == BudgetStatus.WITHIN_BUDGET:
        explanation.append(f"Tổng giá snapshot là {_format_vnd(total_price)}, nằm trong ngân sách.")
    if budget_status == BudgetStatus.OVER_BUDGET:
        explanation.append(
            "Snapshot hiện tại không có phương án rẻ hơn đủ slot, nên hệ thống trả về "
            "khoảng vượt ngân sách thay vì bịa linh kiện ngoài catalog."
        )
    return explanation


def _budget_warnings(
    total_price: int, budget_max: int | None, budget_gap: int
) -> list[str]:
    if budget_max is None:
        return ["Chưa có budget_max nên build chưa thể chứng minh nằm trong ngân sách."]
    if budget_gap > 0:
        return [
            (
                f"Build vượt ngân sách {_format_vnd(budget_max)} "
                f"{_format_vnd(budget_gap)} theo giá snapshot."
            ),
            "Giá có thể thay đổi; kiểm tra lại link Phong Vu trước khi mua.",
        ]
    return ["Giá có thể thay đổi; kiểm tra lại link Phong Vu trước khi mua."]


def _item_explanation(slot: BuildSlot, item: CatalogSku, intent: BuildIntent) -> str:
    if slot == BuildSlot.VGA:
        return "GPU được chọn để ưu tiên workload gaming/creator mà không dùng FPS phỏng đoán."
    if slot == BuildSlot.PSU:
        return "PSU được chọn vì rule engine cần công suất và đầu cấp nguồn đủ cho cấu hình."
    if slot == BuildSlot.CASE:
        return "Case được chọn vì có dữ liệu clearance để kiểm tra chiều dài GPU."
    if slot == BuildSlot.RAM:
        return "RAM được chọn theo chuẩn bộ nhớ trong snapshot và kiểm tra với mainboard."
    if slot == BuildSlot.STORAGE:
        return "SSD NVMe được chọn làm ổ boot tối thiểu cho trải nghiệm mượt hơn."
    if slot == BuildSlot.CPU:
        return f"CPU được chọn làm nền tảng cho nhu cầu {_use_case_label(intent.use_case)}."
    if slot == BuildSlot.MAINBOARD:
        return "Mainboard được chọn để khớp socket CPU và chuẩn RAM."
    return "Linh kiện được chọn từ catalog snapshot hiện tại."


def _use_case_label(use_case: UseCase) -> str:
    labels = {
        UseCase.GAMING: "gaming",
        UseCase.CREATOR: "đồ họa",
        UseCase.OFFICE: "văn phòng",
        UseCase.STUDENT: "học tập",
        UseCase.AI: "AI/local LLM",
        UseCase.STREAMING: "streaming",
        UseCase.COMPACT: "compact",
        UseCase.UNKNOWN: "chưa rõ",
    }
    return labels[use_case]


def _format_vnd(value: int) -> str:
    return f"{value:,}".replace(",", ".") + " VND"
