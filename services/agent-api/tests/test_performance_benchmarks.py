from pc_build_copilot.performance_benchmarks import (
    extract_fps_target,
    load_gaming_benchmark_matrix,
    lookup_gaming_benchmark_estimates,
)


def test_default_gaming_benchmark_matrix_loads_source_backed_rows() -> None:
    matrix = load_gaming_benchmark_matrix()

    assert matrix.matrix_version == "gaming_benchmark_seed_v2026_06_28"
    assert len(matrix.rows) >= 4
    assert all(row.source_url.startswith("https://") for row in matrix.rows)
    assert all(row.fps_low <= row.fps_high for row in matrix.rows)


def test_lookup_requires_matching_game_gpu_resolution_and_preset() -> None:
    estimates = lookup_gaming_benchmark_estimates(
        target_games=["Cyberpunk 2077"],
        gpu_chipset="RX 7600",
        performance_targets=["1440p", "Ultra", "144Hz"],
    )

    assert len(estimates) == 1
    assert estimates[0].target_label == "Cyberpunk 2077 1440p Ultra native"
    assert estimates[0].fps_label == "30-35 FPS"

    rx_7600_1080p = lookup_gaming_benchmark_estimates(
        target_games=["Cyberpunk 2077"],
        gpu_chipset="RX 7600",
        performance_targets=["1080p", "Ultra", "144Hz"],
    )

    assert len(rx_7600_1080p) == 1
    assert rx_7600_1080p[0].target_label == "Cyberpunk 2077 1080p Ultra native"
    assert rx_7600_1080p[0].fps_label == "77 FPS"

    unsupported = lookup_gaming_benchmark_estimates(
        target_games=["Cyberpunk 2077"],
        gpu_chipset="RX 7600",
        performance_targets=["2160p", "Ultra", "144Hz"],
    )

    assert unsupported == []


def test_lookup_covers_rtx_4060_cyberpunk_1440p_ultra() -> None:
    estimates = lookup_gaming_benchmark_estimates(
        target_games=["Cyberpunk 2077"],
        gpu_chipset="RTX 4060",
        performance_targets=["1440p", "Ultra", "144Hz"],
    )

    assert len(estimates) == 1
    assert estimates[0].target_label == "Cyberpunk 2077 1440p Ultra native"
    assert estimates[0].fps_label == "43 FPS"
    assert estimates[0].source_label == "TechSpot Cyberpunk 2077 Phantom Liberty GPU benchmark"


def test_extract_fps_target_uses_highest_fps_or_hz_target() -> None:
    assert extract_fps_target(["1080p", "144Hz", "120fps"]) == 144
    assert extract_fps_target(["1440p", "Ultra"]) is None
