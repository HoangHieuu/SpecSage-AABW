from __future__ import annotations

import math
import re
from collections.abc import Iterable

from pc_build_copilot.catalog_models import CatalogSku, CatalogSnapshot, ComponentCategory
from pc_build_copilot.compatibility_models import BuildSlot
from pc_build_copilot.compatibility_rules import (
    BASE_SYSTEM_POWER_W,
    GPU_CLEARANCE_WARN_MM,
    PSU_HEADROOM_FACTOR,
)
from pc_build_copilot.upgrade_models import (
    ExistingPartDecision,
    ExistingSystemOverrides,
    ExistingSystemParseRequest,
    ExistingSystemParseResponse,
    ExistingSystemSpec,
    UpgradeCheckStatus,
    UpgradeCompatibilityCheck,
    UpgradeDecision,
    UpgradeImpact,
    UpgradePlanRequest,
    UpgradePlanResponse,
    UpgradeRecommendation,
)


GPU_TIER_SCORES = {
    "rtx 5060": 80,
    "rtx 4060": 72,
    "rx 7600": 68,
    "rtx 3060": 62,
    "gtx 1660": 45,
}

CPU_TDP_BY_MODEL = {
    "i5-12400f": 65,
    "i5 12400f": 65,
    "i5-13400f": 65,
    "i5 13400f": 65,
    "i7-14700f": 65,
    "i7 14700f": 65,
    "ryzen 5 5600": 65,
    "ryzen 5 7600": 65,
    "ryzen 7 7700": 65,
}

CPU_MODEL_RE = re.compile(
    r"\b(?:i[3579][-\s]?\d{4,5}[a-z]*|ryzen\s+[3579]\s+\d{4}[a-z0-9]*)\b",
    re.IGNORECASE,
)
GPU_MODEL_RE = re.compile(
    r"\b(?:rtx\s?\d{4}|gtx\s?\d{4}|rx\s?\d{4})\b",
    re.IGNORECASE,
)
PSU_RE = re.compile(r"\b(?:psu|ngu[oồ]n)[^\d]{0,24}(\d{3,4})\s*w\b", re.IGNORECASE)
RAM_LABEL_RE = re.compile(
    r"\bram[^\d]{0,18}(?:(\d+)\s*x\s*)?(\d{1,3})\s*gb\b",
    re.IGNORECASE,
)
RAM_TRAILING_RE = re.compile(
    r"\b(?:(\d+)\s*x\s*)?(\d{1,3})\s*gb\s*(?:ram|ddr[45])\b",
    re.IGNORECASE,
)
CONNECTOR_RE = re.compile(r"\b(\d+)\s*(?:x\s*)?(?:8[-\s]?pin|pcie)\b", re.IGNORECASE)
CLEARANCE_RE = re.compile(
    r"\b(?:case|v[oỏ]\s*m[aá]y|th[uù]ng\s*m[aá]y|clearance|h[oỗ]\s*tr[oợ])"
    r"[^\d]{0,40}(\d{3})\s*mm\b",
    re.IGNORECASE,
)
STORAGE_RE = re.compile(r"\b(?:ssd|hdd|nvme)[^,.;\n]*", re.IGNORECASE)


def create_gpu_upgrade_plan(
    *,
    payload: UpgradePlanRequest,
    catalog: CatalogSnapshot,
) -> UpgradePlanResponse:
    existing = parse_existing_system(payload.current_pc)
    if payload.confirmed_existing_system is not None:
        existing = apply_existing_system_confirmation(
            parsed=existing,
            confirmation=payload.confirmed_existing_system,
        )
    recommendation = _recommend_gpu(payload=payload, catalog=catalog, existing=existing)
    reuse_decisions = _reuse_decisions(existing=existing, recommendation=recommendation)
    warnings = _response_warnings(existing=existing, recommendation=recommendation)

    return UpgradePlanResponse(
        catalog_version=catalog.snapshot_version,
        request=payload,
        existing_system=existing,
        recommendations=[recommendation] if recommendation else [],
        reuse_decisions=reuse_decisions,
        total_upgrade_cost_vnd=recommendation.price_vnd if recommendation else 0,
        warnings_vi=warnings,
        next_steps_vi=_next_steps(recommendation),
    )


def create_existing_system_parse(payload: ExistingSystemParseRequest) -> ExistingSystemParseResponse:
    existing = parse_existing_system(payload.current_pc)
    warnings = _parse_warnings(existing)
    return ExistingSystemParseResponse(
        existing_system=existing,
        summary_vi=_existing_system_summary(existing),
        warnings_vi=warnings,
        next_steps_vi=_parse_next_steps(existing),
    )


def parse_existing_system(raw_text: str) -> ExistingSystemSpec:
    text = raw_text.strip()
    text_lower = text.casefold()
    cpu_name = _first_match(CPU_MODEL_RE, text)
    gpu_name = _first_match(GPU_MODEL_RE, text)
    psu_wattage = _first_int(PSU_RE, text)
    ram_gb = _parse_ram_gb(text)
    storage_summary = _first_match(STORAGE_RE, text)
    clearance = _first_int(CLEARANCE_RE, text)
    connectors = _first_int(CONNECTOR_RE, text)
    mainboard_name = _parse_mainboard(text)
    case_name = "Case hiện tại" if clearance is not None else None

    return ExistingSystemSpec(
        raw_text=text,
        cpu_name=_normalize_component_name(cpu_name),
        cpu_tdp_w=_cpu_tdp(cpu_name),
        mainboard_name=mainboard_name,
        ram_gb=ram_gb,
        gpu_name=_normalize_component_name(gpu_name),
        gpu_tier_score=_gpu_tier_score(gpu_name),
        psu_wattage_w=psu_wattage,
        psu_pcie_8pin_connectors=connectors if "pin" in text_lower or "pcie" in text_lower else None,
        case_name=case_name,
        case_gpu_clearance_mm=clearance,
        storage_summary=_normalize_storage(storage_summary),
        unknown_fields=_unknown_fields(
            cpu_name=cpu_name,
            mainboard_name=mainboard_name,
            ram_gb=ram_gb,
            gpu_name=gpu_name,
            psu_wattage_w=psu_wattage,
            case_gpu_clearance_mm=clearance,
            storage_summary=storage_summary,
        ),
    )


def apply_existing_system_confirmation(
    *,
    parsed: ExistingSystemSpec,
    confirmation: ExistingSystemOverrides,
) -> ExistingSystemSpec:
    values = parsed.model_dump()
    updates = confirmation.model_dump(exclude_unset=True)
    values.update(updates)

    cpu_name = _normalize_component_name(values.get("cpu_name"))
    gpu_name = _normalize_component_name(values.get("gpu_name"))
    mainboard_name = _normalize_mainboard_name(values.get("mainboard_name"))
    ram_gb = values.get("ram_gb")
    psu_wattage = values.get("psu_wattage_w")
    pcie_connectors = values.get("psu_pcie_8pin_connectors")
    case_clearance = values.get("case_gpu_clearance_mm")
    storage_summary = _normalize_storage(values.get("storage_summary"))

    return ExistingSystemSpec(
        raw_text=parsed.raw_text,
        cpu_name=cpu_name,
        cpu_tdp_w=_cpu_tdp(cpu_name),
        mainboard_name=mainboard_name,
        ram_gb=ram_gb,
        gpu_name=gpu_name,
        gpu_tier_score=_gpu_tier_score(gpu_name),
        psu_wattage_w=psu_wattage,
        psu_pcie_8pin_connectors=pcie_connectors,
        case_name="Case hiện tại" if case_clearance is not None else None,
        case_gpu_clearance_mm=case_clearance,
        storage_summary=storage_summary,
        unknown_fields=_unknown_fields(
            cpu_name=cpu_name,
            mainboard_name=mainboard_name,
            ram_gb=ram_gb,
            gpu_name=gpu_name,
            psu_wattage_w=psu_wattage,
            case_gpu_clearance_mm=case_clearance,
            storage_summary=storage_summary,
        ),
    )


def _recommend_gpu(
    *,
    payload: UpgradePlanRequest,
    catalog: CatalogSnapshot,
    existing: ExistingSystemSpec,
) -> UpgradeRecommendation | None:
    candidates = [
        item
        for item in catalog.items
        if item.category == ComponentCategory.VGA
        and item.stock_quantity > 0
        and (
            payload.upgrade_budget_max_vnd is None
            or item.price_vnd <= payload.upgrade_budget_max_vnd
        )
    ]
    if existing.gpu_tier_score is not None:
        candidates = [
            item for item in candidates if _gpu_tier_score(str(item.specs.get("chipset", item.name))) > existing.gpu_tier_score
        ]
    if not candidates:
        return None

    candidate = max(
        candidates,
        key=lambda item: (
            _gpu_tier_score(str(item.specs.get("chipset", item.name))),
            int(item.specs.get("vram_gb", 0)),
            -item.price_vnd,
            item.sku,
        ),
    )
    checks = _gpu_upgrade_checks(existing=existing, candidate=candidate)
    compatibility_status = _max_check_status(checks)
    warnings = [
        check.explanation_vi
        for check in checks
        if check.status in {UpgradeCheckStatus.WARN, UpgradeCheckStatus.BLOCK}
    ]

    return UpgradeRecommendation(
        sku=candidate.sku,
        name=candidate.name,
        category=candidate.category,
        price_vnd=candidate.price_vnd,
        url=candidate.url,
        brand=candidate.brand,
        specs_confidence=candidate.specs_confidence,
        impact=_impact(existing.gpu_tier_score, _gpu_tier_score(str(candidate.specs.get("chipset", candidate.name)))),
        replaced_component=existing.gpu_name,
        compatibility_status=compatibility_status,
        checks=checks,
        reasons_vi=_recommendation_reasons(existing=existing, candidate=candidate),
        warnings_vi=warnings,
    )


def _gpu_upgrade_checks(
    *,
    existing: ExistingSystemSpec,
    candidate: CatalogSku,
) -> list[UpgradeCompatibilityCheck]:
    return [
        _psu_wattage_check(existing=existing, candidate=candidate),
        _psu_connector_check(existing=existing, candidate=candidate),
        _case_clearance_check(existing=existing, candidate=candidate),
    ]


def _psu_wattage_check(
    *,
    existing: ExistingSystemSpec,
    candidate: CatalogSku,
) -> UpgradeCompatibilityCheck:
    candidate_tdp = _int_spec(candidate, "tdp_w")
    cpu_tdp = existing.cpu_tdp_w
    if existing.psu_wattage_w is None or candidate_tdp is None or cpu_tdp is None:
        return UpgradeCompatibilityCheck(
            code="UPGRADE_PSU_INPUT_UNKNOWN",
            status=UpgradeCheckStatus.WARN,
            explanation_vi=(
                "Chưa đủ dữ liệu PSU hoặc CPU TDP để kết luận nguồn hiện tại; cần kiểm tra tem nguồn trước khi mua GPU."
            ),
            facts={
                "psu_wattage_w": existing.psu_wattage_w,
                "cpu_tdp_w": cpu_tdp,
                "gpu_tdp_w": candidate_tdp,
            },
        )

    required_wattage = math.ceil((cpu_tdp + candidate_tdp + BASE_SYSTEM_POWER_W) * PSU_HEADROOM_FACTOR)
    if existing.psu_wattage_w < required_wattage:
        return UpgradeCompatibilityCheck(
            code="UPGRADE_PSU_WATTAGE_TOO_LOW",
            status=UpgradeCheckStatus.BLOCK,
            explanation_vi=(
                f"Nguồn hiện tại {existing.psu_wattage_w}W thấp hơn mức khuyến nghị "
                f"{required_wattage}W cho GPU mới."
            ),
            facts={
                "psu_wattage_w": existing.psu_wattage_w,
                "required_wattage_w": required_wattage,
                "cpu_tdp_w": cpu_tdp,
                "gpu_tdp_w": candidate_tdp,
            },
        )
    return UpgradeCompatibilityCheck(
        code="UPGRADE_PSU_WATTAGE_OK",
        status=UpgradeCheckStatus.PASS,
        explanation_vi=(
            f"Nguồn hiện tại {existing.psu_wattage_w}W đạt mức khuyến nghị {required_wattage}W cho GPU mới."
        ),
        facts={
            "psu_wattage_w": existing.psu_wattage_w,
            "required_wattage_w": required_wattage,
            "cpu_tdp_w": cpu_tdp,
            "gpu_tdp_w": candidate_tdp,
        },
    )


def _psu_connector_check(
    *,
    existing: ExistingSystemSpec,
    candidate: CatalogSku,
) -> UpgradeCompatibilityCheck:
    required_8pin = _required_8pin_connectors(candidate)
    if existing.psu_pcie_8pin_connectors is None:
        return UpgradeCompatibilityCheck(
            code="UPGRADE_GPU_POWER_CONNECTOR_UNKNOWN",
            status=UpgradeCheckStatus.WARN,
            explanation_vi="Chưa rõ số đầu PCIe 8-pin của PSU hiện tại; cần xác nhận trước khi lắp GPU.",
            facts={
                "gpu_required_pcie_8pin": required_8pin,
                "psu_available_pcie_8pin": None,
            },
        )
    if existing.psu_pcie_8pin_connectors < required_8pin:
        return UpgradeCompatibilityCheck(
            code="UPGRADE_GPU_POWER_CONNECTOR_MISSING",
            status=UpgradeCheckStatus.BLOCK,
            explanation_vi=(
                f"GPU mới cần {required_8pin} đầu PCIe 8-pin nhưng PSU hiện tại chỉ khai báo "
                f"{existing.psu_pcie_8pin_connectors} đầu."
            ),
            facts={
                "gpu_required_pcie_8pin": required_8pin,
                "psu_available_pcie_8pin": existing.psu_pcie_8pin_connectors,
            },
        )
    return UpgradeCompatibilityCheck(
        code="UPGRADE_GPU_POWER_CONNECTOR_OK",
        status=UpgradeCheckStatus.PASS,
        explanation_vi="PSU hiện tại đủ đầu cấp nguồn PCIe cho GPU mới.",
        facts={
            "gpu_required_pcie_8pin": required_8pin,
            "psu_available_pcie_8pin": existing.psu_pcie_8pin_connectors,
        },
    )


def _case_clearance_check(
    *,
    existing: ExistingSystemSpec,
    candidate: CatalogSku,
) -> UpgradeCompatibilityCheck:
    gpu_length = _int_spec(candidate, "length_mm")
    if existing.case_gpu_clearance_mm is None or gpu_length is None:
        return UpgradeCompatibilityCheck(
            code="UPGRADE_CASE_CLEARANCE_UNKNOWN",
            status=UpgradeCheckStatus.WARN,
            explanation_vi="Chưa đủ dữ liệu chiều dài GPU hoặc khoảng trống case; cần đo case trước khi mua.",
            facts={
                "gpu_length_mm": gpu_length,
                "case_clearance_mm": existing.case_gpu_clearance_mm,
            },
        )
    margin = existing.case_gpu_clearance_mm - gpu_length
    if margin < 0:
        return UpgradeCompatibilityCheck(
            code="UPGRADE_GPU_CASE_CLEARANCE_BLOCK",
            status=UpgradeCheckStatus.BLOCK,
            explanation_vi=(
                f"GPU dài {gpu_length}mm vượt khoảng trống case hiện tại {existing.case_gpu_clearance_mm}mm."
            ),
            facts={
                "gpu_length_mm": gpu_length,
                "case_clearance_mm": existing.case_gpu_clearance_mm,
                "margin_mm": margin,
            },
        )
    if margin < GPU_CLEARANCE_WARN_MM:
        return UpgradeCompatibilityCheck(
            code="UPGRADE_GPU_CASE_CLEARANCE_TIGHT",
            status=UpgradeCheckStatus.WARN,
            explanation_vi=f"GPU vừa case nhưng chỉ dư {margin}mm; nên kiểm tra thực tế khi lắp.",
            facts={
                "gpu_length_mm": gpu_length,
                "case_clearance_mm": existing.case_gpu_clearance_mm,
                "margin_mm": margin,
            },
        )
    return UpgradeCompatibilityCheck(
        code="UPGRADE_GPU_CASE_CLEARANCE_OK",
        status=UpgradeCheckStatus.PASS,
        explanation_vi=f"Case hiện tại dư {margin}mm cho chiều dài GPU mới.",
        facts={
            "gpu_length_mm": gpu_length,
            "case_clearance_mm": existing.case_gpu_clearance_mm,
            "margin_mm": margin,
        },
    )


def _reuse_decisions(
    *,
    existing: ExistingSystemSpec,
    recommendation: UpgradeRecommendation | None,
) -> list[ExistingPartDecision]:
    decisions = [
        ExistingPartDecision(
            slot=BuildSlot.VGA,
            decision=UpgradeDecision.REPLACE if recommendation else UpgradeDecision.UNKNOWN,
            reason_vi=(
                f"Đổi GPU hiện tại {existing.gpu_name} sang SKU đề xuất."
                if recommendation and existing.gpu_name
                else "Chưa đủ dữ liệu GPU hiện tại để xác định mức nâng cấp."
            ),
        ),
        ExistingPartDecision(
            slot=BuildSlot.CPU,
            decision=UpgradeDecision.REUSE if existing.cpu_name else UpgradeDecision.UNKNOWN,
            reason_vi=(
                "Giữ CPU hiện tại cho bước nâng GPU đầu tiên; CPU chỉ dùng để tính nguồn khuyến nghị."
                if existing.cpu_name
                else "Chưa rõ CPU nên cần xác nhận trước khi kết luận nguồn."
            ),
        ),
        ExistingPartDecision(
            slot=BuildSlot.RAM,
            decision=(
                UpgradeDecision.REUSE
                if existing.ram_gb and existing.ram_gb >= 16
                else UpgradeDecision.OPTIONAL_UPGRADE
                if existing.ram_gb
                else UpgradeDecision.UNKNOWN
            ),
            reason_vi=_ram_decision_reason(existing.ram_gb),
        ),
    ]
    decisions.extend(_psu_case_decisions(recommendation))
    decisions.append(
        ExistingPartDecision(
            slot=BuildSlot.STORAGE,
            decision=UpgradeDecision.REUSE if existing.storage_summary else UpgradeDecision.UNKNOWN,
            reason_vi=(
                "Ổ lưu trữ hiện tại không ảnh hưởng trực tiếp đến bước nâng GPU."
                if existing.storage_summary
                else "Chưa rõ ổ lưu trữ; không dùng để chặn bước nâng GPU này."
            ),
        )
    )
    return decisions


def _psu_case_decisions(
    recommendation: UpgradeRecommendation | None,
) -> list[ExistingPartDecision]:
    if recommendation is None:
        return [
            ExistingPartDecision(
                slot=BuildSlot.PSU,
                decision=UpgradeDecision.UNKNOWN,
                reason_vi="Chưa có GPU đề xuất để kiểm tra PSU.",
            ),
            ExistingPartDecision(
                slot=BuildSlot.CASE,
                decision=UpgradeDecision.UNKNOWN,
                reason_vi="Chưa có GPU đề xuất để kiểm tra case.",
            ),
        ]
    psu_checks = [check for check in recommendation.checks if "PSU" in check.code or "CONNECTOR" in check.code]
    case_checks = [check for check in recommendation.checks if "CASE" in check.code]
    return [
        ExistingPartDecision(
            slot=BuildSlot.PSU,
            decision=_decision_from_checks(psu_checks),
            reason_vi=_decision_reason_from_checks(
                psu_checks,
                "Có thể giữ PSU hiện tại cho GPU đề xuất.",
                "Nên thay hoặc xác nhận PSU trước khi mua GPU.",
            ),
        ),
        ExistingPartDecision(
            slot=BuildSlot.CASE,
            decision=_decision_from_checks(case_checks),
            reason_vi=_decision_reason_from_checks(
                case_checks,
                "Có thể giữ case hiện tại cho GPU đề xuất.",
                "Cần đo lại hoặc thay case nếu GPU không đủ khoảng trống.",
            ),
        ),
    ]


def _response_warnings(
    *,
    existing: ExistingSystemSpec,
    recommendation: UpgradeRecommendation | None,
) -> list[str]:
    warnings = []
    if existing.unknown_fields:
        warnings.append(
            "Một số thông tin máy hiện tại còn thiếu: "
            + ", ".join(existing.unknown_fields)
            + ". Các trường này được xử lý theo hướng thận trọng."
        )
    if recommendation is None:
        warnings.append("Chưa tìm được GPU trong catalog hiện tại phù hợp ngân sách và cao hơn GPU đang dùng.")
    elif recommendation.warnings_vi:
        warnings.extend(recommendation.warnings_vi)
    return warnings


def _parse_warnings(existing: ExistingSystemSpec) -> list[str]:
    if not existing.unknown_fields:
        return []
    return [
        "Một số trường chưa nhận diện được: "
        + ", ".join(existing.unknown_fields)
        + ". Cần xác nhận trước khi lập kế hoạch nâng cấp.",
    ]


def _parse_next_steps(existing: ExistingSystemSpec) -> list[str]:
    if not existing.unknown_fields:
        return ["Xác nhận cấu hình đã đúng rồi lập kế hoạch nâng GPU."]
    return [
        "Bổ sung hoặc sửa các trường còn thiếu trong phần tóm tắt cấu hình.",
        "Không dùng trường còn thiếu để kết luận pass/fail cho PSU hoặc case.",
    ]


def _existing_system_summary(existing: ExistingSystemSpec) -> str:
    known_count = 7 - len(existing.unknown_fields)
    if not existing.unknown_fields:
        return "Đã nhận diện đủ cấu hình chính để lập kế hoạch nâng GPU."
    return f"Đã nhận diện {known_count}/7 nhóm thông tin; các mục còn thiếu vẫn được giữ là unknown."


def _next_steps(recommendation: UpgradeRecommendation | None) -> list[str]:
    if recommendation is None:
        return [
            "Nới ngân sách, bổ sung thông tin GPU hiện tại, hoặc chờ catalog có thêm SKU phù hợp.",
        ]
    steps = [
        "Kiểm tra lại giá và tồn kho trên link Phong Vu trước khi mua.",
        "Xác nhận tem PSU và khoảng trống case thực tế nếu có cảnh báo dữ liệu thiếu.",
    ]
    if recommendation.compatibility_status == UpgradeCheckStatus.BLOCK:
        steps.insert(0, "Xử lý các mục bị block trước khi mua GPU.")
    return steps


def _recommendation_reasons(
    *,
    existing: ExistingSystemSpec,
    candidate: CatalogSku,
) -> list[str]:
    reasons = [
        f"SKU thuộc catalog Phong Vu hiện tại và đang có tín hiệu còn hàng.",
        f"Giá nâng cấp là {candidate.price_vnd:,} VND, chỉ tính riêng GPU.",
    ]
    chipset = str(candidate.specs.get("chipset", "")).strip()
    vram_gb = _int_spec(candidate, "vram_gb")
    if existing.gpu_name:
        reasons.insert(0, f"Đề xuất thay {existing.gpu_name} bằng {chipset or candidate.name}.")
    if vram_gb:
        reasons.append(f"GPU đề xuất có {vram_gb}GB VRAM từ thông số catalog.")
    return reasons


def _max_check_status(checks: Iterable[UpgradeCompatibilityCheck]) -> UpgradeCheckStatus:
    statuses = {check.status for check in checks}
    if UpgradeCheckStatus.BLOCK in statuses:
        return UpgradeCheckStatus.BLOCK
    if UpgradeCheckStatus.WARN in statuses:
        return UpgradeCheckStatus.WARN
    return UpgradeCheckStatus.PASS


def _decision_from_checks(checks: list[UpgradeCompatibilityCheck]) -> UpgradeDecision:
    if any(check.status == UpgradeCheckStatus.BLOCK for check in checks):
        return UpgradeDecision.REPLACE
    if any(check.status == UpgradeCheckStatus.WARN for check in checks):
        return UpgradeDecision.UNKNOWN
    return UpgradeDecision.REUSE


def _decision_reason_from_checks(
    checks: list[UpgradeCompatibilityCheck],
    pass_reason: str,
    fallback_reason: str,
) -> str:
    if all(check.status == UpgradeCheckStatus.PASS for check in checks):
        return pass_reason
    first_issue = next((check for check in checks if check.status != UpgradeCheckStatus.PASS), None)
    if first_issue is None:
        return fallback_reason
    return first_issue.explanation_vi


def _impact(current_score: int | None, candidate_score: int) -> UpgradeImpact:
    if current_score is None:
        return UpgradeImpact.MEDIUM
    delta = candidate_score - current_score
    if delta >= 15:
        return UpgradeImpact.HIGH
    if delta >= 7:
        return UpgradeImpact.MEDIUM
    return UpgradeImpact.LOW


def _ram_decision_reason(ram_gb: int | None) -> str:
    if ram_gb is None:
        return "Chưa rõ RAM hiện tại; không dùng để chặn bước nâng GPU này."
    if ram_gb >= 16:
        return f"RAM {ram_gb}GB đủ cho bước nâng GPU đầu tiên."
    return f"RAM {ram_gb}GB có thể giữ tạm, nhưng nên nâng nếu chơi game hoặc làm việc nặng."


def _required_8pin_connectors(item: CatalogSku) -> int:
    connectors = " ".join(map(str, item.specs.get("power_connectors", []))).casefold()
    match = re.search(r"(\d+)x8[-\s]?pin", connectors)
    if match:
        return int(match.group(1))
    if "8-pin" in connectors or "8 pin" in connectors:
        return 1
    return 0


def _gpu_tier_score(name: str | None) -> int:
    if not name:
        return 0
    normalized = name.casefold().replace("-", " ")
    for token, score in GPU_TIER_SCORES.items():
        if token in normalized:
            return score
    return 0


def _cpu_tdp(name: str | None) -> int | None:
    if not name:
        return None
    normalized = name.casefold().replace(" ", "-")
    for token, tdp in CPU_TDP_BY_MODEL.items():
        if token.casefold().replace(" ", "-") in normalized:
            return tdp
    return None


def _int_spec(item: CatalogSku, key: str) -> int | None:
    value = item.specs.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_ram_gb(text: str) -> int | None:
    matches = [
        _ram_capacity_from_match(match)
        for pattern in (RAM_LABEL_RE, RAM_TRAILING_RE)
        for match in pattern.finditer(text)
    ]
    if not matches:
        return None
    return max(matches)


def _ram_capacity_from_match(match: re.Match[str]) -> int:
    stick_count = int(match.group(1) or 1)
    stick_size_gb = int(match.group(2))
    return stick_count * stick_size_gb


def _parse_mainboard(text: str) -> str | None:
    normalized = text.casefold()
    for token in ("b660", "b760", "b650", "x670", "x870", "h610", "z790"):
        if token in normalized:
            return token.upper()
    return None


def _normalize_mainboard_name(name: str | None) -> str | None:
    if not name:
        return None
    return re.sub(r"\s+", " ", name.strip()).upper()


def _unknown_fields(
    *,
    cpu_name: str | None,
    mainboard_name: str | None,
    ram_gb: int | None,
    gpu_name: str | None,
    psu_wattage_w: int | None,
    case_gpu_clearance_mm: int | None,
    storage_summary: str | None,
) -> list[str]:
    field_values = {
        "cpu": cpu_name,
        "mainboard": mainboard_name,
        "ram": ram_gb,
        "gpu": gpu_name,
        "psu": psu_wattage_w,
        "case": case_gpu_clearance_mm,
        "storage": storage_summary,
    }
    return [field for field, value in field_values.items() if value is None]


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0).strip() if match else None


def _first_int(pattern: re.Pattern[str], text: str) -> int | None:
    match = pattern.search(text)
    return int(match.group(1)) if match else None


def _normalize_component_name(name: str | None) -> str | None:
    if not name:
        return None
    return re.sub(r"\s+", " ", name.strip().upper().replace(" ", "-"))


def _normalize_storage(storage: str | None) -> str | None:
    if not storage:
        return None
    return re.sub(r"\s+", " ", storage.strip())
