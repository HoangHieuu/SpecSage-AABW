from __future__ import annotations

from collections.abc import Iterable
from uuid import uuid4

from pc_build_copilot.build_models import (
    BudgetStatus,
    BuildAlternative,
    BuildAlternativeChangedSlot,
    BuildAlternativeKind,
    BuildAlternativesResponse,
    BuildArtifact,
    BuildItem,
    BuildStatus,
    MockCartPayload,
)
from pc_build_copilot.catalog_models import CatalogSku, CatalogSnapshot, ComponentCategory
from pc_build_copilot.compatibility_models import BuildSlot
from pc_build_copilot.compatibility_rules import validate_build_compatibility
from pc_build_copilot.performance_profile import generate_performance_profile


def generate_build_alternatives(
    *,
    base_artifact: BuildArtifact,
    catalog: CatalogSnapshot,
) -> BuildAlternativesResponse:
    catalog_by_sku = {item.sku: item for item in catalog.items}
    selected = _selected_catalog_items(base_artifact, catalog_by_sku)
    alternatives: list[BuildAlternative] = []

    for candidate in _candidate_swaps(selected, catalog.items):
        alternative = _build_alternative(
            base_artifact=base_artifact,
            selected={**selected, candidate.slot: candidate.item},
            candidate=candidate,
            catalog=catalog,
        )
        if alternative is not None:
            alternatives.append(alternative)

    return BuildAlternativesResponse(
        build_id=base_artifact.build_id,
        build_session_id=base_artifact.build_session_id,
        catalog_version=catalog.snapshot_version,
        rules_version=base_artifact.rules_version,
        base_total_price_vnd=base_artifact.total_price_vnd,
        alternatives=alternatives,
    )


def apply_build_alternative(
    *,
    base_artifact: BuildArtifact,
    variant_id: str,
    catalog: CatalogSnapshot,
) -> BuildArtifact | None:
    response = generate_build_alternatives(base_artifact=base_artifact, catalog=catalog)
    alternative = next(
        (item for item in response.alternatives if item.variant_id == variant_id),
        None,
    )
    if alternative is None:
        return None

    build_id = f"build_{uuid4().hex}"
    catalog_by_sku = {item.sku: item for item in catalog.items}
    selected = _selected_catalog_items_from_build_items(alternative.items, catalog_by_sku)
    compatibility_report = validate_build_compatibility(
        build_id=build_id,
        selected_skus={slot: item.sku for slot, item in selected.items()},
        catalog=catalog,
    )
    performance_profile = generate_performance_profile(
        intent=base_artifact.intent_snapshot,
        selected_skus=selected,
    )
    can_approve = (
        compatibility_report.can_approve
        and alternative.budget_status != BudgetStatus.OVER_BUDGET
    )
    status = _build_status(compatibility_report.can_approve, alternative.budget_status)
    warnings = [
        *_budget_warnings(
            alternative.budget_status,
            base_artifact.budget_max_vnd,
            alternative.budget_gap_vnd,
        ),
        *performance_profile.warnings_vi,
    ]
    if not compatibility_report.can_approve:
        warnings.append("Build áp dụng từ biến thể có lỗi tương thích mức block nên chưa thể duyệt.")

    return BuildArtifact(
        build_id=build_id,
        build_session_id=base_artifact.build_session_id,
        build_version=base_artifact.build_version + 1,
        intent_snapshot=base_artifact.intent_snapshot,
        catalog_version=catalog.snapshot_version,
        rules_version=compatibility_report.rules_version,
        total_price_vnd=alternative.total_price_vnd,
        budget_max_vnd=base_artifact.budget_max_vnd,
        budget_gap_vnd=alternative.budget_gap_vnd,
        budget_status=alternative.budget_status,
        status=status,
        can_approve=can_approve,
        items=alternative.items,
        compatibility_report=compatibility_report,
        performance_profile=performance_profile,
        explanations_vi=[
            *alternative.explanations_vi,
            (
                f"Đã áp dụng biến thể {alternative.label_vi} từ build "
                f"{base_artifact.build_id} thành build version {base_artifact.build_version + 1}."
            ),
            "Approval và handoff giỏ mock vẫn là bước riêng sau khi người dùng duyệt build.",
        ],
        warnings_vi=warnings,
        mock_cart_payload=MockCartPayload(
            items=[{"sku": item.sku, "url": item.url} for item in alternative.items]
        ),
    )


class _CandidateSwap:
    def __init__(
        self,
        *,
        kind: BuildAlternativeKind,
        slot: BuildSlot,
        item: CatalogSku,
        label_vi: str,
        summary_vi: str,
        reason_vi: str,
    ) -> None:
        self.kind = kind
        self.slot = slot
        self.item = item
        self.label_vi = label_vi
        self.summary_vi = summary_vi
        self.reason_vi = reason_vi


def _selected_catalog_items(
    base_artifact: BuildArtifact,
    catalog_by_sku: dict[str, CatalogSku],
) -> dict[BuildSlot, CatalogSku]:
    selected = {}
    for item in base_artifact.items:
        catalog_item = catalog_by_sku.get(item.sku)
        if catalog_item is not None:
            selected[item.slot] = catalog_item
    return selected


def _selected_catalog_items_from_build_items(
    build_items: Iterable[BuildItem],
    catalog_by_sku: dict[str, CatalogSku],
) -> dict[BuildSlot, CatalogSku]:
    selected = {}
    for item in build_items:
        catalog_item = catalog_by_sku.get(item.sku)
        if catalog_item is not None:
            selected[item.slot] = catalog_item
    return selected


def _candidate_swaps(
    selected: dict[BuildSlot, CatalogSku],
    catalog_items: Iterable[CatalogSku],
) -> list[_CandidateSwap]:
    candidates = []
    ram = _next_higher_capacity(
        selected=selected,
        catalog_items=catalog_items,
        slot=BuildSlot.RAM,
        category=ComponentCategory.RAM,
        spec_key="capacity_gb",
    )
    if ram is not None:
        candidates.append(
            _CandidateSwap(
                kind=BuildAlternativeKind.RAM_UPGRADE,
                slot=BuildSlot.RAM,
                item=ram,
                label_vi="Nâng RAM",
                summary_vi="Tăng dung lượng RAM cho creator, AI nhẹ hoặc đa nhiệm nặng.",
                reason_vi="Nâng RAM giúp giảm rủi ro nghẽn bộ nhớ khi mở nhiều ứng dụng hoặc project lớn.",
            )
        )

    storage = _next_higher_capacity(
        selected=selected,
        catalog_items=catalog_items,
        slot=BuildSlot.STORAGE,
        category=ComponentCategory.STORAGE,
        spec_key="capacity_gb",
    )
    if storage is not None:
        candidates.append(
            _CandidateSwap(
                kind=BuildAlternativeKind.STORAGE_UPGRADE,
                slot=BuildSlot.STORAGE,
                item=storage,
                label_vi="SSD rộng hơn",
                summary_vi="Tăng dung lượng NVMe cho game, project và dữ liệu cá nhân.",
                reason_vi="Ổ lớn hơn giảm áp lực xoá dữ liệu và vẫn giữ cấu hình trên SKU thật trong snapshot.",
            )
        )

    nvidia_gpu = _nvidia_gpu_candidate(selected, catalog_items)
    if nvidia_gpu is not None:
        candidates.append(
            _CandidateSwap(
                kind=BuildAlternativeKind.NVIDIA_GPU,
                slot=BuildSlot.VGA,
                item=nvidia_gpu,
                label_vi="GPU NVIDIA",
                summary_vi="Đổi sang GPU NVIDIA để phù hợp hơn với workflow CUDA/AI phổ biến.",
                reason_vi="GPU NVIDIA là hướng thử nghiệm tốt hơn cho nhiều toolchain AI local và creator.",
            )
        )

    psu = _next_higher_capacity(
        selected=selected,
        catalog_items=catalog_items,
        slot=BuildSlot.PSU,
        category=ComponentCategory.PSU,
        spec_key="wattage_w",
    )
    if psu is not None:
        candidates.append(
            _CandidateSwap(
                kind=BuildAlternativeKind.PSU_HEADROOM,
                slot=BuildSlot.PSU,
                item=psu,
                label_vi="PSU dư tải",
                summary_vi="Tăng công suất PSU để có thêm khoảng trống cho nâng cấp sau.",
                reason_vi="PSU công suất cao hơn giúp cấu hình có headroom khi đổi GPU hoặc thêm linh kiện.",
            )
        )

    return candidates


def _build_alternative(
    *,
    base_artifact: BuildArtifact,
    selected: dict[BuildSlot, CatalogSku],
    candidate: _CandidateSwap,
    catalog: CatalogSnapshot,
) -> BuildAlternative | None:
    current_item = _item_for_slot(base_artifact, candidate.slot)
    if current_item is None:
        return None

    variant_id = f"{base_artifact.build_id}_{candidate.kind.value}"
    compatibility_report = validate_build_compatibility(
        build_id=variant_id,
        selected_skus={slot: item.sku for slot, item in selected.items()},
        catalog=catalog,
    )
    total_price = sum(item.price_vnd for item in selected.values())
    price_delta = total_price - base_artifact.total_price_vnd
    budget_status, budget_gap = _budget_status(total_price, base_artifact.budget_max_vnd)
    status = _build_status(compatibility_report.can_approve, budget_status)
    can_approve = compatibility_report.can_approve and budget_status != BudgetStatus.OVER_BUDGET
    performance_profile = generate_performance_profile(
        intent=base_artifact.intent_snapshot,
        selected_skus=selected,
    )
    changed_slot = BuildAlternativeChangedSlot(
        slot=candidate.slot,
        current_sku=current_item.sku,
        current_name=current_item.name,
        candidate_sku=candidate.item.sku,
        candidate_name=candidate.item.name,
        price_delta_vnd=candidate.item.price_vnd - current_item.price_vnd,
        reason_vi=candidate.reason_vi,
    )

    warnings = [
        *_budget_warnings(budget_status, base_artifact.budget_max_vnd, budget_gap),
        *performance_profile.warnings_vi,
    ]
    if not compatibility_report.can_approve:
        warnings.append("Biến thể có lỗi tương thích mức block nên chưa thể duyệt.")

    return BuildAlternative(
        variant_id=variant_id,
        kind=candidate.kind,
        label_vi=candidate.label_vi,
        summary_vi=candidate.summary_vi,
        total_price_vnd=total_price,
        price_delta_vnd=price_delta,
        budget_status=budget_status,
        budget_gap_vnd=budget_gap,
        status=status,
        can_approve=can_approve,
        items=_build_items(base_artifact, selected, changed_slot),
        changed_slots=[changed_slot],
        compatibility_report=compatibility_report,
        performance_profile=performance_profile,
        explanations_vi=[
            (
                f"{candidate.label_vi}: thay {current_item.name} bằng "
                f"{candidate.item.name} từ catalog snapshot {catalog.snapshot_version}."
            ),
            "Biến thể đã chạy lại compatibility rules trước khi hiển thị.",
            "Giá và SKU đều lấy từ catalog snapshot hiện tại; cần kiểm tra lại link Phong Vu trước khi mua.",
        ],
        warnings_vi=warnings,
    )


def _build_items(
    base_artifact: BuildArtifact,
    selected: dict[BuildSlot, CatalogSku],
    changed_slot: BuildAlternativeChangedSlot,
) -> list[BuildItem]:
    base_explanations = {item.slot: item.explanation_vi for item in base_artifact.items}
    items = []
    for base_item in base_artifact.items:
        catalog_item = selected[base_item.slot]
        explanation = base_explanations[base_item.slot]
        if base_item.slot == changed_slot.slot:
            explanation = changed_slot.reason_vi
        items.append(
            BuildItem(
                slot=base_item.slot,
                sku=catalog_item.sku,
                name=catalog_item.name,
                category=catalog_item.category,
                price_vnd=catalog_item.price_vnd,
                url=catalog_item.url,
                brand=catalog_item.brand,
                specs_confidence=catalog_item.specs_confidence,
                explanation_vi=explanation,
            )
        )
    return items


def _next_higher_capacity(
    *,
    selected: dict[BuildSlot, CatalogSku],
    catalog_items: Iterable[CatalogSku],
    slot: BuildSlot,
    category: ComponentCategory,
    spec_key: str,
) -> CatalogSku | None:
    current = selected.get(slot)
    if current is None:
        return None
    current_value = _int_spec(current, spec_key) or 0
    options = [
        item
        for item in catalog_items
        if item.category == category
        and item.stock_quantity > 0
        and item.sku != current.sku
        and (_int_spec(item, spec_key) or 0) > current_value
    ]
    if slot == BuildSlot.RAM:
        current_memory_type = current.specs.get("memory_type")
        options = [
            item for item in options if item.specs.get("memory_type") == current_memory_type
        ]
    return min(options, key=lambda item: (_int_spec(item, spec_key) or 0, item.price_vnd, item.sku), default=None)


def _nvidia_gpu_candidate(
    selected: dict[BuildSlot, CatalogSku],
    catalog_items: Iterable[CatalogSku],
) -> CatalogSku | None:
    current = selected.get(BuildSlot.VGA)
    if current is None:
        return None
    options = [
        item
        for item in catalog_items
        if item.category == ComponentCategory.VGA
        and item.stock_quantity > 0
        and item.sku != current.sku
        and _is_nvidia_chipset(str(item.specs.get("chipset", "")))
    ]
    return min(options, key=lambda item: (item.price_vnd, item.sku), default=None)


def _item_for_slot(base_artifact: BuildArtifact, slot: BuildSlot) -> BuildItem | None:
    return next((item for item in base_artifact.items if item.slot == slot), None)


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


def _budget_warnings(
    budget_status: BudgetStatus,
    budget_max: int | None,
    budget_gap: int,
) -> list[str]:
    if budget_status == BudgetStatus.UNKNOWN_BUDGET:
        return ["Chưa có budget_max nên biến thể chưa thể chứng minh nằm trong ngân sách."]
    if budget_status == BudgetStatus.OVER_BUDGET and budget_max is not None:
        return [
            (
                f"Biến thể vượt ngân sách {_format_vnd(budget_max)} "
                f"{_format_vnd(budget_gap)} theo giá snapshot."
            )
        ]
    return []


def _int_spec(item: CatalogSku, key: str) -> int | None:
    value = item.specs.get(key)
    return value if isinstance(value, int) else None


def _is_nvidia_chipset(chipset: str) -> bool:
    normalized = chipset.casefold()
    return "rtx" in normalized or "gtx" in normalized or "nvidia" in normalized


def _format_vnd(value: int) -> str:
    return f"{value:,}".replace(",", ".") + " VND"
