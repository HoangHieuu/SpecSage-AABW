from typing import Literal

from pc_build_copilot.build_models import (
    PerformanceConfidence,
    PerformanceEvidence,
    PerformanceFitLevel,
    PerformanceProfile,
)
from pc_build_copilot.catalog_models import CatalogSku
from pc_build_copilot.compatibility_models import BuildSlot
from pc_build_copilot.models import BuildIntent, UseCase


def generate_performance_profile(
    *,
    intent: BuildIntent,
    selected_skus: dict[BuildSlot, CatalogSku],
) -> PerformanceProfile:
    facts = _facts(selected_skus, intent)
    if intent.use_case == UseCase.GAMING:
        return _gaming_profile(intent, facts)
    if intent.use_case == UseCase.CREATOR:
        return _creator_profile(intent, facts)
    if intent.use_case == UseCase.AI:
        return _ai_profile(intent, facts)
    if intent.use_case in {UseCase.OFFICE, UseCase.STUDENT}:
        return _office_profile(intent, facts)
    return _general_profile(intent, facts)


class _Facts:
    def __init__(self, selected_skus: dict[BuildSlot, CatalogSku], intent: BuildIntent) -> None:
        self.intent = intent
        self.cpu = selected_skus.get(BuildSlot.CPU)
        self.gpu = selected_skus.get(BuildSlot.VGA)
        self.ram = selected_skus.get(BuildSlot.RAM)
        self.storage = selected_skus.get(BuildSlot.STORAGE)
        self.psu = selected_skus.get(BuildSlot.PSU)

        self.cpu_cores = _int_spec(self.cpu, "cores")
        self.cpu_threads = _int_spec(self.cpu, "threads")
        self.gpu_vram_gb = _int_spec(self.gpu, "vram_gb")
        self.ram_gb = _int_spec(self.ram, "capacity_gb")
        self.storage_gb = _int_spec(self.storage, "capacity_gb")
        self.psu_wattage_w = _int_spec(self.psu, "wattage_w")
        self.storage_interface = _str_spec(self.storage, "interface")
        self.gpu_chipset = _str_spec(self.gpu, "chipset")
        self.cpu_has_igpu = self.cpu.specs.get("integrated_graphics") if self.cpu else None

    @property
    def has_discrete_gpu(self) -> bool:
        return self.gpu is not None

    @property
    def has_nvme_storage(self) -> bool:
        return bool(self.storage_interface and "nvme" in self.storage_interface.casefold())


def _facts(selected_skus: dict[BuildSlot, CatalogSku], intent: BuildIntent) -> _Facts:
    return _Facts(selected_skus, intent)


def _gaming_profile(intent: BuildIntent, facts: _Facts) -> PerformanceProfile:
    notes = []
    bottlenecks = []
    warnings = []
    fit_level = PerformanceFitLevel.ADEQUATE

    if facts.has_discrete_gpu and (facts.gpu_vram_gb or 0) >= 8:
        fit_level = PerformanceFitLevel.GOOD
        notes.append(
            "GPU rời 8GB VRAM phù hợp để ưu tiên game eSports và màn hình tần số quét cao ở mức định tính."
        )
    elif facts.has_discrete_gpu:
        notes.append("Có GPU rời, nhưng VRAM dưới 8GB nên nên giữ kỳ vọng đồ họa vừa phải.")
        bottlenecks.append("GPU/VRAM là giới hạn chính cho game nặng hoặc độ phân giải cao.")
    else:
        fit_level = PerformanceFitLevel.LIMITED
        warnings.append("Không có GPU rời nên không nên xem đây là build gaming chính.")

    if (facts.cpu_cores or 0) >= 6 and (facts.cpu_threads or 0) >= 12:
        notes.append("CPU 6 nhân 12 luồng là nền tảng hợp lý cho gaming phổ thông.")
    else:
        bottlenecks.append("CPU có thể là điểm nghẽn trong game cần nhiều luồng xử lý.")

    if (facts.ram_gb or 0) >= 16:
        notes.append("RAM 16GB đáp ứng mức khởi điểm an toàn cho gaming hiện tại.")
    else:
        fit_level = PerformanceFitLevel.LIMITED
        warnings.append("RAM dưới 16GB không phù hợp cho trải nghiệm gaming ổn định.")

    if _mentions_demanding_1440p(intent):
        warnings.append(
            "Chưa có benchmark cho game/độ phân giải này; không cam kết FPS hay mức đồ họa cụ thể."
        )

    return _profile(
        use_case="gaming",
        fit_level=fit_level,
        summary_vi=_summary(fit_level, "gaming"),
        facts=facts,
        fit_notes=notes,
        bottlenecks=bottlenecks,
        warnings=warnings,
    )


def _creator_profile(intent: BuildIntent, facts: _Facts) -> PerformanceProfile:
    notes = []
    bottlenecks = []
    warnings = []
    fit_level = PerformanceFitLevel.ADEQUATE

    if (facts.ram_gb or 0) >= 32:
        notes.append("RAM 32GB+ phù hợp hơn cho Premiere, After Effects và tác vụ nhiều layer.")
    else:
        fit_level = PerformanceFitLevel.LIMITED
        bottlenecks.append("RAM 16GB là điểm nghẽn rõ nhất cho dự án video/đồ họa nặng.")
        warnings.append("Nên nâng RAM lên 32GB trước khi xem đây là build creator ổn định.")

    if facts.has_discrete_gpu and (facts.gpu_vram_gb or 0) >= 8:
        notes.append("GPU rời 8GB VRAM hỗ trợ tốt hơn cho timeline, preview và tác vụ GPU phổ thông.")
    else:
        bottlenecks.append("VRAM/GPU có thể giới hạn hiệu năng khi render hoặc dùng hiệu ứng nặng.")

    if facts.has_nvme_storage:
        notes.append("SSD NVMe phù hợp làm ổ hệ điều hành và project/scratch cơ bản.")
    else:
        warnings.append("Không thấy SSD NVMe trong facts, cần kiểm tra lại trước workload creator.")

    return _profile(
        use_case="creator",
        fit_level=fit_level,
        summary_vi=_summary(fit_level, "creator/đồ họa"),
        facts=facts,
        fit_notes=notes,
        bottlenecks=bottlenecks,
        warnings=warnings,
    )


def _ai_profile(intent: BuildIntent, facts: _Facts) -> PerformanceProfile:
    notes = []
    bottlenecks = []
    warnings = []
    fit_level = PerformanceFitLevel.LIMITED

    if (facts.ram_gb or 0) >= 32:
        notes.append("RAM 32GB+ phù hợp hơn cho workflow AI/local LLM cơ bản.")
    else:
        bottlenecks.append("RAM dưới 32GB là giới hạn chính cho local LLM và tác vụ AI nặng.")
        warnings.append("Nên nâng RAM lên 32GB+ cho use case AI/local LLM.")

    if facts.has_discrete_gpu and (facts.gpu_vram_gb or 0) >= 12:
        fit_level = PerformanceFitLevel.GOOD
        notes.append("VRAM 12GB+ phù hợp hơn cho thử nghiệm model cục bộ nhỏ đến trung bình.")
    elif facts.has_discrete_gpu and (facts.gpu_vram_gb or 0) >= 8:
        fit_level = PerformanceFitLevel.ADEQUATE
        bottlenecks.append("VRAM 8GB chỉ nên xem là mức thử nghiệm nhẹ cho AI/local LLM.")
    else:
        bottlenecks.append("Thiếu GPU/VRAM phù hợp cho AI local.")

    if facts.gpu_chipset and not _is_nvidia_chipset(facts.gpu_chipset):
        warnings.append("Nhiều workflow AI local phổ biến tối ưu cho NVIDIA/CUDA; cần xác nhận toolchain.")

    return _profile(
        use_case="ai",
        fit_level=fit_level,
        summary_vi=_summary(fit_level, "AI/local LLM"),
        facts=facts,
        fit_notes=notes,
        bottlenecks=bottlenecks,
        warnings=warnings,
    )


def _office_profile(intent: BuildIntent, facts: _Facts) -> PerformanceProfile:
    notes = []
    bottlenecks = []
    warnings = []
    fit_level = PerformanceFitLevel.GOOD

    if (facts.ram_gb or 0) >= 16:
        notes.append("RAM 16GB đủ rộng cho văn phòng, học tập, nhiều tab và họp online.")
    else:
        fit_level = PerformanceFitLevel.ADEQUATE
        bottlenecks.append("RAM dưới 16GB có thể hạn chế khi mở nhiều tab hoặc ứng dụng cùng lúc.")

    if facts.has_nvme_storage and (facts.storage_gb or 0) >= 500:
        notes.append("SSD NVMe 500GB giúp hệ thống phản hồi nhanh và đủ cho dữ liệu cá nhân cơ bản.")
    else:
        bottlenecks.append("Dung lượng hoặc chuẩn SSD là điểm cần kiểm tra cho lưu trữ lâu dài.")

    if facts.has_discrete_gpu and facts.cpu_has_igpu is False:
        notes.append("GPU rời được giữ lại vì CPU trong snapshot không có iGPU.")
    elif facts.has_discrete_gpu:
        warnings.append("GPU rời có thể dư cho văn phòng nếu có lựa chọn CPU iGPU phù hợp hơn.")

    return _profile(
        use_case="office",
        fit_level=fit_level,
        summary_vi=_summary(fit_level, "văn phòng/học tập"),
        facts=facts,
        fit_notes=notes,
        bottlenecks=bottlenecks,
        warnings=warnings,
    )


def _general_profile(intent: BuildIntent, facts: _Facts) -> PerformanceProfile:
    return _profile(
        use_case=intent.use_case.value,
        fit_level=PerformanceFitLevel.UNKNOWN,
        summary_vi="Chưa đủ dữ liệu use case để kết luận workload fit.",
        facts=facts,
        fit_notes=["Hãy xác nhận nhu cầu chính để hệ thống đánh giá workload fit chính xác hơn."],
        bottlenecks=[],
        warnings=["Không có use case rõ ràng nên profile chỉ mang tính nhắc việc."],
    )


def _profile(
    *,
    use_case: str,
    fit_level: PerformanceFitLevel,
    summary_vi: str,
    facts: _Facts,
    fit_notes: list[str],
    bottlenecks: list[str],
    warnings: list[str],
) -> PerformanceProfile:
    return PerformanceProfile(
        use_case=use_case,
        fit_level=fit_level,
        confidence=_confidence(facts),
        summary_vi=summary_vi,
        fit_notes_vi=fit_notes,
        bottleneck_notes_vi=bottlenecks,
        warnings_vi=warnings,
        evidence=_evidence(facts),
    )


def _summary(fit_level: PerformanceFitLevel, use_case_label: str) -> str:
    if fit_level == PerformanceFitLevel.GOOD:
        return f"Phù hợp tốt cho workload {use_case_label} ở mức định tính từ catalog snapshot."
    if fit_level == PerformanceFitLevel.ADEQUATE:
        return f"Đủ dùng cho workload {use_case_label}, nhưng vẫn có điểm cần theo dõi."
    if fit_level == PerformanceFitLevel.LIMITED:
        return f"Còn hạn chế cho workload {use_case_label}; nên xem bottleneck trước khi duyệt."
    return "Chưa đủ dữ liệu để đánh giá workload fit."


def _confidence(facts: _Facts) -> PerformanceConfidence:
    required = [facts.cpu_cores, facts.cpu_threads, facts.ram_gb, facts.storage_gb]
    if facts.has_discrete_gpu:
        required.append(facts.gpu_vram_gb)
    known_count = sum(value is not None for value in required)
    if known_count == len(required):
        return PerformanceConfidence.HIGH
    if known_count >= max(2, len(required) - 1):
        return PerformanceConfidence.MEDIUM
    return PerformanceConfidence.LOW


def _evidence(facts: _Facts) -> list[PerformanceEvidence]:
    evidence = []
    _add_evidence(evidence, "CPU", _cpu_label(facts), "catalog_spec")
    _add_evidence(evidence, "GPU", _gpu_label(facts), "catalog_spec")
    _add_evidence(evidence, "RAM", _capacity_label(facts.ram_gb, "GB"), "catalog_spec")
    _add_evidence(evidence, "Storage", _storage_label(facts), "catalog_spec")
    _add_evidence(evidence, "PSU", _capacity_label(facts.psu_wattage_w, "W"), "catalog_spec")
    if facts.intent.performance_targets:
        _add_evidence(evidence, "Mục tiêu", ", ".join(facts.intent.performance_targets), "intent")
    if facts.intent.target_games:
        _add_evidence(evidence, "Game", ", ".join(facts.intent.target_games), "intent")
    if facts.intent.target_apps:
        _add_evidence(evidence, "Ứng dụng", ", ".join(facts.intent.target_apps), "intent")
    return evidence


def _add_evidence(
    evidence: list[PerformanceEvidence],
    label: str,
    value: str | None,
    source: Literal["catalog_spec", "intent", "rule"],
) -> None:
    if value:
        evidence.append(PerformanceEvidence(label=label, value=value, source=source))


def _cpu_label(facts: _Facts) -> str | None:
    if facts.cpu_cores is None and facts.cpu_threads is None:
        return None
    if facts.cpu_cores is None:
        return f"{facts.cpu_threads} luồng"
    if facts.cpu_threads is None:
        return f"{facts.cpu_cores} nhân"
    return f"{facts.cpu_cores} nhân / {facts.cpu_threads} luồng"


def _gpu_label(facts: _Facts) -> str | None:
    if not facts.gpu:
        return None
    parts = [facts.gpu_chipset or facts.gpu.name]
    if facts.gpu_vram_gb is not None:
        parts.append(f"{facts.gpu_vram_gb}GB VRAM")
    return " · ".join(parts)


def _storage_label(facts: _Facts) -> str | None:
    if facts.storage_gb is None and not facts.storage_interface:
        return None
    parts = []
    if facts.storage_gb is not None:
        parts.append(f"{facts.storage_gb}GB")
    if facts.storage_interface:
        parts.append(facts.storage_interface)
    return " ".join(parts)


def _capacity_label(value: int | None, suffix: str) -> str | None:
    if value is None:
        return None
    return f"{value}{suffix}"


def _mentions_demanding_1440p(intent: BuildIntent) -> bool:
    targets = " ".join(intent.performance_targets).casefold()
    games = " ".join(intent.target_games).casefold()
    demanding_games = ["cyberpunk", "alan wake", "starfield", "hogwarts"]
    return ("1440p" in targets or "2k" in targets) and any(game in games for game in demanding_games)


def _is_nvidia_chipset(chipset: str) -> bool:
    normalized = chipset.casefold()
    return "rtx" in normalized or "gtx" in normalized or "nvidia" in normalized


def _int_spec(item: CatalogSku | None, key: str) -> int | None:
    if not item:
        return None
    value = item.specs.get(key)
    return value if isinstance(value, int) else None


def _str_spec(item: CatalogSku | None, key: str) -> str | None:
    if not item:
        return None
    value = item.specs.get(key)
    return value if isinstance(value, str) else None
