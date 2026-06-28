from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class GamingBenchmarkRow(BaseModel):
    game: str
    game_aliases: list[str] = Field(default_factory=list)
    gpu_chipset: str
    gpu_aliases: list[str] = Field(default_factory=list)
    resolution: str
    preset: str
    render_mode: str = "native"
    fps_low: int = Field(ge=1)
    fps_high: int = Field(ge=1)
    source_label: str
    source_url: str
    methodology: str

    @model_validator(mode="after")
    def validate_fps_range(self) -> "GamingBenchmarkRow":
        if self.fps_high < self.fps_low:
            raise ValueError("fps_high must be greater than or equal to fps_low")
        return self


class GamingBenchmarkMatrix(BaseModel):
    matrix_version: str
    generated_at: str
    disclaimer_vi: str
    rows: list[GamingBenchmarkRow] = Field(default_factory=list)


class GamingBenchmarkEstimate(BaseModel):
    matrix_version: str
    disclaimer_vi: str
    game: str
    gpu_chipset: str
    resolution: str
    preset: str
    render_mode: str
    fps_low: int
    fps_high: int
    source_label: str
    source_url: str

    @property
    def fps_label(self) -> str:
        if self.fps_low == self.fps_high:
            return f"{self.fps_low} FPS"
        return f"{self.fps_low}-{self.fps_high} FPS"

    @property
    def target_label(self) -> str:
        return f"{self.game} {self.resolution} {self.preset} {self.render_mode}"


def default_benchmark_matrix_path() -> Path:
    return Path(__file__).resolve().parents[2] / "benchmarks" / "gaming_benchmark_matrix.json"


@lru_cache(maxsize=1)
def load_gaming_benchmark_matrix(
    path: Path | None = None,
) -> GamingBenchmarkMatrix:
    matrix_path = path or default_benchmark_matrix_path()
    payload = json.loads(matrix_path.read_text(encoding="utf-8"))
    return GamingBenchmarkMatrix.model_validate(payload)


def lookup_gaming_benchmark_estimates(
    *,
    target_games: list[str],
    gpu_chipset: str | None,
    performance_targets: list[str],
    matrix: GamingBenchmarkMatrix | None = None,
    max_results: int = 2,
) -> list[GamingBenchmarkEstimate]:
    if not target_games or not gpu_chipset:
        return []

    matrix = matrix or load_gaming_benchmark_matrix()
    requested_resolution = _requested_resolution(performance_targets)
    requested_preset = _requested_preset(performance_targets)
    estimates: list[GamingBenchmarkEstimate] = []

    for game in target_games:
        for row in matrix.rows:
            if not _game_matches(row, game):
                continue
            if not _gpu_matches(row, gpu_chipset):
                continue
            if requested_resolution and _normalize_resolution(row.resolution) != requested_resolution:
                continue
            if requested_preset and _normalize(row.preset) != requested_preset:
                continue
            estimates.append(_estimate_from_row(row, matrix))
            break
        if len(estimates) >= max_results:
            break

    return estimates


def extract_fps_target(performance_targets: list[str]) -> int | None:
    fps_targets = []
    for target in performance_targets:
        match = re.search(r"(\d{2,3})\s*(?:fps|hz)\b", target, re.IGNORECASE)
        if match:
            fps_targets.append(int(match.group(1)))
    return max(fps_targets) if fps_targets else None


def _estimate_from_row(
    row: GamingBenchmarkRow,
    matrix: GamingBenchmarkMatrix,
) -> GamingBenchmarkEstimate:
    return GamingBenchmarkEstimate(
        matrix_version=matrix.matrix_version,
        disclaimer_vi=matrix.disclaimer_vi,
        game=row.game,
        gpu_chipset=row.gpu_chipset,
        resolution=row.resolution,
        preset=row.preset,
        render_mode=row.render_mode,
        fps_low=row.fps_low,
        fps_high=row.fps_high,
        source_label=row.source_label,
        source_url=row.source_url,
    )


def _game_matches(row: GamingBenchmarkRow, game: str) -> bool:
    candidates = [row.game, *row.game_aliases]
    normalized_game = _normalize(game)
    return any(_normalize(candidate) == normalized_game for candidate in candidates)


def _gpu_matches(row: GamingBenchmarkRow, gpu_chipset: str) -> bool:
    normalized_chipset = _normalize(gpu_chipset)
    candidates = [row.gpu_chipset, *row.gpu_aliases]
    return any(_normalize(candidate) in normalized_chipset for candidate in candidates)


def _requested_resolution(performance_targets: list[str]) -> str | None:
    for target in performance_targets:
        normalized = _normalize_resolution(target)
        if normalized:
            return normalized
    return None


def _requested_preset(performance_targets: list[str]) -> str | None:
    for target in performance_targets:
        normalized = _normalize(target)
        if normalized in {"low", "medium", "high", "ultra"}:
            return normalized
    return None


def _normalize_resolution(value: str) -> str | None:
    normalized = _normalize(value)
    if normalized in {"1080p", "1440p", "2160p"}:
        return normalized
    if normalized == "2k":
        return "1440p"
    if normalized == "4k":
        return "2160p"
    return None


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())
