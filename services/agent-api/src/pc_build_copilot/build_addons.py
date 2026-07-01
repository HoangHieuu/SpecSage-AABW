from __future__ import annotations

import re
from collections.abc import Iterable

from pc_build_copilot.build_models import BuildAddOnKind, BuildRecommendedAddOn
from pc_build_copilot.catalog_models import CatalogSku, CatalogSnapshot, ComponentCategory
from pc_build_copilot.compatibility_models import BuildSlot
from pc_build_copilot.models import BuildIntent, UseCase


HZ_RE = re.compile(r"\b(\d{2,3})\s*(?:hz|fps)\b", re.IGNORECASE)


def recommend_build_addons(
    *,
    intent: BuildIntent,
    catalog: CatalogSnapshot,
    selected: dict[BuildSlot, CatalogSku],
) -> list[BuildRecommendedAddOn]:
    addons: list[BuildRecommendedAddOn] = []
    monitor = _recommend_monitor(intent=intent, catalog_items=catalog.items)
    if monitor is not None:
        addons.append(monitor)

    cooler = _recommend_cooler(
        intent=intent,
        catalog_items=catalog.items,
        selected=selected,
    )
    if cooler is not None:
        addons.append(cooler)

    return addons


def _recommend_monitor(
    *,
    intent: BuildIntent,
    catalog_items: Iterable[CatalogSku],
) -> BuildRecommendedAddOn | None:
    if not _wants_monitor(intent):
        return None

    monitors = [
        item
        for item in catalog_items
        if item.category == ComponentCategory.MONITOR and item.stock_quantity > 0
    ]
    if not monitors:
        return None

    resolution_target = _target_resolution(intent)
    refresh_target = _target_refresh_hz(intent)
    selected = min(
        monitors,
        key=lambda item: _monitor_rank(
            item,
            intent=intent,
            resolution_target=resolution_target,
            refresh_target=refresh_target,
        ),
    )

    resolution = str(selected.specs.get("resolution", "chưa rõ"))
    refresh_hz = _int_spec(selected, "refresh_rate_hz")
    fit_notes = [
        f"Độ phân giải snapshot: {resolution}.",
        (
            f"Tần số quét snapshot: {refresh_hz}Hz."
            if refresh_hz is not None
            else "Tần số quét snapshot chưa rõ."
        ),
    ]
    warnings = []
    if refresh_target is not None and (refresh_hz is None or refresh_hz < refresh_target):
        warnings.append(
            f"Màn hình này thấp hơn mục tiêu {refresh_target}Hz; ưu tiên độ phân giải theo yêu cầu."
        )

    return BuildRecommendedAddOn(
        kind=BuildAddOnKind.MONITOR,
        sku=selected.sku,
        name=selected.name,
        category=selected.category,
        price_vnd=selected.price_vnd,
        url=selected.url,
        image_url=selected.image_url,
        brand=selected.brand,
        warranty_text=selected.warranty_text,
        stock_status=selected.stock_status,
        stock_quantity=selected.stock_quantity,
        specs_confidence=selected.specs_confidence,
        reason_vi=_monitor_reason(intent, resolution_target, refresh_target),
        fit_notes_vi=fit_notes,
        warnings_vi=warnings,
    )


def _recommend_cooler(
    *,
    intent: BuildIntent,
    catalog_items: Iterable[CatalogSku],
    selected: dict[BuildSlot, CatalogSku],
) -> BuildRecommendedAddOn | None:
    if not _wants_cooler(intent):
        return None

    cpu = selected.get(BuildSlot.CPU)
    case = selected.get(BuildSlot.CASE)
    if cpu is None:
        return None

    coolers = [
        item
        for item in catalog_items
        if item.category == ComponentCategory.COOLER and item.stock_quantity > 0
    ]
    compatible = [
        item
        for item in coolers
        if _cooler_fits_cpu_and_case(item, cpu=cpu, case=case)
    ]
    if not compatible:
        return None

    wants_aio = _mentions_any(intent, ["aio", "tản nhiệt nước", "tan nhiet nuoc", "water"])
    quiet = _is_quiet_request(intent)
    selected_cooler = min(
        compatible,
        key=lambda item: _cooler_rank(
            item,
            cpu=cpu,
            wants_aio=wants_aio,
            quiet=quiet,
        ),
    )

    cpu_socket = str(cpu.specs.get("socket", "chưa rõ"))
    cpu_tdp = _int_spec(cpu, "tdp_w")
    cooler_tdp = _int_spec(selected_cooler, "tdp_rating_w")
    cooler_height = _int_spec(selected_cooler, "height_mm")
    case_height = _int_spec(case, "max_cooler_height_mm") if case else None
    fit_notes = [
        f"Hỗ trợ socket CPU {cpu_socket}.",
    ]
    if cpu_tdp is not None and cooler_tdp is not None:
        fit_notes.append(f"TDP tản nhiệt {cooler_tdp}W cho CPU {cpu_tdp}W.")
    if cooler_height is not None and case_height is not None:
        fit_notes.append(f"Cao {cooler_height}mm, nằm trong giới hạn case {case_height}mm.")

    return BuildRecommendedAddOn(
        kind=BuildAddOnKind.COOLER,
        sku=selected_cooler.sku,
        name=selected_cooler.name,
        category=selected_cooler.category,
        price_vnd=selected_cooler.price_vnd,
        url=selected_cooler.url,
        image_url=selected_cooler.image_url,
        brand=selected_cooler.brand,
        warranty_text=selected_cooler.warranty_text,
        stock_status=selected_cooler.stock_status,
        stock_quantity=selected_cooler.stock_quantity,
        specs_confidence=selected_cooler.specs_confidence,
        reason_vi=_cooler_reason(intent, selected_cooler),
        fit_notes_vi=fit_notes,
    )


def _wants_monitor(intent: BuildIntent) -> bool:
    if intent.monitor_count is not None or "monitor" in intent.mentioned_components:
        return True
    text = _intent_text(intent)
    if any(term in text for term in ["màn hình", "man hinh", "monitor", "display"]):
        return True
    return _target_resolution(intent) is not None and _target_refresh_hz(intent) is not None


def _wants_cooler(intent: BuildIntent) -> bool:
    if "cooler" in intent.mentioned_components:
        return True
    text = _intent_text(intent)
    return _is_quiet_request(intent) or any(
        term in text
        for term in [
            "tản nhiệt",
            "tan nhiet",
            "cooler",
            "aio",
            "im lặng",
            "im lang",
            "êm",
            "quiet",
        ]
    )


def _target_resolution(intent: BuildIntent) -> str | None:
    text = _intent_text(intent)
    if any(term in text for term in ["3840x2160", "2160p", "4k", "uhd"]):
        return "3840x2160"
    if any(term in text for term in ["2560x1440", "1440p", "2k", "qhd"]):
        return "2560x1440"
    if any(term in text for term in ["1920x1080", "1080p", "fhd", "full hd"]):
        return "1920x1080"
    return None


def _target_refresh_hz(intent: BuildIntent) -> int | None:
    matches = [int(match.group(1)) for match in HZ_RE.finditer(_intent_text(intent))]
    if not matches:
        return None
    return max(matches)


def _monitor_rank(
    item: CatalogSku,
    *,
    intent: BuildIntent,
    resolution_target: str | None,
    refresh_target: int | None,
) -> tuple[int, int, int, int, str]:
    resolution = str(item.specs.get("resolution", ""))
    refresh_hz = _int_spec(item, "refresh_rate_hz") or 0
    resolution_penalty = _resolution_penalty(resolution, resolution_target)
    if refresh_target is None:
        refresh_penalty = -refresh_hz if intent.use_case == UseCase.GAMING else 0
        refresh_overage = 0
    elif refresh_hz >= refresh_target:
        refresh_penalty = 0
        refresh_overage = refresh_hz - refresh_target
    else:
        refresh_penalty = refresh_target - refresh_hz
        refresh_overage = 999
    return (
        resolution_penalty,
        refresh_penalty,
        refresh_overage,
        item.price_vnd,
        item.sku,
    )


def _resolution_penalty(resolution: str, target: str | None) -> int:
    if target is None:
        return 0
    if resolution == target:
        return 0
    current_width = _resolution_width(resolution)
    target_width = _resolution_width(target)
    if current_width is None or target_width is None:
        return 100
    if current_width > target_width:
        return 20 + ((current_width - target_width) // 100)
    return 50 + ((target_width - current_width) // 100)


def _cooler_fits_cpu_and_case(
    item: CatalogSku,
    *,
    cpu: CatalogSku,
    case: CatalogSku | None,
) -> bool:
    cpu_socket = cpu.specs.get("socket")
    socket_support = item.specs.get("socket_support")
    if cpu_socket and isinstance(socket_support, list) and cpu_socket not in socket_support:
        return False

    cpu_tdp = _int_spec(cpu, "tdp_w")
    cooler_tdp = _int_spec(item, "tdp_rating_w")
    if cpu_tdp is not None and cooler_tdp is not None and cooler_tdp < cpu_tdp:
        return False

    cooler_height = _int_spec(item, "height_mm")
    case_height = _int_spec(case, "max_cooler_height_mm") if case else None
    if cooler_height is not None and case_height is not None and cooler_height > case_height:
        return False
    return True


def _cooler_rank(
    item: CatalogSku,
    *,
    cpu: CatalogSku,
    wants_aio: bool,
    quiet: bool,
) -> tuple[int, int, int, str]:
    cooler_type = str(item.specs.get("cooler_type", ""))
    tdp_rating = _int_spec(item, "tdp_rating_w") or 0
    cpu_tdp = _int_spec(cpu, "tdp_w") or 0
    headroom = tdp_rating - cpu_tdp
    aio_penalty = 0 if (wants_aio and cooler_type.startswith("aio")) else 1 if wants_aio else 0
    quiet_penalty = 0 if not quiet or headroom >= 120 else 1
    headroom_rank = -min(headroom, 180) if quiet else 0
    return (
        aio_penalty,
        quiet_penalty,
        headroom_rank + item.price_vnd,
        item.sku,
    )


def _monitor_reason(
    intent: BuildIntent,
    resolution_target: str | None,
    refresh_target: int | None,
) -> str:
    if resolution_target and refresh_target:
        return (
            f"Gợi ý màn hình khớp mục tiêu {resolution_target} và {refresh_target}Hz "
            "để đồng bộ với nhu cầu đã nhập."
        )
    if resolution_target:
        return f"Gợi ý màn hình theo độ phân giải {resolution_target} trong nhu cầu đã nhập."
    if intent.monitor_count:
        return "Gợi ý màn hình vì nhu cầu có nhắc số lượng màn hình."
    return "Gợi ý màn hình từ catalog Phong Vu vì nhu cầu có nhắc màn hình."


def _cooler_reason(intent: BuildIntent, item: CatalogSku) -> str:
    if str(item.specs.get("cooler_type", "")).startswith("aio"):
        return "Gợi ý tản nhiệt nước vì nhu cầu có nhắc AIO/tản nhiệt nước hoặc cần thêm headroom."
    if _is_quiet_request(intent):
        return "Gợi ý tản nhiệt khí có headroom để hỗ trợ vận hành êm hơn."
    return "Gợi ý tản nhiệt CPU tương thích socket, TDP và chiều cao case trong snapshot."


def _resolution_width(resolution: str) -> int | None:
    match = re.match(r"(\d{4})x\d{3,4}", resolution)
    if not match:
        return None
    return int(match.group(1))


def _is_quiet_request(intent: BuildIntent) -> bool:
    if intent.noise_preferences:
        return True
    return _mentions_any(intent, ["ưu tiên êm", "im lặng", "im lang", "quiet"])


def _mentions_any(intent: BuildIntent, terms: list[str]) -> bool:
    text = _intent_text(intent)
    return any(term in text for term in terms)


def _intent_text(intent: BuildIntent) -> str:
    return " ".join(
        [
            intent.raw_text,
            *(intent.performance_targets or []),
            *(intent.mentioned_components or []),
            intent.noise_preferences or "",
        ]
    ).casefold()


def _int_spec(item: CatalogSku | None, key: str) -> int | None:
    if item is None:
        return None
    value = item.specs.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None
