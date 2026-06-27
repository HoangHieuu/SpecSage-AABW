from __future__ import annotations

import math
import re
from collections.abc import Mapping

from pc_build_copilot.catalog_models import CatalogSku, CatalogSnapshot
from pc_build_copilot.compatibility_models import (
    REQUIRED_FULL_BUILD_SLOTS,
    RULES_VERSION,
    SLOT_TO_CATEGORY,
    BuildSlot,
    CompatibilityReport,
    CompatibilityResult,
    CompatibilitySeverity,
    report_status,
)


PSU_HEADROOM_FACTOR = 1.3
BASE_SYSTEM_POWER_W = 150
GPU_CLEARANCE_WARN_MM = 20
COOLER_CLEARANCE_WARN_MM = 10


def validate_build_compatibility(
    *,
    build_id: str,
    selected_skus: Mapping[BuildSlot, str],
    catalog: CatalogSnapshot,
) -> CompatibilityReport:
    sku_index = {item.sku: item for item in catalog.items}
    selected: dict[BuildSlot, CatalogSku] = {}
    results: list[CompatibilityResult] = []

    for slot in REQUIRED_FULL_BUILD_SLOTS:
        if not selected_skus.get(slot):
            results.append(_missing_required_slot(slot))

    for slot, sku in selected_skus.items():
        item = sku_index.get(sku)
        if item is None:
            results.append(_sku_not_found(slot, sku))
            continue
        expected_category = SLOT_TO_CATEGORY[slot]
        if item.category != expected_category:
            results.append(_slot_category_mismatch(slot, sku, item.category.value))
            continue
        selected[slot] = item

    results.extend(_check_cpu_mainboard_socket(selected))
    results.extend(_check_ram_mainboard_type(selected))
    results.extend(_check_psu_capacity_and_gpu_connectors(selected))
    results.extend(_check_gpu_case_clearance(selected))
    results.extend(_check_cooler_compatibility(selected))

    if not results:
        results.append(
            CompatibilityResult(
                rule_id="COMPAT_ALL_SELECTED_RULES_PASS",
                severity=CompatibilitySeverity.PASS,
                explanation_key="compat.all_rules_pass",
                explanation_vi="Cấu hình đã qua các kiểm tra tương thích bắt buộc hiện có.",
            )
        )

    status, max_severity, can_approve = report_status(results)
    return CompatibilityReport(
        build_id=build_id,
        rules_version=RULES_VERSION,
        catalog_version=catalog.snapshot_version,
        status=status,
        max_severity=max_severity,
        can_approve=can_approve,
        selected_skus=dict(selected_skus),
        results=results,
    )


def _check_cpu_mainboard_socket(
    selected: Mapping[BuildSlot, CatalogSku]
) -> list[CompatibilityResult]:
    cpu = selected.get(BuildSlot.CPU)
    mainboard = selected.get(BuildSlot.MAINBOARD)
    if not cpu or not mainboard:
        return []

    cpu_socket = _string_spec(cpu, "socket")
    board_socket = _string_spec(mainboard, "socket")
    missing = _missing_specs(
        "COMPAT_SOCKET_SPEC_MISSING",
        [(BuildSlot.CPU, cpu, "socket"), (BuildSlot.MAINBOARD, mainboard, "socket")],
    )
    if missing:
        return missing
    if cpu_socket.casefold() != board_socket.casefold():
        return [
            CompatibilityResult(
                rule_id="COMPAT_SOCKET_MISMATCH",
                severity=CompatibilitySeverity.BLOCK,
                slots=[BuildSlot.CPU, BuildSlot.MAINBOARD],
                skus=[cpu.sku, mainboard.sku],
                explanation_key="compat.socket_mismatch",
                explanation_vi=(
                    f"CPU dùng socket {cpu_socket} nhưng mainboard hỗ trợ "
                    f"{board_socket}, nên hai linh kiện không lắp được với nhau."
                ),
                remediation_vi="Chọn CPU và mainboard cùng socket.",
                facts={"cpu_socket": cpu_socket, "mainboard_socket": board_socket},
            )
        ]
    return [
        CompatibilityResult(
            rule_id="COMPAT_SOCKET_MATCH",
            severity=CompatibilitySeverity.PASS,
            slots=[BuildSlot.CPU, BuildSlot.MAINBOARD],
            skus=[cpu.sku, mainboard.sku],
            explanation_key="compat.socket_match",
            explanation_vi=f"CPU và mainboard cùng socket {cpu_socket}.",
            facts={"socket": cpu_socket},
        )
    ]


def _check_ram_mainboard_type(
    selected: Mapping[BuildSlot, CatalogSku]
) -> list[CompatibilityResult]:
    ram = selected.get(BuildSlot.RAM)
    mainboard = selected.get(BuildSlot.MAINBOARD)
    if not ram or not mainboard:
        return []

    ram_type = _string_spec(ram, "memory_type")
    board_type = _string_spec(mainboard, "memory_type")
    missing = _missing_specs(
        "COMPAT_RAM_TYPE_SPEC_MISSING",
        [(BuildSlot.RAM, ram, "memory_type"), (BuildSlot.MAINBOARD, mainboard, "memory_type")],
    )
    if missing:
        return missing
    if ram_type.casefold() != board_type.casefold():
        return [
            CompatibilityResult(
                rule_id="COMPAT_RAM_TYPE_MISMATCH",
                severity=CompatibilitySeverity.BLOCK,
                slots=[BuildSlot.RAM, BuildSlot.MAINBOARD],
                skus=[ram.sku, mainboard.sku],
                explanation_key="compat.ram_type_mismatch",
                explanation_vi=(
                    f"RAM là {ram_type} nhưng mainboard yêu cầu {board_type}."
                ),
                remediation_vi="Chọn RAM đúng chuẩn bộ nhớ mà mainboard hỗ trợ.",
                facts={"ram_memory_type": ram_type, "mainboard_memory_type": board_type},
            )
        ]
    return [
        CompatibilityResult(
            rule_id="COMPAT_RAM_TYPE_MATCH",
            severity=CompatibilitySeverity.PASS,
            slots=[BuildSlot.RAM, BuildSlot.MAINBOARD],
            skus=[ram.sku, mainboard.sku],
            explanation_key="compat.ram_type_match",
            explanation_vi=f"RAM và mainboard cùng chuẩn {ram_type}.",
            facts={"memory_type": ram_type},
        )
    ]


def _check_psu_capacity_and_gpu_connectors(
    selected: Mapping[BuildSlot, CatalogSku]
) -> list[CompatibilityResult]:
    cpu = selected.get(BuildSlot.CPU)
    gpu = selected.get(BuildSlot.VGA)
    psu = selected.get(BuildSlot.PSU)
    if not cpu or not psu:
        return []

    results: list[CompatibilityResult] = []
    missing = _missing_specs(
        "COMPAT_PSU_SPEC_MISSING",
        [(BuildSlot.CPU, cpu, "tdp_w"), (BuildSlot.PSU, psu, "wattage_w")],
    )
    if gpu:
        missing.extend(_missing_specs("COMPAT_GPU_POWER_SPEC_MISSING", [(BuildSlot.VGA, gpu, "tdp_w")]))
    if missing:
        return missing

    cpu_tdp = _int_spec(cpu, "tdp_w")
    gpu_tdp = _int_spec(gpu, "tdp_w") if gpu else 0
    psu_wattage = _int_spec(psu, "wattage_w")
    required_wattage = math.ceil((cpu_tdp + gpu_tdp + BASE_SYSTEM_POWER_W) * PSU_HEADROOM_FACTOR)

    if psu_wattage < required_wattage:
        results.append(
            CompatibilityResult(
                rule_id="COMPAT_PSU_WATTAGE_TOO_LOW",
                severity=CompatibilitySeverity.BLOCK,
                slots=[slot for slot in (BuildSlot.CPU, BuildSlot.VGA, BuildSlot.PSU) if slot in selected],
                skus=[item.sku for item in (cpu, gpu, psu) if item is not None],
                explanation_key="compat.psu_wattage_too_low",
                explanation_vi=(
                    f"Nguồn {psu_wattage}W thấp hơn mức khuyến nghị {required_wattage}W "
                    "cho CPU/GPU và phần còn lại của hệ thống."
                ),
                remediation_vi="Chọn PSU công suất cao hơn trước khi duyệt cấu hình.",
                facts={
                    "cpu_tdp_w": cpu_tdp,
                    "gpu_tdp_w": gpu_tdp,
                    "base_system_power_w": BASE_SYSTEM_POWER_W,
                    "headroom_factor": PSU_HEADROOM_FACTOR,
                    "required_wattage_w": required_wattage,
                    "psu_wattage_w": psu_wattage,
                },
            )
        )
    else:
        results.append(
            CompatibilityResult(
                rule_id="COMPAT_PSU_WATTAGE_OK",
                severity=CompatibilitySeverity.PASS,
                slots=[BuildSlot.PSU],
                skus=[psu.sku],
                explanation_key="compat.psu_wattage_ok",
                explanation_vi=f"Nguồn {psu_wattage}W đạt mức khuyến nghị {required_wattage}W.",
                facts={"required_wattage_w": required_wattage, "psu_wattage_w": psu_wattage},
            )
        )

    if gpu:
        connector_missing = _missing_specs(
            "COMPAT_GPU_CONNECTOR_SPEC_MISSING",
            [
                (BuildSlot.VGA, gpu, "power_connectors"),
                (BuildSlot.PSU, psu, "pcie_8pin_connectors"),
            ],
        )
        if connector_missing:
            results.extend(connector_missing)
            return results

        gpu_8pin_required = _required_8pin_connectors(gpu)
        psu_8pin_available = _int_spec(psu, "pcie_8pin_connectors")
        if gpu_8pin_required > psu_8pin_available:
            results.append(
                CompatibilityResult(
                    rule_id="COMPAT_GPU_POWER_CONNECTOR_MISSING",
                    severity=CompatibilitySeverity.BLOCK,
                    slots=[BuildSlot.VGA, BuildSlot.PSU],
                    skus=[gpu.sku, psu.sku],
                    explanation_key="compat.gpu_power_connector_missing",
                    explanation_vi=(
                        f"GPU cần {gpu_8pin_required} đầu PCIe 8-pin nhưng PSU chỉ có "
                        f"{psu_8pin_available} đầu."
                    ),
                    remediation_vi="Chọn PSU có đủ đầu cấp nguồn PCIe cho GPU.",
                    facts={
                        "gpu_required_pcie_8pin": gpu_8pin_required,
                        "psu_available_pcie_8pin": psu_8pin_available,
                    },
                )
            )
        else:
            results.append(
                CompatibilityResult(
                    rule_id="COMPAT_GPU_POWER_CONNECTOR_OK",
                    severity=CompatibilitySeverity.PASS,
                    slots=[BuildSlot.VGA, BuildSlot.PSU],
                    skus=[gpu.sku, psu.sku],
                    explanation_key="compat.gpu_power_connector_ok",
                    explanation_vi="PSU có đủ đầu cấp nguồn PCIe cho GPU.",
                    facts={
                        "gpu_required_pcie_8pin": gpu_8pin_required,
                        "psu_available_pcie_8pin": psu_8pin_available,
                    },
                )
            )

    return results


def _check_gpu_case_clearance(
    selected: Mapping[BuildSlot, CatalogSku]
) -> list[CompatibilityResult]:
    gpu = selected.get(BuildSlot.VGA)
    case = selected.get(BuildSlot.CASE)
    if not gpu or not case:
        return []

    missing = _missing_specs(
        "COMPAT_GPU_CLEARANCE_SPEC_MISSING",
        [(BuildSlot.VGA, gpu, "length_mm"), (BuildSlot.CASE, case, "gpu_clearance_mm")],
    )
    if missing:
        return missing

    gpu_length = _int_spec(gpu, "length_mm")
    case_clearance = _int_spec(case, "gpu_clearance_mm")
    margin = case_clearance - gpu_length
    if margin < 0:
        return [
            CompatibilityResult(
                rule_id="COMPAT_GPU_CASE_CLEARANCE_BLOCK",
                severity=CompatibilitySeverity.BLOCK,
                slots=[BuildSlot.VGA, BuildSlot.CASE],
                skus=[gpu.sku, case.sku],
                explanation_key="compat.gpu_case_clearance_block",
                explanation_vi=(
                    f"GPU dài {gpu_length}mm vượt giới hạn case {case_clearance}mm."
                ),
                remediation_vi="Chọn case rộng hơn hoặc GPU ngắn hơn.",
                facts={"gpu_length_mm": gpu_length, "case_clearance_mm": case_clearance, "margin_mm": margin},
            )
        ]
    if margin < GPU_CLEARANCE_WARN_MM:
        return [
            CompatibilityResult(
                rule_id="COMPAT_GPU_CASE_CLEARANCE_TIGHT",
                severity=CompatibilitySeverity.WARN,
                slots=[BuildSlot.VGA, BuildSlot.CASE],
                skus=[gpu.sku, case.sku],
                explanation_key="compat.gpu_case_clearance_tight",
                explanation_vi=(
                    f"GPU vừa case nhưng chỉ dư {margin}mm, nên cần kiểm tra thực tế khi lắp."
                ),
                remediation_vi="Ưu tiên case dư ít nhất 20mm cho luồng gió và thao tác lắp đặt.",
                facts={"gpu_length_mm": gpu_length, "case_clearance_mm": case_clearance, "margin_mm": margin},
            )
        ]
    return [
        CompatibilityResult(
            rule_id="COMPAT_GPU_CASE_CLEARANCE_OK",
            severity=CompatibilitySeverity.PASS,
            slots=[BuildSlot.VGA, BuildSlot.CASE],
            skus=[gpu.sku, case.sku],
            explanation_key="compat.gpu_case_clearance_ok",
            explanation_vi=f"Case dư {margin}mm cho chiều dài GPU.",
            facts={"gpu_length_mm": gpu_length, "case_clearance_mm": case_clearance, "margin_mm": margin},
        )
    ]


def _check_cooler_compatibility(
    selected: Mapping[BuildSlot, CatalogSku]
) -> list[CompatibilityResult]:
    cooler = selected.get(BuildSlot.COOLER)
    if not cooler:
        return []

    cpu = selected.get(BuildSlot.CPU)
    case = selected.get(BuildSlot.CASE)
    results: list[CompatibilityResult] = []

    if cpu:
        cpu_socket = _string_spec(cpu, "socket")
        supported_sockets = [str(value).casefold() for value in cooler.specs.get("socket_support", [])]
        if not supported_sockets:
            results.append(_missing_spec(BuildSlot.COOLER, cooler, "socket_support", "COMPAT_COOLER_SPEC_MISSING"))
        elif cpu_socket.casefold() not in supported_sockets:
            results.append(
                CompatibilityResult(
                    rule_id="COMPAT_COOLER_SOCKET_UNSUPPORTED",
                    severity=CompatibilitySeverity.BLOCK,
                    slots=[BuildSlot.CPU, BuildSlot.COOLER],
                    skus=[cpu.sku, cooler.sku],
                    explanation_key="compat.cooler_socket_unsupported",
                    explanation_vi=f"Tản nhiệt không hỗ trợ socket {cpu_socket} của CPU.",
                    remediation_vi="Chọn tản nhiệt hỗ trợ đúng socket CPU.",
                    facts={"cpu_socket": cpu_socket, "cooler_socket_support": cooler.specs.get("socket_support", [])},
                )
            )
        else:
            results.append(
                CompatibilityResult(
                    rule_id="COMPAT_COOLER_SOCKET_OK",
                    severity=CompatibilitySeverity.PASS,
                    slots=[BuildSlot.CPU, BuildSlot.COOLER],
                    skus=[cpu.sku, cooler.sku],
                    explanation_key="compat.cooler_socket_ok",
                    explanation_vi=f"Tản nhiệt hỗ trợ socket {cpu_socket}.",
                    facts={"cpu_socket": cpu_socket},
                )
            )

        cpu_tdp = _int_spec(cpu, "tdp_w")
        cooler_tdp = _int_spec(cooler, "tdp_rating_w")
        if not cooler_tdp:
            results.append(_missing_spec(BuildSlot.COOLER, cooler, "tdp_rating_w", "COMPAT_COOLER_SPEC_MISSING"))
        elif cooler_tdp < cpu_tdp:
            results.append(
                CompatibilityResult(
                    rule_id="COMPAT_COOLER_TDP_TOO_LOW",
                    severity=CompatibilitySeverity.BLOCK,
                    slots=[BuildSlot.CPU, BuildSlot.COOLER],
                    skus=[cpu.sku, cooler.sku],
                    explanation_key="compat.cooler_tdp_too_low",
                    explanation_vi=f"Tản nhiệt chịu {cooler_tdp}W thấp hơn CPU {cpu_tdp}W.",
                    remediation_vi="Chọn tản nhiệt có mức TDP cao hơn CPU.",
                    facts={"cpu_tdp_w": cpu_tdp, "cooler_tdp_rating_w": cooler_tdp},
                )
            )

    if case:
        cooler_height = _int_spec(cooler, "height_mm")
        max_height = _int_spec(case, "max_cooler_height_mm")
        if not cooler_height or not max_height:
            results.extend(
                _missing_specs(
                    "COMPAT_COOLER_CLEARANCE_SPEC_MISSING",
                    [(BuildSlot.COOLER, cooler, "height_mm"), (BuildSlot.CASE, case, "max_cooler_height_mm")],
                )
            )
        else:
            margin = max_height - cooler_height
            if margin < 0:
                results.append(
                    CompatibilityResult(
                        rule_id="COMPAT_COOLER_CASE_CLEARANCE_BLOCK",
                        severity=CompatibilitySeverity.BLOCK,
                        slots=[BuildSlot.COOLER, BuildSlot.CASE],
                        skus=[cooler.sku, case.sku],
                        explanation_key="compat.cooler_case_clearance_block",
                        explanation_vi=f"Tản nhiệt cao {cooler_height}mm vượt giới hạn case {max_height}mm.",
                        remediation_vi="Chọn case cao hơn hoặc tản nhiệt thấp hơn.",
                        facts={"cooler_height_mm": cooler_height, "case_max_height_mm": max_height, "margin_mm": margin},
                    )
                )
            elif margin < COOLER_CLEARANCE_WARN_MM:
                results.append(
                    CompatibilityResult(
                        rule_id="COMPAT_COOLER_CASE_CLEARANCE_TIGHT",
                        severity=CompatibilitySeverity.WARN,
                        slots=[BuildSlot.COOLER, BuildSlot.CASE],
                        skus=[cooler.sku, case.sku],
                        explanation_key="compat.cooler_case_clearance_tight",
                        explanation_vi=f"Tản nhiệt vừa case nhưng chỉ dư {margin}mm.",
                        remediation_vi="Ưu tiên case dư ít nhất 10mm cho nắp hông và thao tác lắp.",
                        facts={"cooler_height_mm": cooler_height, "case_max_height_mm": max_height, "margin_mm": margin},
                    )
                )
            else:
                results.append(
                    CompatibilityResult(
                        rule_id="COMPAT_COOLER_CASE_CLEARANCE_OK",
                        severity=CompatibilitySeverity.PASS,
                        slots=[BuildSlot.COOLER, BuildSlot.CASE],
                        skus=[cooler.sku, case.sku],
                        explanation_key="compat.cooler_case_clearance_ok",
                        explanation_vi=f"Case dư {margin}mm cho chiều cao tản nhiệt.",
                        facts={"cooler_height_mm": cooler_height, "case_max_height_mm": max_height, "margin_mm": margin},
                    )
                )

    return results


def _missing_required_slot(slot: BuildSlot) -> CompatibilityResult:
    return CompatibilityResult(
        rule_id="COMPAT_REQUIRED_SLOT_MISSING",
        severity=CompatibilitySeverity.BLOCK,
        slots=[slot],
        explanation_key="compat.required_slot_missing",
        explanation_vi=f"Cấu hình thiếu linh kiện bắt buộc ở slot {slot.value}.",
        remediation_vi="Bổ sung đủ CPU, mainboard, RAM, storage, PSU và case trước khi duyệt.",
        facts={"slot": slot.value},
    )


def _sku_not_found(slot: BuildSlot, sku: str) -> CompatibilityResult:
    return CompatibilityResult(
        rule_id="CATALOG_SKU_NOT_FOUND",
        severity=CompatibilitySeverity.BLOCK,
        slots=[slot],
        skus=[sku],
        explanation_key="compat.catalog_sku_not_found",
        explanation_vi=f"SKU {sku} không có trong catalog snapshot hiện tại.",
        remediation_vi="Chọn SKU từ catalog snapshot trước khi kiểm tra tương thích.",
        facts={"slot": slot.value, "sku": sku},
    )


def _slot_category_mismatch(slot: BuildSlot, sku: str, actual_category: str) -> CompatibilityResult:
    return CompatibilityResult(
        rule_id="COMPAT_SLOT_CATEGORY_MISMATCH",
        severity=CompatibilitySeverity.BLOCK,
        slots=[slot],
        skus=[sku],
        explanation_key="compat.slot_category_mismatch",
        explanation_vi=f"SKU {sku} thuộc nhóm {actual_category}, không đúng slot {slot.value}.",
        remediation_vi="Đặt SKU vào đúng slot linh kiện.",
        facts={"slot": slot.value, "sku": sku, "actual_category": actual_category},
    )


def _missing_specs(
    rule_id: str,
    fields: list[tuple[BuildSlot, CatalogSku, str]],
) -> list[CompatibilityResult]:
    return [
        _missing_spec(slot, item, field, rule_id)
        for slot, item, field in fields
        if item.specs.get(field) in (None, "", [])
    ]


def _missing_spec(slot: BuildSlot, item: CatalogSku, field: str, rule_id: str) -> CompatibilityResult:
    return CompatibilityResult(
        rule_id=rule_id,
        severity=CompatibilitySeverity.BLOCK,
        slots=[slot],
        skus=[item.sku],
        explanation_key="compat.required_spec_missing",
        explanation_vi=f"SKU {item.sku} thiếu thông số bắt buộc specs.{field}.",
        remediation_vi="Bổ sung spec đã kiểm chứng trong override catalog trước khi dùng SKU này.",
        facts={"slot": slot.value, "sku": item.sku, "field": f"specs.{field}"},
    )


def _string_spec(item: CatalogSku, field: str) -> str:
    value = item.specs.get(field)
    return str(value).strip() if value is not None else ""


def _int_spec(item: CatalogSku | None, field: str) -> int:
    if item is None:
        return 0
    value = item.specs.get(field)
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        digits = re.sub(r"\D", "", value)
        return int(digits) if digits else 0
    return 0


def _required_8pin_connectors(gpu: CatalogSku) -> int:
    connectors = gpu.specs.get("power_connectors", [])
    if isinstance(connectors, str):
        connectors = [connectors]
    total = 0
    for connector in connectors:
        text = str(connector).casefold()
        if "8" not in text:
            continue
        match = re.search(r"(\d+)\s*x?\s*8", text)
        total += int(match.group(1)) if match else 1
    return total
