from dataclasses import dataclass
from typing import Literal

from pc_build_copilot.build_models import (
    PerformanceBalance,
    PerformanceConfidence,
    PerformanceEvidence,
    PerformanceFitLevel,
    PerformanceProfile,
    PerformanceWorkloadProfile,
)
from pc_build_copilot.catalog_models import CatalogSku
from pc_build_copilot.compatibility_models import BuildSlot
from pc_build_copilot.models import BuildIntent, UseCase
from pc_build_copilot.performance_benchmarks import (
    GamingBenchmarkEstimate,
    extract_fps_target,
    lookup_gaming_benchmark_estimates,
)


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
    if intent.use_case == UseCase.STREAMING:
        return _streaming_profile(intent, facts)
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


@dataclass(frozen=True)
class _WorkloadSpec:
    name: str
    category: Literal["video_editing", "three_d", "photo_editing", "streaming", "local_llm"]
    ram_min_gb: int
    vram_min_gb: int
    cpu_threads_min: int
    storage_min_gb: int
    requires_nvme: bool
    preferred_nvidia: bool = False


WORKLOAD_SPECS: dict[str, _WorkloadSpec] = {
    "Adobe Premiere Pro": _WorkloadSpec(
        name="Adobe Premiere Pro",
        category="video_editing",
        ram_min_gb=32,
        vram_min_gb=8,
        cpu_threads_min=12,
        storage_min_gb=1000,
        requires_nvme=True,
    ),
    "Adobe After Effects": _WorkloadSpec(
        name="Adobe After Effects",
        category="video_editing",
        ram_min_gb=32,
        vram_min_gb=8,
        cpu_threads_min=12,
        storage_min_gb=1000,
        requires_nvme=True,
    ),
    "Blender": _WorkloadSpec(
        name="Blender",
        category="three_d",
        ram_min_gb=32,
        vram_min_gb=8,
        cpu_threads_min=12,
        storage_min_gb=1000,
        requires_nvme=True,
    ),
    "Adobe Photoshop": _WorkloadSpec(
        name="Adobe Photoshop",
        category="photo_editing",
        ram_min_gb=16,
        vram_min_gb=4,
        cpu_threads_min=8,
        storage_min_gb=500,
        requires_nvme=True,
    ),
    "OBS Studio": _WorkloadSpec(
        name="OBS Studio",
        category="streaming",
        ram_min_gb=16,
        vram_min_gb=6,
        cpu_threads_min=12,
        storage_min_gb=500,
        requires_nvme=True,
        preferred_nvidia=True,
    ),
    "Streaming": _WorkloadSpec(
        name="Streaming",
        category="streaming",
        ram_min_gb=16,
        vram_min_gb=6,
        cpu_threads_min=12,
        storage_min_gb=500,
        requires_nvme=True,
        preferred_nvidia=True,
    ),
}


def _gaming_profile(intent: BuildIntent, facts: _Facts) -> PerformanceProfile:
    notes = []
    bottlenecks = []
    warnings = []
    fit_level = PerformanceFitLevel.ADEQUATE
    benchmark_estimates = lookup_gaming_benchmark_estimates(
        target_games=intent.target_games,
        gpu_chipset=facts.gpu_chipset,
        performance_targets=intent.performance_targets,
    )

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

    if benchmark_estimates:
        notes.extend(_benchmark_notes(benchmark_estimates))
        target_fps = extract_fps_target(intent.performance_targets)
        below_target_estimates = [
            estimate
            for estimate in benchmark_estimates
            if target_fps is not None and estimate.fps_high < target_fps
        ]
        if below_target_estimates:
            fit_level = PerformanceFitLevel.LIMITED
            bottlenecks.append(
                "GPU/preset hiện tại thấp hơn mục tiêu high-refresh đã khai báo theo benchmark matrix."
            )
            warnings.extend(_below_target_warnings(below_target_estimates, target_fps))
            if _mentions_monitor(intent):
                warnings.extend(_monitor_overspec_warnings(below_target_estimates, target_fps))
    elif _mentions_demanding_1440p(intent):
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
        extra_evidence=_benchmark_evidence(benchmark_estimates),
    )


def _creator_profile(intent: BuildIntent, facts: _Facts) -> PerformanceProfile:
    notes = []
    bottlenecks = []
    warnings = []
    fit_level = PerformanceFitLevel.ADEQUATE
    workload_profiles = _workload_profiles_for_apps(intent.target_apps, facts)

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

    if workload_profiles:
        notes.extend(_workload_fit_notes(workload_profiles))
        bottlenecks.extend(_workload_bottleneck_notes(workload_profiles))
        warnings.extend(_workload_warnings(workload_profiles))
        fit_level = _worst_fit_level(fit_level, workload_profiles)

    return _profile(
        use_case="creator",
        fit_level=fit_level,
        summary_vi=_summary(fit_level, "creator/đồ họa"),
        facts=facts,
        fit_notes=notes,
        bottlenecks=bottlenecks,
        warnings=warnings,
        workload_profiles=workload_profiles,
    )


def _ai_profile(intent: BuildIntent, facts: _Facts) -> PerformanceProfile:
    notes = []
    bottlenecks = []
    warnings = []
    fit_level = PerformanceFitLevel.LIMITED
    workload_profiles = [_local_llm_workload_profile(intent, facts)]

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

    notes.extend(_workload_fit_notes(workload_profiles))
    bottlenecks.extend(_workload_bottleneck_notes(workload_profiles))
    warnings.extend(_workload_warnings(workload_profiles))
    fit_level = _worst_fit_level(fit_level, workload_profiles)

    return _profile(
        use_case="ai",
        fit_level=fit_level,
        summary_vi=_summary(fit_level, "AI/local LLM"),
        facts=facts,
        fit_notes=notes,
        bottlenecks=bottlenecks,
        warnings=warnings,
        workload_profiles=workload_profiles,
    )


def _streaming_profile(intent: BuildIntent, facts: _Facts) -> PerformanceProfile:
    notes = []
    bottlenecks = []
    warnings = []
    workload_profiles = _workload_profiles_for_apps(
        intent.target_apps or ["Streaming"],
        facts,
    )
    fit_level = _worst_fit_level(PerformanceFitLevel.ADEQUATE, workload_profiles)

    if facts.has_discrete_gpu:
        notes.append("GPU rời giúp stream ổn định hơn khi vừa chơi game vừa encode video.")
    else:
        fit_level = PerformanceFitLevel.LIMITED
        bottlenecks.append("Thiếu GPU rời có thể giới hạn stream/game đồng thời.")

    notes.extend(_workload_fit_notes(workload_profiles))
    bottlenecks.extend(_workload_bottleneck_notes(workload_profiles))
    warnings.extend(_workload_warnings(workload_profiles))

    return _profile(
        use_case="streaming",
        fit_level=fit_level,
        summary_vi=_summary(fit_level, "streaming"),
        facts=facts,
        fit_notes=notes,
        bottlenecks=bottlenecks,
        warnings=warnings,
        workload_profiles=workload_profiles,
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
        notes.append("GPU rời ở build văn phòng này là để xuất hình, không phải upsell hiệu năng.")
    elif facts.has_discrete_gpu:
        warnings.append(
            "OFFICE_DISCRETE_GPU_OPTIONAL: GPU rời có thể dư cho văn phòng nếu có lựa chọn CPU iGPU phù hợp hơn."
        )
    elif facts.cpu_has_igpu is True:
        notes.append(
            "Có thể dùng iGPU cho văn phòng để giảm chi phí, điện năng và tiếng ồn nếu mainboard có cổng xuất hình phù hợp."
        )

    if intent.noise_preferences == "quiet":
        notes.append(
            "Ưu tiên êm: cấu hình văn phòng nên hạn chế GPU dư, giữ case thoáng và kiểm tra độ ồn thực tế trước khi mua."
        )

    if intent.monitor_count and intent.monitor_count >= 2:
        if fit_level == PerformanceFitLevel.GOOD:
            fit_level = PerformanceFitLevel.ADEQUATE
        warnings.append(
            f"OFFICE_MULTI_MONITOR_OUTPUTS_UNKNOWN: Người dùng cần {intent.monitor_count} màn hình "
            "nhưng catalog chưa có dữ liệu cổng HDMI/DP trên VGA hoặc mainboard; cần kiểm tra cổng xuất hình trước khi tư vấn."
        )

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
    extra_evidence: list[PerformanceEvidence] | None = None,
    workload_profiles: list[PerformanceWorkloadProfile] | None = None,
) -> PerformanceProfile:
    balance = _balance_analysis(facts)
    if balance:
        if balance.limiting_component != "unknown":
            bottlenecks.append(_balance_bottleneck_note(balance))
        if balance.score < 65:
            warnings.append(_balance_warning(balance))

    return PerformanceProfile(
        use_case=use_case,
        fit_level=fit_level,
        confidence=_confidence(facts),
        summary_vi=summary_vi,
        fit_notes_vi=fit_notes,
        bottleneck_notes_vi=bottlenecks,
        warnings_vi=warnings,
        evidence=[*_evidence(facts), *(extra_evidence or [])],
        balance=balance,
        workload_profiles=workload_profiles or [],
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
    if facts.intent.monitor_count:
        _add_evidence(evidence, "Màn hình", f"{facts.intent.monitor_count} màn hình", "intent")
    return evidence


def _add_evidence(
    evidence: list[PerformanceEvidence],
    label: str,
    value: str | None,
    source: Literal["catalog_spec", "intent", "rule", "benchmark"],
    source_label: str | None = None,
    source_url: str | None = None,
) -> None:
    if value:
        evidence.append(
            PerformanceEvidence(
                label=label,
                value=value,
                source=source,
                source_label=source_label,
                source_url=source_url,
            )
        )


def _benchmark_notes(estimates: list[GamingBenchmarkEstimate]) -> list[str]:
    return [
        (
            f"Có benchmark source-backed cho {estimate.target_label}; "
            "xem evidence để biết FPS tham khảo."
        )
        for estimate in estimates
    ]


def _below_target_warnings(
    estimates: list[GamingBenchmarkEstimate],
    target_fps: int,
) -> list[str]:
    return [
        (
            f"PERF_BELOW_TARGET: Benchmark {estimate.target_label} thấp hơn "
            f"mục tiêu {target_fps}Hz đã khai báo; cần GPU mạnh hơn hoặc giảm preset/độ phân giải."
        )
        for estimate in estimates
    ]


def _monitor_overspec_warnings(
    estimates: list[GamingBenchmarkEstimate],
    target_fps: int,
) -> list[str]:
    return [
        (
            f"PERF_MONITOR_OVERSPEC: Màn hình {target_fps}Hz có thể vượt khả năng "
            f"của cấu hình trong {estimate.target_label} theo benchmark matrix; "
            "nên chọn màn hình refresh thấp hơn hoặc nâng GPU trước khi tư vấn SKU màn hình."
        )
        for estimate in estimates
    ]


def _benchmark_evidence(estimates: list[GamingBenchmarkEstimate]) -> list[PerformanceEvidence]:
    evidence: list[PerformanceEvidence] = []
    for estimate in estimates:
        _add_evidence(
            evidence,
            "Benchmark",
            f"{estimate.target_label}: {estimate.fps_label}",
            "benchmark",
            source_label=estimate.source_label,
            source_url=estimate.source_url,
        )
    return evidence


def _workload_profiles_for_apps(
    target_apps: list[str],
    facts: _Facts,
) -> list[PerformanceWorkloadProfile]:
    profiles = []
    for app in target_apps:
        spec = WORKLOAD_SPECS.get(app)
        if spec:
            profiles.append(_workload_profile_from_spec(spec, facts))
        elif app == "Local LLM":
            profiles.append(_local_llm_workload_profile(facts.intent, facts))
    return profiles


def _workload_profile_from_spec(
    spec: _WorkloadSpec,
    facts: _Facts,
) -> PerformanceWorkloadProfile:
    bottlenecks: list[
        Literal[
            "cpu_bound",
            "gpu_bound",
            "ram_limited",
            "storage_limited",
            "vram_limited",
            "cuda_preferred",
        ]
    ] = []
    if (facts.ram_gb or 0) < spec.ram_min_gb:
        bottlenecks.append("ram_limited")
    if not facts.has_discrete_gpu:
        bottlenecks.append("gpu_bound")
    elif (facts.gpu_vram_gb or 0) < spec.vram_min_gb:
        bottlenecks.append("vram_limited")
    if (facts.cpu_threads or 0) < spec.cpu_threads_min:
        bottlenecks.append("cpu_bound")
    if (facts.storage_gb or 0) < spec.storage_min_gb or (spec.requires_nvme and not facts.has_nvme_storage):
        bottlenecks.append("storage_limited")
    if spec.preferred_nvidia and facts.gpu_chipset and not _is_nvidia_chipset(facts.gpu_chipset):
        bottlenecks.append("cuda_preferred")

    fit_level = _workload_fit_level(bottlenecks)
    return PerformanceWorkloadProfile(
        name=spec.name,
        category=spec.category,
        fit_level=fit_level,
        bottlenecks=bottlenecks,
        requirement_summary_vi=(
            f"Khuyến nghị tối thiểu: RAM {spec.ram_min_gb}GB, VRAM {spec.vram_min_gb}GB, "
            f"CPU {spec.cpu_threads_min} luồng, SSD {'NVMe ' if spec.requires_nvme else ''}{spec.storage_min_gb}GB."
        ),
        recommendation_vi=_workload_recommendation(spec.name, fit_level, bottlenecks),
    )


def _local_llm_workload_profile(
    intent: BuildIntent,
    facts: _Facts,
) -> PerformanceWorkloadProfile:
    model_class = _llm_model_class(intent)
    thresholds = {
        "7B": {"ram": 32, "entry_vram": 8, "good_vram": 12, "ideal_vram": 16},
        "13B": {"ram": 32, "entry_vram": 12, "good_vram": 16, "ideal_vram": 24},
        "70B": {"ram": 64, "entry_vram": 48, "good_vram": 80, "ideal_vram": 120},
    }[model_class]
    bottlenecks: list[
        Literal[
            "cpu_bound",
            "gpu_bound",
            "ram_limited",
            "storage_limited",
            "vram_limited",
            "cuda_preferred",
        ]
    ] = []
    vram = facts.gpu_vram_gb or 0
    if (facts.ram_gb or 0) < thresholds["ram"]:
        bottlenecks.append("ram_limited")
    if not facts.has_discrete_gpu:
        bottlenecks.append("gpu_bound")
    elif vram < thresholds["entry_vram"]:
        bottlenecks.append("vram_limited")
    if facts.gpu_chipset and not _is_nvidia_chipset(facts.gpu_chipset):
        bottlenecks.append("cuda_preferred")
    if not facts.has_nvme_storage or (facts.storage_gb or 0) < 500:
        bottlenecks.append("storage_limited")

    if vram >= thresholds["ideal_vram"] and not bottlenecks:
        label = "ideal"
        fit_level = PerformanceFitLevel.GOOD
    elif vram >= thresholds["good_vram"] and "ram_limited" not in bottlenecks:
        label = "good"
        fit_level = PerformanceFitLevel.GOOD
    elif vram >= thresholds["entry_vram"] and "gpu_bound" not in bottlenecks:
        label = "entry"
        fit_level = PerformanceFitLevel.ADEQUATE if "ram_limited" not in bottlenecks else PerformanceFitLevel.LIMITED
    else:
        label = "below-entry"
        fit_level = PerformanceFitLevel.LIMITED

    return PerformanceWorkloadProfile(
        name=f"Local LLM {model_class}",
        category="local_llm",
        fit_level=fit_level,
        bottlenecks=bottlenecks,
        requirement_summary_vi=(
            f"{model_class}: entry {thresholds['entry_vram']}GB VRAM, "
            f"good {thresholds['good_vram']}GB, ideal {thresholds['ideal_vram']}GB; "
            f"RAM khuyến nghị {thresholds['ram']}GB+."
        ),
        recommendation_vi=(
            f"Local LLM {model_class} đang ở mức {label}; "
            "ưu tiên VRAM NVIDIA/CUDA và RAM trước khi mở rộng model."
        ),
    )


def _workload_fit_level(
    bottlenecks: list[str],
) -> PerformanceFitLevel:
    hard_bottlenecks = {"gpu_bound", "vram_limited", "ram_limited"}
    if hard_bottlenecks & set(bottlenecks):
        return PerformanceFitLevel.LIMITED
    if bottlenecks:
        return PerformanceFitLevel.ADEQUATE
    return PerformanceFitLevel.GOOD


def _workload_recommendation(
    name: str,
    fit_level: PerformanceFitLevel,
    bottlenecks: list[str],
) -> str:
    if fit_level == PerformanceFitLevel.GOOD:
        return f"{name} phù hợp tốt với cấu hình hiện tại theo ngưỡng local."
    label = _bottleneck_labels_vi(bottlenecks)
    if fit_level == PerformanceFitLevel.ADEQUATE:
        return f"{name} dùng được, nhưng nên theo dõi {label} khi dự án lớn hơn."
    return f"{name} bị giới hạn bởi {label}; nên nâng linh kiện giới hạn trước."


def _workload_fit_notes(
    profiles: list[PerformanceWorkloadProfile],
) -> list[str]:
    return [
        profile.recommendation_vi
        for profile in profiles
        if profile.fit_level in {PerformanceFitLevel.GOOD, PerformanceFitLevel.ADEQUATE}
    ]


def _workload_bottleneck_notes(
    profiles: list[PerformanceWorkloadProfile],
) -> list[str]:
    return [
        f"{profile.name}: {_bottleneck_labels_vi(profile.bottlenecks)}."
        for profile in profiles
        if profile.bottlenecks
    ]


def _workload_warnings(
    profiles: list[PerformanceWorkloadProfile],
) -> list[str]:
    warnings = []
    for profile in profiles:
        if profile.fit_level == PerformanceFitLevel.LIMITED:
            warnings.append(f"WORKLOAD_LIMITED: {profile.recommendation_vi}")
        if "cuda_preferred" in profile.bottlenecks:
            warnings.append(
                f"WORKLOAD_CUDA_PREFERRED: {profile.name} thường tối ưu hơn với NVIDIA/CUDA; "
                "cần xác nhận encoder/toolchain nếu dùng GPU khác."
            )
    return warnings


def _worst_fit_level(
    current: PerformanceFitLevel,
    profiles: list[PerformanceWorkloadProfile],
) -> PerformanceFitLevel:
    order = {
        PerformanceFitLevel.GOOD: 3,
        PerformanceFitLevel.ADEQUATE: 2,
        PerformanceFitLevel.LIMITED: 1,
        PerformanceFitLevel.UNKNOWN: 0,
    }
    result = current
    for profile in profiles:
        if order[profile.fit_level] < order[result]:
            result = profile.fit_level
    return result


def _bottleneck_labels_vi(bottlenecks: list[str]) -> str:
    labels = {
        "cpu_bound": "CPU-bound",
        "gpu_bound": "GPU-bound",
        "ram_limited": "RAM-limited",
        "storage_limited": "storage-limited",
        "vram_limited": "VRAM-limited",
        "cuda_preferred": "ưu tiên CUDA/NVIDIA",
    }
    if not bottlenecks:
        return "không có bottleneck rõ"
    return ", ".join(labels[bottleneck] for bottleneck in bottlenecks)


def _llm_model_class(intent: BuildIntent) -> Literal["7B", "13B", "70B"]:
    text = " ".join([intent.raw_text, *intent.performance_targets]).casefold()
    if "70b" in text:
        return "70B"
    if "13b" in text:
        return "13B"
    return "7B"


def _balance_analysis(facts: _Facts) -> PerformanceBalance | None:
    cpu_score = _cpu_balance_factor(facts)
    gpu_score = _gpu_balance_factor(facts)
    ram_score = _ram_balance_factor(facts)
    storage_score = _storage_balance_factor(facts)
    if None in {cpu_score, gpu_score, ram_score, storage_score}:
        return None

    factors = {
        "cpu": cpu_score or 0,
        "gpu": gpu_score or 0,
        "ram": ram_score or 0,
        "storage": storage_score or 0,
    }
    cpu_gpu_gap = abs(factors["cpu"] - factors["gpu"])
    weakest = min(factors, key=factors.get)
    score = max(
        0,
        min(
            100,
            round(
                100
                - cpu_gpu_gap * 1.15
                - max(0, 70 - factors["ram"]) * 0.45
                - max(0, 65 - factors["storage"]) * 0.25
            ),
        ),
    )
    return PerformanceBalance(
        score=score,
        interpretation_vi=_balance_interpretation(score),
        limiting_component=weakest,
        suggestions_vi=_balance_suggestions(weakest, factors, cpu_gpu_gap),
        factors=factors,
    )


def _balance_bottleneck_note(balance: PerformanceBalance) -> str:
    labels = {
        "cpu": "CPU",
        "gpu": "GPU",
        "ram": "RAM",
        "storage": "SSD",
        "unknown": "linh kiện",
    }
    return (
        f"Balance score {balance.score}/100: giới hạn đầu tiên là "
        f"{labels[balance.limiting_component]}."
    )


def _balance_warning(balance: PerformanceBalance) -> str:
    return (
        f"PERF_IMBALANCE: Balance score {balance.score}/100 cho thấy cấu hình lệch; "
        f"{balance.interpretation_vi}"
    )


def _balance_interpretation(score: int) -> str:
    if score >= 85:
        return "CPU, GPU, RAM và SSD đang cân bằng cho workload đã chọn."
    if score >= 70:
        return "Cấu hình nhìn chung cân bằng, nhưng vẫn có một điểm nên theo dõi khi nâng cấp."
    if score >= 55:
        return "Cấu hình có dấu hiệu lệch; nên nâng linh kiện giới hạn trước khi tăng linh kiện khác."
    return "Cấu hình mất cân bằng rõ; nên điều chỉnh linh kiện giới hạn trước khi duyệt."


def _balance_suggestions(
    weakest: str,
    factors: dict[str, int],
    cpu_gpu_gap: int,
) -> list[str]:
    if weakest == "cpu":
        suggestions = ["Ưu tiên CPU nhiều nhân/luồng hơn trước khi nâng GPU mạnh hơn."]
    elif weakest == "gpu":
        suggestions = ["Ưu tiên GPU/VRAM mạnh hơn trước khi tăng preset, độ phân giải hoặc refresh rate."]
    elif weakest == "ram":
        suggestions = ["Ưu tiên nâng RAM lên 32GB nếu workload có game nặng, creator hoặc AI."]
    elif weakest == "storage":
        suggestions = ["Ưu tiên SSD NVMe dung lượng lớn hơn cho game/project/scratch disk."]
    else:
        suggestions = ["Bổ sung dữ liệu cấu hình trước khi kết luận cân bằng."]

    if cpu_gpu_gap >= 30:
        suggestions.append("Chênh lệch CPU/GPU lớn; kiểm tra lại cặp CPU và GPU trước khi tư vấn.")
    elif factors["ram"] < 70:
        suggestions.append("RAM là điểm dễ nâng cấp nhất nếu người dùng muốn giữ nền tảng hiện tại.")
    return suggestions


def _cpu_balance_factor(facts: _Facts) -> int | None:
    if facts.cpu_cores is None or facts.cpu_threads is None:
        return None
    return min(100, facts.cpu_cores * 8 + facts.cpu_threads * 2)


def _gpu_balance_factor(facts: _Facts) -> int | None:
    if not facts.has_discrete_gpu:
        if facts.intent.use_case in {UseCase.OFFICE, UseCase.STUDENT} and facts.cpu_has_igpu is True:
            return 65
        return 35
    if facts.gpu_vram_gb is None:
        return None
    chipset = (facts.gpu_chipset or "").casefold()
    if "4090" in chipset or "7900 xtx" in chipset:
        base = 98
    elif "4080" in chipset or "4070" in chipset or "7800 xt" in chipset:
        base = 88
    elif "4060" in chipset or "7600" in chipset:
        base = 70
    elif "3060" in chipset or "6600" in chipset:
        base = 62
    else:
        base = 55
    return min(100, base + max(0, facts.gpu_vram_gb - 8) * 2)


def _ram_balance_factor(facts: _Facts) -> int | None:
    if facts.ram_gb is None:
        return None
    if facts.ram_gb >= 64:
        return 95
    if facts.ram_gb >= 32:
        return 82
    if facts.ram_gb >= 16:
        return 68
    return 45


def _storage_balance_factor(facts: _Facts) -> int | None:
    if facts.storage_gb is None:
        return None
    score = 70 if facts.has_nvme_storage else 50
    if facts.storage_gb >= 1000:
        score += 12
    elif facts.storage_gb < 500:
        score -= 15
    return max(0, min(100, score))


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


def _mentions_monitor(intent: BuildIntent) -> bool:
    text = intent.raw_text.casefold()
    components = {component.casefold() for component in intent.mentioned_components}
    return (
        "monitor" in components
        or "monitor" in text
        or "màn hình" in text
        or "man hinh" in text
    )


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
