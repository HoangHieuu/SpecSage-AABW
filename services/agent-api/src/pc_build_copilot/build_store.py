from fastapi import HTTPException

from pc_build_copilot.build_models import (
    BuildApproval,
    BuildArtifact,
    BuildStatus,
    CartReadyHandoff,
)


class BuildStore:
    def __init__(self) -> None:
        self._builds: dict[str, BuildArtifact] = {}
        self._cart_handoffs: dict[str, CartReadyHandoff] = {}
        self._cart_handoff_by_build: dict[str, str] = {}

    def save(self, artifact: BuildArtifact) -> BuildArtifact:
        self._builds[artifact.build_id] = artifact
        return artifact

    def get(self, build_id: str) -> BuildArtifact:
        artifact = self._builds.get(build_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail="build_id not found")
        return artifact

    def approve(self, build_id: str) -> CartReadyHandoff:
        artifact = self.get(build_id)
        existing_handoff_id = self._cart_handoff_by_build.get(build_id)
        if existing_handoff_id:
            return self._cart_handoffs[existing_handoff_id]
        if artifact.status != BuildStatus.GENERATED or not artifact.can_approve:
            raise HTTPException(
                status_code=409,
                detail="build must be compatible and within budget before approval",
            )

        approval = BuildApproval(
            build_id=artifact.build_id,
            build_session_id=artifact.build_session_id,
            selected_skus={item.slot.value: item.sku for item in artifact.items},
            total_price_vnd=artifact.total_price_vnd,
            catalog_version=artifact.catalog_version,
            rules_version=artifact.rules_version,
        )
        handoff = CartReadyHandoff(
            build_id=artifact.build_id,
            build_session_id=artifact.build_session_id,
            approval=approval,
            total_price_vnd=artifact.total_price_vnd,
            item_count=len(artifact.items),
            mock_cart_payload=artifact.mock_cart_payload,
            warnings_vi=[
                *artifact.warnings_vi,
                "Mock cart: mở từng link sản phẩm Phong Vu để thêm vào giỏ.",
            ],
        )
        self._cart_handoffs[handoff.handoff_id] = handoff
        self._cart_handoff_by_build[build_id] = handoff.handoff_id
        return handoff
