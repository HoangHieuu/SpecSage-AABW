from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from pc_build_copilot.build_alternatives import (
    apply_build_alternative,
    generate_build_alternatives,
)
from pc_build_copilot.build_orchestrator import generate_build_with_orchestration
from pc_build_copilot.build_iteration import iterate_build_from_command
from pc_build_copilot.build_models import (
    BuildApprovalRequest,
    BuildAlternativesResponse,
    BuildArtifact,
    BuildFeedback,
    BuildFeedbackRequest,
    BuildIterationRequest,
    BuildIterationResponse,
    BuildTraceReplay,
    CartReadyHandoff,
    SessionTraceReplay,
)
from pc_build_copilot.build_store import BuildStore
from pc_build_copilot.catalog_models import (
    CatalogQueryResponse,
    CatalogValidationReport,
    ComponentCategory,
)
from pc_build_copilot.catalog_repository import (
    CatalogDataStore,
    create_catalog_repository,
)
from pc_build_copilot.compatibility_models import (
    BuildValidationRequest,
    CompatibilityReport,
)
from pc_build_copilot.compatibility_rules import validate_build_compatibility
from pc_build_copilot.intent_parser import parse_intent
from pc_build_copilot.llm_intent_advisor import LlmIntentAdvisor
from pc_build_copilot.models import (
    BuildSession,
    BuildSessionCreate,
    IntentRequest,
    IntentResponse,
    IntentRevision,
)
from pc_build_copilot.persistence import create_persistent_stores
from pc_build_copilot.store import SessionStore
from pc_build_copilot.trace_replay import build_trace_replay, session_trace_replay
from pc_build_copilot.upgrade_models import (
    ExistingSystemParseRequest,
    ExistingSystemParseResponse,
    UpgradePlanRequest,
    UpgradePlanResponse,
)
from pc_build_copilot.upgrade_planner import (
    create_existing_system_parse,
    create_gpu_upgrade_plan,
)


def create_app(
    store: SessionStore | None = None,
    catalog_repository: CatalogDataStore | None = None,
    build_store: BuildStore | None = None,
    intent_advisor: LlmIntentAdvisor | None = None,
) -> FastAPI:
    if store is None and build_store is None:
        session_store, builds = create_persistent_stores()
    else:
        session_store = store or SessionStore()
        builds = build_store or BuildStore()
    catalog_store = catalog_repository or create_catalog_repository()
    advisor = intent_advisor or LlmIntentAdvisor.from_env()
    app = FastAPI(title="PC Build Copilot Agent API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/catalog/health", response_model=CatalogValidationReport)
    def catalog_health() -> CatalogValidationReport:
        return catalog_store.validation_report()

    @app.get("/catalog/skus", response_model=CatalogQueryResponse)
    def list_catalog_skus(
        category: ComponentCategory | None = None,
        brand: str | None = None,
        min_price_vnd: int | None = Query(default=None, ge=0),
        max_price_vnd: int | None = Query(default=None, ge=0),
        in_stock: bool | None = None,
        socket: str | None = None,
        memory_type: str | None = None,
        min_wattage_w: int | None = Query(default=None, ge=0),
        min_capacity_gb: int | None = Query(default=None, ge=0),
        min_vram_gb: int | None = Query(default=None, ge=0),
    ) -> CatalogQueryResponse:
        return catalog_store.query(
            category=category,
            brand=brand,
            min_price_vnd=min_price_vnd,
            max_price_vnd=max_price_vnd,
            in_stock=in_stock,
            socket=socket,
            memory_type=memory_type,
            min_wattage_w=min_wattage_w,
            min_capacity_gb=min_capacity_gb,
            min_vram_gb=min_vram_gb,
        )

    @app.post("/builds/{build_id}/validate", response_model=CompatibilityReport)
    def validate_build(build_id: str, payload: BuildValidationRequest) -> CompatibilityReport:
        return validate_build_compatibility(
            build_id=build_id,
            selected_skus=payload.selected_skus,
            catalog=catalog_store.snapshot(),
        )

    @app.post("/upgrade-plans/gpu", response_model=UpgradePlanResponse)
    def create_gpu_upgrade(payload: UpgradePlanRequest) -> UpgradePlanResponse:
        return create_gpu_upgrade_plan(
            payload=payload,
            catalog=catalog_store.snapshot(),
        )

    @app.post(
        "/upgrade-plans/existing-system/parse",
        response_model=ExistingSystemParseResponse,
    )
    def parse_existing_upgrade_system(
        payload: ExistingSystemParseRequest,
    ) -> ExistingSystemParseResponse:
        return create_existing_system_parse(payload)

    @app.get("/builds/{build_id}", response_model=BuildArtifact)
    def get_build(build_id: str) -> BuildArtifact:
        return builds.get(build_id)

    @app.get("/builds/{build_id}/trace", response_model=BuildTraceReplay)
    def get_build_trace(build_id: str) -> BuildTraceReplay:
        return build_trace_replay(builds.get(build_id))

    @app.get("/builds/{build_id}/alternatives", response_model=BuildAlternativesResponse)
    def get_build_alternatives(build_id: str) -> BuildAlternativesResponse:
        return generate_build_alternatives(
            base_artifact=builds.get(build_id),
            catalog=catalog_store.snapshot(),
        )

    @app.post("/builds/{build_id}/feedback", response_model=BuildFeedback)
    def submit_build_feedback(
        build_id: str,
        payload: BuildFeedbackRequest,
    ) -> BuildFeedback:
        return builds.save_feedback(build_id, payload)

    @app.get("/builds/{build_id}/feedback", response_model=list[BuildFeedback])
    def get_build_feedback(build_id: str) -> list[BuildFeedback]:
        return builds.feedback_for_build(build_id)

    @app.get("/feedback/review-queue", response_model=list[BuildFeedback])
    def get_feedback_review_queue() -> list[BuildFeedback]:
        return builds.feedback_review_queue()

    @app.post(
        "/builds/{build_id}/alternatives/{variant_id}/apply",
        response_model=BuildArtifact,
    )
    def apply_alternative(build_id: str, variant_id: str) -> BuildArtifact:
        artifact = apply_build_alternative(
            base_artifact=builds.get(build_id),
            variant_id=variant_id,
            catalog=catalog_store.snapshot(),
        )
        if artifact is None:
            raise HTTPException(status_code=404, detail="variant_id not found")
        builds.save(artifact)
        session_store.mark_generated(artifact.build_session_id)
        return artifact

    @app.post("/builds/{build_id}/iterate", response_model=BuildIterationResponse)
    def iterate_build(
        build_id: str,
        payload: BuildIterationRequest,
    ) -> BuildIterationResponse:
        response = iterate_build_from_command(
            base_artifact=builds.get(build_id),
            payload=payload,
            catalog=catalog_store.snapshot(),
        )
        builds.save(response.applied_build)
        session_store.mark_generated(response.applied_build.build_session_id)
        return response

    @app.post("/builds/{build_id}/approve", response_model=CartReadyHandoff)
    def approve_build(
        build_id: str,
        payload: BuildApprovalRequest | None = None,
    ) -> CartReadyHandoff:
        artifact = builds.get(build_id)
        if artifact.can_approve and artifact.status.value == "generated":
            session_store.mark_reviewing(artifact.build_session_id)
        handoff = builds.approve(build_id, payload or BuildApprovalRequest())
        session_store.mark_approved(artifact.build_session_id)
        session_store.mark_cart_ready(artifact.build_session_id)
        return handoff

    @app.post("/sessions", response_model=BuildSession)
    def create_session(payload: BuildSessionCreate = BuildSessionCreate()) -> BuildSession:
        return session_store.create(
            BuildSession(locale=payload.locale, channel=payload.channel)
        )

    @app.get("/sessions/{build_session_id}", response_model=BuildSession)
    def get_session(build_session_id: str) -> BuildSession:
        return session_store.get(build_session_id)

    @app.get("/sessions/{build_session_id}/intent-revisions", response_model=list[IntentRevision])
    def get_intent_revisions(build_session_id: str) -> list[IntentRevision]:
        return session_store.revisions(build_session_id)

    @app.get("/sessions/{build_session_id}/trace", response_model=SessionTraceReplay)
    def get_session_trace(build_session_id: str) -> SessionTraceReplay:
        session_store.get(build_session_id)
        return session_trace_replay(
            build_session_id=build_session_id,
            artifacts=builds.list_for_session(build_session_id),
        )

    @app.post("/sessions/{build_session_id}/intent", response_model=IntentResponse)
    def submit_intent(build_session_id: str, payload: IntentRequest) -> IntentResponse:
        session = session_store.get(build_session_id)
        intent, clarification = parse_intent(payload.message, payload.preset)
        confirmed = payload.confirm and clarification.field is None
        agent_analysis = None
        if payload.use_llm and not payload.confirm:
            agent_analysis = advisor.analyze(payload.message, intent, clarification)
        revision = session_store.add_revision(
            IntentRevision(
                build_session_id=build_session_id,
                intent=intent,
                clarification=clarification,
                confirmed=confirmed,
            )
        )
        return IntentResponse(
            session=session_store.get(session.build_session_id),
            revision=revision,
            agent_analysis=agent_analysis,
        )

    @app.post("/sessions/{build_session_id}/generate", response_model=BuildArtifact)
    def generate_build(build_session_id: str) -> BuildArtifact:
        revision = session_store.latest_confirmed_revision(build_session_id)
        artifact = generate_build_with_orchestration(
            build_session_id=build_session_id,
            intent=revision.intent,
            catalog=catalog_store.snapshot(),
        )
        builds.save(artifact)
        session_store.mark_generated(build_session_id)
        return artifact

    return app


app = create_app()
