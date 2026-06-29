from fastapi import HTTPException

from pc_build_copilot.build_models import (
    BuildApproval,
    BuildApprovalRequest,
    BuildArtifact,
    BuildFeedback,
    BuildFeedbackRequest,
    BuildFeedbackReviewStatus,
    BuildFeedbackRating,
    BuildRecommendedAddOn,
    BuildStatus,
    CartReadyHandoff,
    MockCartPayload,
    PartFeedback,
)


class BuildStore:
    def __init__(self) -> None:
        self._builds: dict[str, BuildArtifact] = {}
        self._cart_handoffs: dict[str, CartReadyHandoff] = {}
        self._cart_handoff_by_build: dict[str, str] = {}
        self._feedback: dict[str, BuildFeedback] = {}
        self._feedback_by_build: dict[str, list[str]] = {}

    def save(self, artifact: BuildArtifact) -> BuildArtifact:
        self._builds[artifact.build_id] = artifact
        return artifact

    def get(self, build_id: str) -> BuildArtifact:
        artifact = self._builds.get(build_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail="build_id not found")
        return artifact

    def list_for_session(self, build_session_id: str) -> list[BuildArtifact]:
        return sorted(
            [
                artifact
                for artifact in self._builds.values()
                if artifact.build_session_id == build_session_id
            ],
            key=lambda artifact: (artifact.build_version, artifact.generated_at),
        )

    def approve(
        self,
        build_id: str,
        payload: BuildApprovalRequest | None = None,
    ) -> CartReadyHandoff:
        artifact = self.get(build_id)
        payload = payload or BuildApprovalRequest()
        selected_addon_skus = normalized_selected_addon_skus(artifact, payload)
        existing_handoff_id = self._cart_handoff_by_build.get(build_id)
        if existing_handoff_id:
            existing = self._cart_handoffs[existing_handoff_id]
            assert_same_addon_selection(existing, selected_addon_skus)
            return existing
        if artifact.status != BuildStatus.GENERATED or not artifact.can_approve:
            raise HTTPException(
                status_code=409,
                detail="build must be compatible and within budget before approval",
            )

        handoff = cart_handoff_from_artifact(artifact, payload)
        self._cart_handoffs[handoff.handoff_id] = handoff
        self._cart_handoff_by_build[build_id] = handoff.handoff_id
        return handoff

    def save_feedback(
        self,
        build_id: str,
        payload: BuildFeedbackRequest,
    ) -> BuildFeedback:
        artifact = self.get(build_id)
        feedback = build_feedback_from_artifact(artifact, payload)
        self._feedback[feedback.feedback_id] = feedback
        self._feedback_by_build.setdefault(build_id, []).append(feedback.feedback_id)
        return feedback

    def feedback_for_build(self, build_id: str) -> list[BuildFeedback]:
        self.get(build_id)
        return [
            self._feedback[feedback_id]
            for feedback_id in self._feedback_by_build.get(build_id, [])
        ]

    def feedback_review_queue(self) -> list[BuildFeedback]:
        return sorted(
            [
                feedback
                for feedback in self._feedback.values()
                if feedback.review_queue_status == BuildFeedbackReviewStatus.QUEUED
            ],
            key=lambda feedback: feedback.created_at,
            reverse=True,
        )


def build_feedback_from_artifact(
    artifact: BuildArtifact,
    payload: BuildFeedbackRequest,
) -> BuildFeedback:
    part_feedback = _validated_part_feedback(artifact, payload)
    review_queued = payload.rating == BuildFeedbackRating.THUMBS_DOWN or any(
        part.rating == BuildFeedbackRating.THUMBS_DOWN for part in part_feedback
    )
    return BuildFeedback(
        build_id=artifact.build_id,
        build_session_id=artifact.build_session_id,
        build_version=artifact.build_version,
        catalog_version=artifact.catalog_version,
        rules_version=artifact.rules_version,
        rating=payload.rating,
        reason_tags=payload.reason_tags,
        comment_vi=payload.comment_vi,
        part_feedback=part_feedback,
        review_queue_status=(
            BuildFeedbackReviewStatus.QUEUED
            if review_queued
            else BuildFeedbackReviewStatus.NOT_QUEUED
        ),
        review_queue_reason_vi=_review_queue_reason(payload, part_feedback),
    )


def _validated_part_feedback(
    artifact: BuildArtifact,
    payload: BuildFeedbackRequest,
) -> list[PartFeedback]:
    items_by_key = {(item.slot, item.sku): item for item in artifact.items}
    seen_keys: set[tuple[object, str]] = set()
    feedback: list[PartFeedback] = []
    for part in payload.part_feedback:
        key = (part.slot, part.sku)
        if key in seen_keys:
            raise HTTPException(
                status_code=422,
                detail="part feedback can only reference each build SKU once",
            )
        seen_keys.add(key)
        item = items_by_key.get(key)
        if item is None:
            raise HTTPException(
                status_code=422,
                detail="part feedback must reference a SKU in this build",
            )
        feedback.append(
            PartFeedback(
                slot=part.slot,
                sku=part.sku,
                name=item.name,
                rating=part.rating,
                reason_tags=part.reason_tags,
                comment_vi=part.comment_vi,
            )
        )
    return feedback


def _review_queue_reason(
    payload: BuildFeedbackRequest,
    part_feedback: list[PartFeedback],
) -> str | None:
    if payload.rating == BuildFeedbackRating.THUMBS_DOWN:
        return "Khach hang danh gia build chua phu hop; can review lai intent va cau hinh."
    if any(part.rating == BuildFeedbackRating.THUMBS_DOWN for part in part_feedback):
        return "Khach hang danh gia mot linh kien chua phu hop; can review part-level feedback."
    return None


def cart_handoff_from_artifact(
    artifact: BuildArtifact,
    payload: BuildApprovalRequest | None = None,
) -> CartReadyHandoff:
    payload = payload or BuildApprovalRequest()
    selected_addon_skus = normalized_selected_addon_skus(artifact, payload)
    selected_addons = _selected_addons(artifact, selected_addon_skus)
    add_on_total = sum(item.price_vnd for item in selected_addons)
    mock_items = [
        {"sku": item.sku, "url": item.url, "name": item.name}
        for item in artifact.items
    ]
    mock_items.extend(
        {"sku": item.sku, "url": item.url, "name": item.name}
        for item in selected_addons
    )
    approval = BuildApproval(
        build_id=artifact.build_id,
        build_session_id=artifact.build_session_id,
        selected_skus={item.slot.value: item.sku for item in artifact.items},
        total_price_vnd=artifact.total_price_vnd,
        catalog_version=artifact.catalog_version,
        rules_version=artifact.rules_version,
    )
    return CartReadyHandoff(
        build_id=artifact.build_id,
        build_session_id=artifact.build_session_id,
        approval=approval,
        total_price_vnd=artifact.total_price_vnd,
        add_on_total_price_vnd=add_on_total,
        shopping_list_total_price_vnd=artifact.total_price_vnd + add_on_total,
        item_count=len(mock_items),
        selected_addons=selected_addons,
        mock_cart_payload=MockCartPayload(items=mock_items),
        warnings_vi=[
            *artifact.warnings_vi,
            *(
                [
                    "Gợi ý thêm đã chọn là tùy chọn; giá này không thay đổi cấu hình PC đã duyệt."
                ]
                if selected_addons
                else []
            ),
            "Mock cart: mở từng link sản phẩm Phong Vu để thêm vào giỏ.",
        ],
    )


def normalized_selected_addon_skus(
    artifact: BuildArtifact,
    payload: BuildApprovalRequest,
) -> tuple[str, ...]:
    seen: set[str] = set()
    requested: list[str] = []
    for sku in payload.selected_addon_skus:
        if sku in seen:
            raise HTTPException(
                status_code=422,
                detail="selected_addon_skus cannot contain duplicate SKUs",
            )
        seen.add(sku)
        requested.append(sku)

    addon_by_sku = {item.sku: item for item in artifact.recommended_addons}
    unknown = [sku for sku in requested if sku not in addon_by_sku]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail="selected_addon_skus must reference recommended add-ons for this build",
        )
    requested_set = set(requested)
    return tuple(
        item.sku
        for item in artifact.recommended_addons
        if item.sku in requested_set
    )


def _selected_addons(
    artifact: BuildArtifact,
    selected_addon_skus: tuple[str, ...],
) -> list[BuildRecommendedAddOn]:
    selected = set(selected_addon_skus)
    return [item for item in artifact.recommended_addons if item.sku in selected]


def assert_same_addon_selection(
    handoff: CartReadyHandoff,
    selected_addon_skus: tuple[str, ...],
) -> None:
    existing = tuple(item.sku for item in handoff.selected_addons)
    if existing != selected_addon_skus:
        raise HTTPException(
            status_code=409,
            detail="cart handoff already exists for this build with different add-ons",
        )
