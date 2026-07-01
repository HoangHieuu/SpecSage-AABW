"use client";

import { CSSProperties, FormEvent, RefObject, useEffect, useMemo, useRef, useState } from "react";

import { BackgroundAnimation } from "@/components/background-animation";
import {
  BuildAlternative,
  BuildAlternativesResponse,
  BuildArtifact,
  BuildFeedback,
  BuildFeedbackRating,
  BuildFeedbackReason,
  BuildFeedbackRequest,
  BuildItem,
  BuildIterationResponse,
  BuildOrchestrationStep,
  BuildRecommendedAddOn,
  BuildSession,
  CartReadyHandoff,
  ExistingSystemOverrides,
  ExistingSystemParseResponse,
  IntentAgentAnalysis,
  IntentResponse,
  OptimizerTrace,
  PartFeedbackRequest,
  PerformanceProfile,
  SessionTraceReplay,
  TraceReplayEvent,
  UpgradePlanResponse,
  UseCase,
  applyBuildAlternative,
  approveBuild,
  createGpuUpgradePlan,
  createSession,
  generateBuild,
  getBuildAlternatives,
  getSessionTrace,
  iterateBuild,
  parseExistingSystem,
  submitBuildFeedback,
  submitIntent
} from "@/lib/api";

const presets: Array<{ value: UseCase; label: string; sample: string }> = [
  {
    value: "gaming",
    label: "Gaming",
    sample: "PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz, ưu tiên VGA"
  },
  {
    value: "creator",
    label: "Đồ họa",
    sample: "PC đồ họa khoảng 35 triệu dùng Premiere và Photoshop"
  },
  {
    value: "office",
    label: "Văn phòng",
    sample: "Máy văn phòng khoảng 20 triệu, ưu tiên êm và bền"
  },
  {
    value: "ai",
    label: "AI cá nhân",
    sample: "PC chạy AI cục bộ 40 triệu, ưu tiên NVIDIA và 32GB RAM"
  }
];

type PresetOption = (typeof presets)[number];
type ResolutionOption = "Full HD (1080p)" | "QHD (1440p)" | "4K (2160p)";

const useCaseCards: Array<PresetOption & { description: string; icon: "gamepad" | "creator" | "office" | "ai" }> = [
  {
    ...presets[0],
    description: "Chơi game AAA, eSports",
    icon: "gamepad"
  },
  {
    ...presets[1],
    description: "Render, dựng phim, 3D",
    icon: "creator"
  },
  {
    ...presets[2],
    description: "Hiệu suất, ổn định",
    icon: "office"
  },
  {
    ...presets[3],
    description: "LLM, training, inference",
    icon: "ai"
  }
];

const resolutionOptions: ResolutionOption[] = ["Full HD (1080p)", "QHD (1440p)", "4K (2160p)"];
const priorityOptions = ["Hiệu năng / FPS", "Đồ họa đẹp", "Yên tĩnh", "Nâng cấp dễ dàng", "Tiết kiệm điện", "Nhỏ gọn"];
const featureOptions = ["Wi-Fi / Bluetooth", "RGB", "Không LED", "Kèm màn hình"];

const useCaseLabels: Record<UseCase, string> = {
  gaming: "Gaming",
  creator: "Creator/đồ họa",
  office: "Văn phòng",
  student: "Sinh viên",
  ai: "AI cá nhân",
  streaming: "Streaming",
  compact: "Compact/Mini ITX",
  unknown: "Chưa rõ"
};

type DisplayMode = "basic" | "advanced";

const defaultUpgradeCurrentPc =
  "Máy hiện tại i5-12400F, B660 DDR4, RAM 16GB, RTX 3060, nguồn 650W 2x8-pin, case hỗ trợ GPU 330mm, SSD 1TB";

export function BuildCopilotClient() {
  const intentTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [session, setSession] = useState<BuildSession | null>(null);
  const [message, setMessage] = useState(presets[0].sample);
  const [preset, setPreset] = useState<UseCase>("gaming");
  const [budgetTarget, setBudgetTarget] = useState(30);
  const [resolution, setResolution] = useState<ResolutionOption>("QHD (1440p)");
  const [selectedPriorities, setSelectedPriorities] = useState(["Hiệu năng / FPS", "Nâng cấp dễ dàng"]);
  const [selectedFeatures, setSelectedFeatures] = useState(["Wi-Fi / Bluetooth", "RGB"]);
  const [intentResponse, setIntentResponse] = useState<IntentResponse | null>(null);
  const [agentAnalysis, setAgentAnalysis] = useState<IntentAgentAnalysis | null>(null);
  const [buildArtifact, setBuildArtifact] = useState<BuildArtifact | null>(null);
  const [buildAlternatives, setBuildAlternatives] = useState<BuildAlternativesResponse | null>(null);
  const [sessionTrace, setSessionTrace] = useState<SessionTraceReplay | null>(null);
  const [cartHandoff, setCartHandoff] = useState<CartReadyHandoff | null>(null);
  const [selectedAddOnSkus, setSelectedAddOnSkus] = useState<string[]>([]);
  const [buildFeedback, setBuildFeedback] = useState<BuildFeedback | null>(null);
  const [appliedAlternativeLabel, setAppliedAlternativeLabel] = useState<string | null>(null);
  const [iterationCommand, setIterationCommand] = useState("Tăng SSD nhưng giữ dưới 20 triệu");
  const [lastIteration, setLastIteration] = useState<BuildIterationResponse | null>(null);
  const [upgradeCurrentPc, setUpgradeCurrentPc] = useState(defaultUpgradeCurrentPc);
  const [upgradeBudgetText, setUpgradeBudgetText] = useState("10000000");
  const [upgradeParse, setUpgradeParse] = useState<ExistingSystemParseResponse | null>(null);
  const [confirmedExistingSystem, setConfirmedExistingSystem] = useState<ExistingSystemOverrides>({});
  const [upgradePlan, setUpgradePlan] = useState<UpgradePlanResponse | null>(null);
  const [displayMode, setDisplayMode] = useState<DisplayMode>("basic");
  const [showSupportDetails, setShowSupportDetails] = useState(false);
  const [traceCopyState, setTraceCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const [isLoading, setIsLoading] = useState(false);
  const [isParsingUpgrade, setIsParsingUpgrade] = useState(false);
  const [isPlanningUpgrade, setIsPlanningUpgrade] = useState(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const intent = intentResponse?.revision.intent;
  const isConfirmed = intentResponse?.revision.confirmed ?? false;
  const canConfirm = Boolean(intentResponse && !intentResponse.revision.clarification.field);
  const canApprove = Boolean(
    buildArtifact && buildArtifact.can_approve && buildArtifact.status === "generated" && !cartHandoff
  );
  const needsClarification = Boolean(intentResponse?.revision.clarification.field);
  const primaryActionLabel = buildArtifact
    ? "Phân tích nhu cầu mới"
    : isConfirmed
      ? "Sinh cấu hình"
      : intentResponse && !needsClarification
        ? "Xác nhận & sinh cấu hình"
        : "Phân tích nhu cầu";
  const primaryActionHint = buildArtifact
    ? "Chỉnh mô tả rồi chạy lại nếu bạn muốn bắt đầu một đề xuất mới."
    : isConfirmed
      ? "Nhu cầu đã xác nhận, bước tiếp theo là sinh cấu hình."
      : intentResponse && !needsClarification
        ? "Bước này sẽ xác nhận nhu cầu và tạo cấu hình ngay."
        : "Mô tả nhu cầu, ngân sách và ưu tiên của bạn.";

  const budget = useMemo(() => {
    if (!intent) return "Chưa có";
    return formatBudget(intent.budget_min, intent.budget_max);
  }, [intent]);
  const selectedAddOnTotal = useMemo(() => {
    if (!buildArtifact || !selectedAddOnSkus.length) return 0;
    const selected = new Set(selectedAddOnSkus);
    return buildArtifact.recommended_addons.reduce(
      (total, addon) => total + (selected.has(addon.sku) ? addon.price_vnd : 0),
      0
    );
  }, [buildArtifact, selectedAddOnSkus]);

  useEffect(() => {
    const textarea = intentTextareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  }, [message]);

  async function ensureSession() {
    if (session) return session;
    const created = await createSession();
    setSession(created);
    return created;
  }

  async function handleStart() {
    setIsLoading(true);
    setError(null);
    try {
      const created = await createSession();
      setSession(created);
      setIntentResponse(null);
      setAgentAnalysis(null);
      setBuildArtifact(null);
      setBuildAlternatives(null);
      setSessionTrace(null);
      setCartHandoff(null);
      setSelectedAddOnSkus([]);
      setBuildFeedback(null);
      setAppliedAlternativeLabel(null);
      setLastIteration(null);
      setDisplayMode("basic");
      setShowSupportDetails(false);
      setTraceCopyState("idle");
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await handlePrimaryAction();
  }

  function handlePresetSelect(item: PresetOption) {
    setPreset(item.value);
    setMessage(item.sample);
    setBudgetTarget(extractBudgetMillions(item.sample) ?? budgetTarget);
  }

  function handleBudgetTargetChange(nextBudget: number) {
    setBudgetTarget(nextBudget);
    setMessage((current) => applyBudgetText(current, nextBudget));
  }

  function togglePriority(priority: string) {
    setSelectedPriorities((current) => toggleListItem(current, priority));
  }

  function toggleFeature(feature: string) {
    setSelectedFeatures((current) => toggleListItem(current, feature));
  }

  async function submitIntentRevision(confirm: boolean) {
    const activeSession = await ensureSession();
    const response = await submitIntent(activeSession.build_session_id, message, confirm, preset);
    setSession(response.session);
    setIntentResponse(response);
    if (response.agent_analysis) {
      setAgentAnalysis(response.agent_analysis);
    } else if (!confirm) {
      setAgentAnalysis(null);
    }
    setBuildArtifact(null);
    setBuildAlternatives(null);
    setSessionTrace(null);
    setCartHandoff(null);
    setSelectedAddOnSkus([]);
    setBuildFeedback(null);
    setAppliedAlternativeLabel(null);
    setLastIteration(null);
    setDisplayMode("basic");
    setShowSupportDetails(false);
    setTraceCopyState("idle");
    return response;
  }

  async function loadBuildOutputs(artifact: BuildArtifact) {
    const [alternatives, trace] = await Promise.all([
      getBuildAlternatives(artifact.build_id),
      getSessionTrace(artifact.build_session_id)
    ]);
    setBuildArtifact(artifact);
    setBuildAlternatives(alternatives);
    setSessionTrace(trace);
    setCartHandoff(null);
    setSelectedAddOnSkus([]);
    setBuildFeedback(null);
    setAppliedAlternativeLabel(null);
    setLastIteration(null);
    setDisplayMode("basic");
    setShowSupportDetails(false);
    setTraceCopyState("idle");
    setSession((current) => (current ? { ...current, state: "generated" } : current));
  }

  async function handlePrimaryAction() {
    if (buildArtifact) {
      await sendIntent(false);
      return;
    }
    if (isConfirmed) {
      await handleGenerate();
      return;
    }
    if (intentResponse && canConfirm) {
      await handleConfirmAndGenerate();
      return;
    }
    await sendIntent(false);
  }

  async function sendIntent(confirm: boolean) {
    setIsLoading(true);
    setError(null);
    try {
      await submitIntentRevision(confirm);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleConfirmAndGenerate() {
    setIsLoading(true);
    setError(null);
    try {
      const response = await submitIntentRevision(true);
      if (!response.revision.confirmed) return;
      const artifact = await generateBuild(response.session.build_session_id);
      await loadBuildOutputs(artifact);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleGenerate() {
    if (!session || !isConfirmed) return;
    setIsLoading(true);
    setError(null);
    try {
      const artifact = await generateBuild(session.build_session_id);
      await loadBuildOutputs(artifact);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleApplyAlternative(alternative: BuildAlternative) {
    if (!buildArtifact) return;
    setIsLoading(true);
    setError(null);
    try {
      const artifact = await applyBuildAlternative(buildArtifact.build_id, alternative.variant_id);
      const [alternatives, trace] = await Promise.all([
        getBuildAlternatives(artifact.build_id),
        getSessionTrace(artifact.build_session_id)
      ]);
      setBuildArtifact(artifact);
      setBuildAlternatives(alternatives);
      setSessionTrace(trace);
      setCartHandoff(null);
      setSelectedAddOnSkus([]);
      setBuildFeedback(null);
      setAppliedAlternativeLabel(alternative.label_vi);
      setLastIteration(null);
      setDisplayMode("basic");
      setShowSupportDetails(false);
      setTraceCopyState("idle");
      setSession((current) => (current ? { ...current, state: "generated" } : current));
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCopyTraceExport() {
    if (!sessionTrace) return;
    try {
      await navigator.clipboard.writeText(sessionTrace.support_export_text);
      setTraceCopyState("copied");
    } catch {
      setTraceCopyState("failed");
    }
  }

  async function handleIterateBuild(commandOverride?: string) {
    if (!buildArtifact) return;
    const command = (commandOverride ?? iterationCommand).trim();
    if (!command) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await iterateBuild(buildArtifact.build_id, command);
      const [alternatives, trace] = await Promise.all([
        getBuildAlternatives(response.applied_build.build_id),
        getSessionTrace(response.applied_build.build_session_id)
      ]);
      setBuildArtifact(response.applied_build);
      setBuildAlternatives(alternatives);
      setSessionTrace(trace);
      setCartHandoff(null);
      setSelectedAddOnSkus([]);
      setBuildFeedback(null);
      setAppliedAlternativeLabel(null);
      setLastIteration(response);
      setIterationCommand(command);
      setDisplayMode("basic");
      setShowSupportDetails(false);
      setTraceCopyState("idle");
      setSession((current) => (current ? { ...current, state: "generated" } : current));
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleApprove() {
    if (!buildArtifact || !canApprove) return;
    setIsLoading(true);
    setError(null);
    try {
      const handoff = await approveBuild(buildArtifact.build_id, {
        selected_addon_skus: selectedAddOnSkus
      });
      setCartHandoff(handoff);
      setSession((current) => (current ? { ...current, state: "cart_ready" } : current));
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  function handleToggleAddOn(sku: string, checked: boolean) {
    setSelectedAddOnSkus((current) => {
      if (checked) {
        return current.includes(sku) ? current : [...current, sku];
      }
      return current.filter((item) => item !== sku);
    });
  }

  async function handleSubmitFeedback(payload: BuildFeedbackRequest) {
    if (!buildArtifact) return;
    setIsSubmittingFeedback(true);
    setError(null);
    try {
      const feedback = await submitBuildFeedback(buildArtifact.build_id, payload);
      setBuildFeedback(feedback);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsSubmittingFeedback(false);
    }
  }

  function handleUpgradeCurrentPcChange(value: string) {
    setUpgradeCurrentPc(value);
    setUpgradeParse(null);
    setConfirmedExistingSystem({});
    setUpgradePlan(null);
  }

  async function handleParseExistingSystem() {
    const trimmedCurrentPc = upgradeCurrentPc.trim();
    if (!trimmedCurrentPc) return;
    setIsParsingUpgrade(true);
    setError(null);
    try {
      const parsed = await parseExistingSystem({ current_pc: trimmedCurrentPc });
      setUpgradeParse(parsed);
      setConfirmedExistingSystem(existingSystemToOverrides(parsed.existing_system));
      setUpgradePlan(null);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsParsingUpgrade(false);
    }
  }

  function handleConfirmedExistingSystemChange<K extends keyof ExistingSystemOverrides>(
    field: K,
    value: ExistingSystemOverrides[K]
  ) {
    setConfirmedExistingSystem((current) => ({ ...current, [field]: value }));
    setUpgradePlan(null);
  }

  async function handlePlanGpuUpgrade(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedCurrentPc = upgradeCurrentPc.trim();
    if (!trimmedCurrentPc || !upgradeParse) return;
    setIsPlanningUpgrade(true);
    setError(null);
    try {
      const plan = await createGpuUpgradePlan({
        current_pc: trimmedCurrentPc,
        target_use_case: "gaming",
        upgrade_budget_max_vnd: parseVndInput(upgradeBudgetText),
        confirmed_existing_system: confirmedExistingSystem
      });
      setUpgradePlan(plan);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsPlanningUpgrade(false);
    }
  }

  const workflowStatus = cartHandoff
    ? "Sẵn sàng mua"
    : buildArtifact
      ? "Đã có build"
      : isConfirmed
        ? "Đã xác nhận"
        : intentResponse
          ? "Đang chốt nhu cầu"
          : session
            ? "Đang nhập nhu cầu"
            : "Chưa bắt đầu";
  const sessionLabel = session ? `Phiên ${session.build_session_id.slice(0, 8)}` : "Chưa có phiên";
  const agentStatusLabel = agentAnalysis
    ? agentAnalysis.status === "available"
      ? "LLM đang hoạt động"
      : agentAnalysis.status === "degraded"
        ? "LLM gián đoạn"
        : "LLM chưa bật"
    : "LLM chờ phân tích";
  const agentStatusTone = agentAnalysis?.status === "available" ? "positive" : agentAnalysis ? "warning" : "";
  const selectedSkuLabel = buildArtifact ? `${buildArtifact.items.length} SKU` : "Chưa sinh build";
  const compatibilityLabel = buildArtifact
    ? buildArtifact.compatibility_report.status === "approved"
      ? "Tương thích"
      : buildArtifact.compatibility_report.status === "warning"
        ? "Cần xem cảnh báo"
        : "Bị chặn"
    : "Chờ kiểm tra";
  const cartItemCount = buildArtifact ? buildArtifact.items.length + selectedAddOnSkus.length : 0;
  const shoppingTotal = (buildArtifact?.total_price_vnd ?? 0) + selectedAddOnTotal;

  return (
    <>
      <BackgroundAnimation />
      <main className={`commerce-app${isLoading ? " is-loading" : ""}`}>
        <CommerceHeader
          agentStatusLabel={agentStatusLabel}
          agentStatusTone={agentStatusTone}
          sessionLabel={sessionLabel}
        />

        <section className="commerce-grid" aria-label="SpecSage build console">
          <IntentControlPanel
            preset={preset}
            budgetTarget={budgetTarget}
            resolution={resolution}
            selectedPriorities={selectedPriorities}
            selectedFeatures={selectedFeatures}
            message={message}
            isLoading={isLoading}
            primaryActionLabel={primaryActionLabel}
            primaryActionHint={primaryActionHint}
            error={error}
            textareaRef={intentTextareaRef}
            onSubmit={handleSubmit}
            onPresetSelect={handlePresetSelect}
            onBudgetTargetChange={handleBudgetTargetChange}
            onResolutionChange={setResolution}
            onTogglePriority={togglePriority}
            onToggleFeature={toggleFeature}
            onMessageChange={setMessage}
          />

          <section className="build-workbench" aria-live="polite" data-testid="build-panel">
            <div className="workbench-heading">
              <div>
                <h1>2. Build đề xuất cho bạn</h1>
                <div className="workbench-tags">
                  <span>{intent ? `Đã tối ưu cho ${useCaseLabels[intent.use_case]}` : workflowStatus}</span>
                  <span>{resolution}</span>
                </div>
              </div>
              <div className="workbench-actions">
                <button type="button" className="ghost-action" disabled={!buildArtifact}>
                  Chia sẻ build
                </button>
                <button type="button" className="ghost-action" disabled={!buildArtifact}>
                  Lưu build
                </button>
                <button type="button" className="ghost-action" onClick={handleStart} disabled={isLoading}>
                  Xóa build
                </button>
              </div>
            </div>

            <CommerceMetricStrip
              artifact={buildArtifact}
              selectedSkuLabel={selectedSkuLabel}
              compatibilityLabel={compatibilityLabel}
            />

            <CommerceProcessSteps
              hasIntent={Boolean(intentResponse)}
              isConfirmed={isConfirmed}
              hasBuild={Boolean(buildArtifact)}
              hasCart={Boolean(cartHandoff)}
            />

            <BuildItemsTable artifact={buildArtifact} />

            {appliedAlternativeLabel ? (
              <p className="build-version-note" data-testid="applied-alternative-note">
                Đã áp dụng lựa chọn {appliedAlternativeLabel}. Cấu hình hiện là phiên bản{" "}
                {buildArtifact?.build_version}; hãy xem lại giá và điểm cần lưu ý trước khi tạo
                danh sách mua.
              </p>
            ) : null}

            <ReplacementSuggestions
              response={buildAlternatives}
              isApplying={isLoading}
              onApplyAlternative={handleApplyAlternative}
            />

            {agentAnalysis ? <LlmAgentPanel analysis={agentAnalysis} /> : null}

            {buildArtifact ? (
              <div className="below-workbench">
                <DisplayModeToggle mode={displayMode} onModeChange={setDisplayMode} />

                <CustomerDecisionSummary
                  artifact={buildArtifact}
                  canApprove={canApprove}
                  isCartReady={Boolean(cartHandoff)}
                />

                <PerformanceProfilePanel
                  profile={buildArtifact.performance_profile}
                  isAdvanced={displayMode === "advanced"}
                />

                <AddOnRecommendationsPanel
                  addons={buildArtifact.recommended_addons}
                  isAdvanced={displayMode === "advanced"}
                  selectedSkus={selectedAddOnSkus}
                  disabled={Boolean(cartHandoff)}
                  onToggle={handleToggleAddOn}
                />

                <BuildIterationPanel
                  command={iterationCommand}
                  isLoading={isLoading}
                  lastIteration={lastIteration}
                  onCommandChange={setIterationCommand}
                  onSubmitCommand={handleIterateBuild}
                />

                {displayMode === "advanced" ? (
                  <>
                    <div className="build-notes">
                      <div>
                        <h3>Giải thích</h3>
                        <ul>
                          {buildArtifact.explanations_vi.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h3>Cảnh báo</h3>
                        <ul>
                          {buildArtifact.warnings_vi.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                          {buildArtifact.compatibility_report.results
                            .filter((result) => result.severity !== "pass")
                            .map((result) => (
                              <li key={result.rule_id}>{result.explanation_vi}</li>
                            ))}
                        </ul>
                      </div>
                    </div>
                    <SupportDetailsPanel
                      isOpen={showSupportDetails}
                      trace={sessionTrace}
                      copyState={traceCopyState}
                      orchestrationSteps={buildArtifact.orchestration_trace}
                      optimizerTrace={buildArtifact.optimizer_trace}
                      onCopyExport={handleCopyTraceExport}
                      onToggle={() => setShowSupportDetails((current) => !current)}
                    />
                  </>
                ) : (
                  <CustomerWarningsPanel artifact={buildArtifact} />
                )}

                <BuildFeedbackPanel
                  artifact={buildArtifact}
                  feedback={buildFeedback}
                  isSubmitting={isSubmittingFeedback}
                  onSubmit={handleSubmitFeedback}
                />
              </div>
            ) : null}
          </section>

          <CartSummaryRail
            artifact={buildArtifact}
            cartHandoff={cartHandoff}
            cartItemCount={cartItemCount}
            selectedAddOnTotal={selectedAddOnTotal}
            shoppingTotal={shoppingTotal}
            canApprove={canApprove}
            isLoading={isLoading}
            onApprove={handleApprove}
          />
        </section>

        <section className="commerce-secondary">
          <UpgradePlannerPanel
            currentPc={upgradeCurrentPc}
            budgetText={upgradeBudgetText}
            parseResult={upgradeParse}
            confirmedSystem={confirmedExistingSystem}
            plan={upgradePlan}
            isParsing={isParsingUpgrade}
            isLoading={isPlanningUpgrade}
            onCurrentPcChange={handleUpgradeCurrentPcChange}
            onBudgetChange={setUpgradeBudgetText}
            onParse={handleParseExistingSystem}
            onConfirmedSystemChange={handleConfirmedExistingSystemChange}
            onSubmit={handlePlanGpuUpgrade}
          />
        </section>
      </main>
    </>
  );
}

function CommerceHeader({
  agentStatusLabel,
  agentStatusTone,
  sessionLabel
}: {
  agentStatusLabel: string;
  agentStatusTone: string;
  sessionLabel: string;
}) {
  return (
    <header className="commerce-topbar">
      <div className="commerce-brand">
        <SpecSageLogo />
        <div>
          <strong>SpecSage</strong>
          <span>PC Build Copilot</span>
        </div>
      </div>
      <div className="commerce-userbar" aria-label="Trạng thái">
        <span className="location-pill">
          <SmallIcon name="pin" />
          Phong Vũ Online
        </span>
        <span className={`runtime-pill ${agentStatusTone}`}>{agentStatusLabel}</span>
        <span className="runtime-pill alert">{sessionLabel}</span>
        <button type="button" className="icon-button" aria-label="Trợ giúp">
          <SmallIcon name="help" />
        </button>
        <button type="button" className="icon-button has-dot" aria-label="Thông báo">
          <SmallIcon name="bell" />
        </button>
        <button type="button" className="avatar-button" aria-label="Tài khoản">
          N
        </button>
      </div>
    </header>
  );
}

function IntentControlPanel({
  preset,
  budgetTarget,
  resolution,
  selectedPriorities,
  selectedFeatures,
  message,
  isLoading,
  primaryActionLabel,
  primaryActionHint,
  error,
  textareaRef,
  onSubmit,
  onPresetSelect,
  onBudgetTargetChange,
  onResolutionChange,
  onTogglePriority,
  onToggleFeature,
  onMessageChange
}: {
  preset: UseCase;
  budgetTarget: number;
  resolution: ResolutionOption;
  selectedPriorities: string[];
  selectedFeatures: string[];
  message: string;
  isLoading: boolean;
  primaryActionLabel: string;
  primaryActionHint: string;
  error: string | null;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onPresetSelect: (item: PresetOption) => void;
  onBudgetTargetChange: (budget: number) => void;
  onResolutionChange: (resolution: ResolutionOption) => void;
  onTogglePriority: (priority: string) => void;
  onToggleFeature: (feature: string) => void;
  onMessageChange: (message: string) => void;
}) {
  return (
    <form className="commerce-card intent-console" id="build-copilot" onSubmit={onSubmit}>
      <div className="commerce-card-heading">
        <h2>1. Nhu cầu & Ngân sách</h2>
        <SmallIcon name="info" />
      </div>

      <section className="intent-block">
        <h3>Mục đích chính</h3>
        <div className="use-case-grid" aria-label="Mục đích chính">
          {useCaseCards.map((item) => (
            <button
              key={item.value}
              type="button"
              className={preset === item.value ? "use-case-card selected" : "use-case-card"}
              onClick={() => onPresetSelect(item)}
            >
              <UseCaseIcon name={item.icon} />
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="intent-block">
        <div className="field-row">
          <h3>Ngân sách dự kiến</h3>
          <span>{formatVnd(budgetTarget * 1_000_000)}</span>
        </div>
        <div className="budget-scale">
          <span>20.000.000 đ</span>
          <span>45.000.000 đ</span>
        </div>
        <input
          className="budget-range"
          type="range"
          min={20}
          max={45}
          step={1}
          value={budgetTarget}
          aria-label="Ngân sách dự kiến"
          onChange={(event) => onBudgetTargetChange(Number(event.target.value))}
        />
        <output className="budget-output">{formatVnd(budgetTarget * 1_000_000)}</output>
      </section>

      <section className="intent-block">
        <h3>Độ phân giải mục tiêu</h3>
        <div className="segmented-control" aria-label="Độ phân giải mục tiêu">
          {resolutionOptions.map((option) => (
            <button
              key={option}
              type="button"
              className={resolution === option ? "selected" : ""}
              onClick={() => onResolutionChange(option)}
            >
              {option}
            </button>
          ))}
        </div>
      </section>

      <section className="intent-block">
        <h3>Ưu tiên của bạn</h3>
        <div className="chip-grid" aria-label="Ưu tiên của bạn">
          {priorityOptions.map((priority) => (
            <button
              key={priority}
              type="button"
              className={selectedPriorities.includes(priority) ? "selected" : ""}
              onClick={() => onTogglePriority(priority)}
            >
              {selectedPriorities.includes(priority) ? <SmallIcon name="check" /> : null}
              {priority}
            </button>
          ))}
        </div>
      </section>

      <section className="intent-block">
        <h3>Tính năng cần có</h3>
        <div className="checkbox-grid" aria-label="Tính năng cần có">
          {featureOptions.map((feature) => (
            <label key={feature}>
              <input
                type="checkbox"
                checked={selectedFeatures.includes(feature)}
                onChange={() => onToggleFeature(feature)}
              />
              {feature}
            </label>
          ))}
        </div>
      </section>

      <section className="intent-block">
        <label htmlFor="intent">Ghi chú thêm</label>
        <textarea
          id="intent"
          ref={textareaRef}
          data-testid="intent-input"
          value={message}
          onChange={(event) => onMessageChange(event.target.value)}
          rows={4}
        />
        <span className="textarea-counter">{message.length}/300</span>
      </section>

      {error ? <p className="error">{error}</p> : null}

      <button
        type="submit"
        className="primary-commerce-action"
        data-testid="primary-flow-action"
        disabled={isLoading || !message.trim()}
      >
        <SmallIcon name="spark" />
        {isLoading ? "Đang xử lý..." : primaryActionLabel}
      </button>
      <p className="intent-footnote">{primaryActionHint}</p>
    </form>
  );
}

function CommerceMetricStrip({
  artifact,
  selectedSkuLabel,
  compatibilityLabel
}: {
  artifact: BuildArtifact | null;
  selectedSkuLabel: string;
  compatibilityLabel: string;
}) {
  const fitLabel = artifact ? compactPerformanceFitLabel(artifact.performance_profile.fit_level) : "Chưa có";
  const fitNote = artifact ? compactPerformanceFitNote(artifact.performance_profile) : "Chưa có dữ liệu build";
  const warrantyLabel = artifact ? "36 tháng" : "Chờ build";
  const upgradeLabel = artifact ? upgradeReadinessLabel(artifact) : "Chưa sinh build";
  const upgradeNote = artifact ? compactBudgetHeadroomNote(artifact) : selectedSkuLabel;
  return (
    <div className="commerce-metrics">
      <MetricTile
        label={`Tổng chi phí (${artifact ? artifact.items.length : 0} SP)`}
        value={artifact ? formatVnd(artifact.total_price_vnd) : "0 đ"}
        note={artifact?.budget_status === "within_budget" ? "Trong ngân sách" : "Chờ ngân sách"}
        tone="price"
      />
      <MetricTile
        label="Hiệu năng ước tính"
        value={fitLabel}
        note={fitNote}
        tone="success"
        gauge={artifact ? 92 : 0}
      />
      <MetricTile label="Tương thích" value={compatibilityLabel} note="Không xung đột linh kiện" tone="success" />
      <MetricTile label="Sẵn sàng nâng cấp" value={upgradeLabel} note={upgradeNote} tone="success" gauge={artifact ? 75 : 0} />
      <MetricTile label="Bảo hành dự kiến" value={warrantyLabel} note="Tại Phong Vũ" tone="neutral" />
    </div>
  );
}

function MetricTile({
  label,
  value,
  note,
  tone,
  gauge
}: {
  label: string;
  value: string;
  note: string;
  tone: "price" | "success" | "neutral";
  gauge?: number;
}) {
  const hasGauge = typeof gauge === "number" && gauge > 0;
  return (
    <div className={`metric-tile ${tone}${hasGauge ? " has-gauge" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
      {hasGauge ? (
        <div className="mini-gauge" style={{ "--gauge": `${gauge}%` } as CSSProperties}>
          {gauge}%
        </div>
      ) : null}
    </div>
  );
}

function CommerceProcessSteps({
  hasIntent,
  isConfirmed,
  hasBuild,
  hasCart
}: {
  hasIntent: boolean;
  isConfirmed: boolean;
  hasBuild: boolean;
  hasCart: boolean;
}) {
  const steps = [
    { label: "Phân tích nhu cầu", done: hasIntent },
    { label: "Chọn linh kiện", done: hasBuild },
    { label: "Kiểm tra tương thích", done: hasBuild },
    { label: "Tối ưu hiệu năng", done: hasBuild },
    { label: "Tính toán ngân sách", done: isConfirmed || hasCart }
  ];
  return (
    <div className="commerce-process" aria-label="Quy trình AI Copilot">
      <strong>Quy trình AI Copilot</strong>
      <ol>
        {steps.map((step) => (
          <li key={step.label} className={step.done ? "done" : ""}>
            <span>{step.done ? <SmallIcon name="check" /> : null}</span>
            <div>
              <b>{step.label}</b>
              <small>{step.done ? "Hoàn tất" : "Đang chờ"}</small>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

type BuildTableRow = Pick<BuildItem, "slot" | "sku" | "name" | "price_vnd"> &
  Partial<
    Pick<
      BuildItem,
      "brand" | "image_url" | "stock_quantity" | "stock_status" | "url" | "warranty_text"
    >
  >;

function BuildItemsTable({ artifact }: { artifact: BuildArtifact | null }) {
  const rows = artifact?.items ?? placeholderBuildRows;
  return (
    <section className="parts-board" aria-label="Danh sách linh kiện">
      <div className="parts-board-heading">
        <h2>Danh sách linh kiện</h2>
        <div>
          <button type="button" className="ghost-action" disabled={!artifact}>
            Sửa build
          </button>
          <button type="button" className="ghost-action" disabled={!artifact}>
            Xuất file
          </button>
        </div>
      </div>
      <div className="commerce-table-wrap">
        <table className="commerce-parts-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Linh kiện</th>
              <th>Sản phẩm</th>
              <th>SKU</th>
              <th>Giá</th>
              <th>SL</th>
              <th>Thành tiền</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item, index) => {
              const realItem = artifact ? (item as BuildItem) : null;
              return (
                <tr key={`${item.slot}-${item.sku || index}`} className={!artifact ? "placeholder-row" : ""}>
                  <td>{index + 1}</td>
                  <td>
                    <div className="part-slot">
                      <PartThumb
                        slot={item.slot}
                        imageUrl={realItem?.image_url}
                      />
                      {slotLabel(item.slot)}
                    </div>
                  </td>
                  <td>
                    {realItem ? (
                      <div className="product-cell">
                        <a href={realItem.url} target="_blank" rel="noreferrer">
                          {realItem.name}
                        </a>
                        <div className="product-meta-line">
                          {realItem.brand ? <span>{realItem.brand}</span> : null}
                          {realItem.warranty_text ? <span>BH {realItem.warranty_text}</span> : null}
                          <span className={stockStatusClass(realItem.stock_status)}>
                            {stockStatusLabel(realItem.stock_status, realItem.stock_quantity)}
                          </span>
                        </div>
                      </div>
                    ) : (
                      item.name
                    )}
                  </td>
                  <td>{item.sku || "Chưa chọn"}</td>
                  <td>{item.price_vnd ? formatVnd(item.price_vnd) : "-"}</td>
                  <td>
                    <span className="qty-box">{artifact ? 1 : 0}</span>
                  </td>
                  <td>{item.price_vnd ? formatVnd(item.price_vnd) : "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const placeholderBuildRows: BuildTableRow[] = [
  { slot: "cpu", sku: "", name: "CPU sẽ được chọn sau khi phân tích", price_vnd: 0 },
  { slot: "mainboard", sku: "", name: "Mainboard tương thích socket/RAM", price_vnd: 0 },
  { slot: "ram", sku: "", name: "RAM theo workload và ngân sách", price_vnd: 0 },
  { slot: "vga", sku: "", name: "VGA ưu tiên theo mục tiêu hiệu năng", price_vnd: 0 },
  { slot: "storage", sku: "", name: "SSD/HDD theo nhu cầu lưu trữ", price_vnd: 0 },
  { slot: "psu", sku: "", name: "Nguồn theo công suất và đầu cấp", price_vnd: 0 },
  { slot: "case", sku: "", name: "Case theo clearance linh kiện", price_vnd: 0 },
  { slot: "cooler", sku: "", name: "Tản nhiệt nếu cần theo TDP/case", price_vnd: 0 }
];

function ReplacementSuggestions({
  response,
  isApplying,
  onApplyAlternative
}: {
  response: BuildAlternativesResponse | null;
  isApplying: boolean;
  onApplyAlternative: (alternative: BuildAlternative) => void;
}) {
  const alternatives = response?.alternatives.slice(0, 3) ?? [];
  return (
    <section className="replacement-strip" data-testid="alternatives-panel">
      <h2>Gợi ý thay thế</h2>
      <div className="replacement-grid">
        {alternatives.length ? (
          alternatives.map((alternative) => (
            <button
              key={alternative.variant_id}
              type="button"
              disabled={isApplying || !alternative.can_approve}
              onClick={() => onApplyAlternative(alternative)}
            >
              <span>{alternative.label_vi}</span>
              <strong>{formatDeltaVnd(alternative.price_delta_vnd)}</strong>
              <small>Hiệu năng: {performanceFitLabel(alternative.performance_profile.fit_level)}</small>
            </button>
          ))
        ) : (
          <>
            <div className="replacement-empty">Chưa có lựa chọn thay thế</div>
            <div className="replacement-empty">Sinh build để xem thêm</div>
            <div className="replacement-empty more">Xem thêm</div>
          </>
        )}
      </div>
    </section>
  );
}

function CartSummaryRail({
  artifact,
  cartHandoff,
  cartItemCount,
  selectedAddOnTotal,
  shoppingTotal,
  canApprove,
  isLoading,
  onApprove
}: {
  artifact: BuildArtifact | null;
  cartHandoff: CartReadyHandoff | null;
  cartItemCount: number;
  selectedAddOnTotal: number;
  shoppingTotal: number;
  canApprove: boolean;
  isLoading: boolean;
  onApprove: () => void;
}) {
  return (
    <aside className="cart-column" aria-label="Giỏ build">
      <section className="commerce-card cart-card">
        <div className="cart-heading">
          <h2>Giỏ build ({cartItemCount})</h2>
          <SmallIcon name="chevron" />
        </div>
        <dl className="cart-totals">
          <div>
            <dt>Tạm tính</dt>
            <dd>{artifact ? formatVnd(artifact.total_price_vnd) : "0 đ"}</dd>
          </div>
          <div>
            <dt>Gợi ý thêm</dt>
            <dd>{selectedAddOnTotal ? formatVnd(selectedAddOnTotal) : "0 đ"}</dd>
          </div>
          <div className="grand-total">
            <dt>Tổng cộng</dt>
            <dd>{artifact ? formatVnd(shoppingTotal) : "0 đ"}</dd>
          </div>
        </dl>
        <button
          type="button"
          className="add-cart-button"
          data-testid="approve-build"
          disabled={isLoading || !canApprove}
          onClick={onApprove}
        >
          <SmallIcon name="cart" />
          {cartHandoff ? "Đã tạo danh sách" : "Thêm tất cả vào giỏ hàng"}
        </button>
        <button type="button" className="secondary-cart-button" disabled={!cartHandoff}>
          Xem giỏ hàng
        </button>
        <ul className="service-list">
          <li>
            <SmallIcon name="build" />
            <div>
              <strong>Miễn phí lắp ráp</strong>
              <span>Kiểm tra & cài đặt</span>
            </div>
          </li>
          <li>
            <SmallIcon name="shield" />
            <div>
              <strong>Bảo hành chính hãng</strong>
              <span>36 tháng tại Phong Vũ</span>
            </div>
          </li>
          <li>
            <SmallIcon name="support" />
            <div>
              <strong>Hỗ trợ kỹ thuật 24/7</strong>
              <span>1900 2164</span>
            </div>
          </li>
          <li>
            <SmallIcon name="card" />
            <div>
              <strong>Trả góp 0%</strong>
              <span>Qua thẻ tín dụng</span>
            </div>
          </li>
        </ul>
      </section>

      <section className="commerce-card build-info-card">
        <h2>Thông tin build</h2>
        <dl>
          <div>
            <dt>ID build</dt>
            <dd>{artifact ? shortId(artifact.build_id) : "-"}</dd>
          </div>
          <div>
            <dt>Tạo lúc</dt>
            <dd>{artifact ? formatShortDate(artifact.generated_at) : "-"}</dd>
          </div>
          <div>
            <dt>Cập nhật</dt>
            <dd>{artifact ? formatShortDate(artifact.generated_at) : "-"}</dd>
          </div>
          <div>
            <dt>Trạng thái</dt>
            <dd>{artifact ? buildStatusLabel(artifact) : "Chờ build"}</dd>
          </div>
          <div>
            <dt>Copilot</dt>
            <dd>SpecSage AI v1.0</dd>
          </div>
        </dl>
      </section>

      {cartHandoff ? <CartReadyPanel handoff={cartHandoff} /> : null}
    </aside>
  );
}

function UseCaseIcon({ name }: { name: "gamepad" | "creator" | "office" | "ai" }) {
  return (
    <span className="use-case-icon" aria-hidden="true">
      <SmallIcon name={name} />
    </span>
  );
}

function PartThumb({
  slot,
  imageUrl
}: {
  slot: BuildItem["slot"];
  imageUrl?: string | null;
}) {
  return <ProductThumb token={slot} imageUrl={imageUrl} label={slotLabel(slot)} />;
}

function ProductThumb({
  token,
  imageUrl,
  label
}: {
  token: string;
  imageUrl?: string | null;
  label: string;
}) {
  return (
    <span className={`part-thumb ${token} ${imageUrl ? "has-image" : ""}`} aria-hidden="true">
      {imageUrl ? (
        <img
          src={imageUrl}
          alt=""
          loading="lazy"
          decoding="async"
          onError={(event) => {
            event.currentTarget.dataset.failed = "true";
            event.currentTarget.parentElement?.classList.add("image-failed");
          }}
        />
      ) : null}
      <span className="part-thumb-fallback">{label.slice(0, 1)}</span>
    </span>
  );
}

function SmallIcon({
  name
}: {
  name:
    | "ai"
    | "bell"
    | "build"
    | "card"
    | "cart"
    | "check"
    | "chevron"
    | "creator"
    | "gamepad"
    | "help"
    | "info"
    | "office"
    | "pin"
    | "shield"
    | "spark"
    | "support";
}) {
  const paths: Record<typeof name, string> = {
    ai: "M8 9a4 4 0 0 1 8 0v2a4 4 0 0 1-8 0V9Zm1 8h6m-3-2v4m-7-9H3m18 0h-2M7 4 5.5 2.5M17 4l1.5-1.5M7 18l-1.5 1.5M17 18l1.5 1.5",
    bell: "M18 16v-5a6 6 0 0 0-12 0v5l-2 2h16l-2-2Zm-8 4h4",
    build: "m14 7 3-3 3 3-3 3-3-3ZM4 18h16M6 18v-7h12v7",
    card: "M3 7h18v10H3V7Zm0 3h18M7 14h4",
    cart: "M3 4h2l2 11h10l2-7H7m2 11a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm8 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z",
    check: "m5 12 4 4L19 6",
    chevron: "m8 10 4 4 4-4",
    creator: "M5 17 17 5l2 2L7 19H5v-2Zm10-10 2 2M4 21h16",
    gamepad: "M7 9h10a4 4 0 0 1 4 4v2a3 3 0 0 1-5 2l-2-2h-4l-2 2a3 3 0 0 1-5-2v-2a4 4 0 0 1 4-4Zm1 4h4M10 11v4m6-2h.01M18 15h.01",
    help: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-5v.01M9.8 9a2.2 2.2 0 1 1 3.6 1.7c-.9.6-1.4 1-1.4 2.3",
    info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-10v6m0-9v.01",
    office: "M4 21V5h10v16M14 9h6v12M7 9h3m-3 4h3m-3 4h3m7-4h2m-2 4h2",
    pin: "M12 21s7-5.1 7-11a7 7 0 1 0-14 0c0 5.9 7 11 7 11Zm0-8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
    shield: "M12 3 5 6v6c0 4 2.7 7.4 7 9 4.3-1.6 7-5 7-9V6l-7-3Z",
    spark: "M12 2 9.8 8.8 3 11l6.8 2.2L12 20l2.2-6.8L21 11l-6.8-2.2L12 2Z",
    support: "M4 12a8 8 0 0 1 16 0v4a3 3 0 0 1-3 3h-2v-6h5M4 13h5v6H7a3 3 0 0 1-3-3v-4Zm8 8h2"
  };
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d={paths[name]} />
    </svg>
  );
}

function SpecSageLogo() {
  return (
    <svg
      className="brand-mark"
      viewBox="0 0 48 48"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="5" y="5" width="38" height="38" rx="10" fill="#ef4136" />
      <path
        d="M31.5 14.5H19.7l-5.2 5.2v5.1l5 5h9l3.1 3.1-3.7 3.7H16.7"
        fill="none"
        stroke="#ffffff"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="4"
      />
      <path
        d="M16.5 33.5h11.8l5.2-5.2v-5.1l-5-5h-9l-3.1-3.1 3.7-3.7h11.2"
        fill="none"
        stroke="#ffffff"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="4"
      />
      <circle cx="35" cy="13" r="2" fill="#ffffff" />
      <circle cx="13" cy="35" r="2" fill="#ffffff" />
    </svg>
  );
}

function FlowProgress({
  hasSession,
  isConfirmed,
  hasBuild,
  isCartReady
}: {
  hasSession: boolean;
  isConfirmed: boolean;
  hasBuild: boolean;
  isCartReady: boolean;
}) {
  const steps = [
    { label: "Phiên", active: hasSession, done: hasSession },
    { label: "Nhu cầu", active: hasSession && !isConfirmed, done: isConfirmed },
    { label: "Cấu hình", active: isConfirmed && !hasBuild, done: hasBuild },
    { label: "Danh sách mua", active: hasBuild && !isCartReady, done: isCartReady }
  ];

  return (
    <nav className="flow-progress" aria-label="Tiến trình tư vấn">
      {steps.map((step, index) => (
        <div
          key={step.label}
          className={
            step.done ? "flow-step done" : step.active ? "flow-step active" : "flow-step"
          }
        >
          <span className="flow-step-dot">{step.done ? "✓" : index + 1}</span>
          <span className="flow-step-label">{step.label}</span>
        </div>
      ))}
    </nav>
  );
}

function DisplayModeToggle({
  mode,
  onModeChange
}: {
  mode: DisplayMode;
  onModeChange: (mode: DisplayMode) => void;
}) {
  return (
    <div className="display-mode-toggle" aria-label="Chế độ xem">
      <button
        type="button"
        className={mode === "basic" ? "selected" : ""}
        data-testid="view-basic"
        onClick={() => onModeChange("basic")}
      >
        Cơ bản
      </button>
      <button
        type="button"
        className={mode === "advanced" ? "selected" : ""}
        data-testid="view-advanced"
        onClick={() => onModeChange("advanced")}
      >
        Chi tiết kỹ thuật
      </button>
    </div>
  );
}

function CustomerDecisionSummary({
  artifact,
  canApprove,
  isCartReady
}: {
  artifact: BuildArtifact;
  canApprove: boolean;
  isCartReady: boolean;
}) {
  const budgetTone =
    artifact.budget_status === "within_budget"
      ? "good"
      : artifact.budget_status === "over_budget"
        ? "warning"
        : "neutral";
  const budgetValue =
    artifact.budget_status === "within_budget"
      ? "Trong ngân sách"
      : artifact.budget_status === "over_budget"
        ? `Vượt ${formatVnd(Math.abs(artifact.budget_gap_vnd))}`
        : "Chưa có ngân sách";
  const nextAction = isCartReady
    ? "Danh sách sản phẩm đã sẵn sàng."
    : canApprove
      ? "Có thể tạo danh sách mua khi bạn muốn giữ cấu hình này."
      : "Xem điểm cần lưu ý trước khi mua.";
  const fitTone =
    artifact.performance_profile.fit_level === "good"
      ? "good"
      : artifact.performance_profile.fit_level === "adequate"
        ? "warning"
        : artifact.performance_profile.fit_level === "limited"
          ? "danger"
          : "neutral";

  return (
    <section className="customer-decision-summary" data-testid="customer-decision-summary">
      <div className="customer-decision-copy">
        <h3>Có nên chọn cấu hình này?</h3>
        <p>
          Cấu hình đã được kiểm tra theo ngân sách, độ phù hợp với nhu cầu và các cảnh báo
          chính trước khi bạn tạo danh sách mua.
        </p>
      </div>
      <div className="customer-decision-grid">
        <DecisionItem label="Tổng giá" value={formatVnd(artifact.total_price_vnd)} tone="neutral" />
        <DecisionItem
          label="Mức phù hợp"
          value={performanceFitLabel(artifact.performance_profile.fit_level)}
          tone={fitTone}
        />
        <DecisionItem label="Ngân sách" value={budgetValue} tone={budgetTone} />
        <DecisionItem label="Bước tiếp theo" value={nextAction} tone={canApprove ? "good" : "warning"} />
      </div>
    </section>
  );
}

function DecisionItem({
  label,
  value,
  tone
}: {
  label: string;
  value: string;
  tone: "good" | "warning" | "danger" | "neutral";
}) {
  return (
    <div className={`decision-item ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

const positiveFeedbackReasons: Array<{ value: BuildFeedbackReason; label: string }> = [
  { value: "fits_need", label: "Đúng nhu cầu" },
  { value: "good_value", label: "Tối ưu giá" },
  { value: "clear_explanation", label: "Dễ hiểu" }
];

const negativeFeedbackReasons: Array<{ value: BuildFeedbackReason; label: string }> = [
  { value: "confusing_explanation", label: "Giải thích chưa rõ" },
  { value: "wrong_performance_fit", label: "Chưa đúng hiệu năng" },
  { value: "over_budget", label: "Ngân sách chưa ổn" },
  { value: "missing_part", label: "Thiếu linh kiện" },
  { value: "compatibility_concern", label: "Lo tương thích" },
  { value: "price_or_stock_concern", label: "Giá/tồn kho cần kiểm tra" },
  { value: "other", label: "Lý do khác" }
];

function BuildFeedbackPanel({
  artifact,
  feedback,
  isSubmitting,
  onSubmit
}: {
  artifact: BuildArtifact;
  feedback: BuildFeedback | null;
  isSubmitting: boolean;
  onSubmit: (payload: BuildFeedbackRequest) => void;
}) {
  const [rating, setRating] = useState<BuildFeedbackRating | null>(null);
  const [reasonTags, setReasonTags] = useState<BuildFeedbackReason[]>([]);
  const [comment, setComment] = useState("");
  const [partRatings, setPartRatings] = useState<Record<string, BuildFeedbackRating>>({});
  const reasonOptions =
    rating === "thumbs_down" ? negativeFeedbackReasons : positiveFeedbackReasons;

  function handleRating(nextRating: BuildFeedbackRating) {
    setRating(nextRating);
    setReasonTags([]);
  }

  function toggleReason(reason: BuildFeedbackReason) {
    setReasonTags((current) =>
      current.includes(reason)
        ? current.filter((item) => item !== reason)
        : [...current, reason]
    );
  }

  function togglePartRating(item: BuildItem, nextRating: BuildFeedbackRating) {
    const key = feedbackPartKey(item);
    setPartRatings((current) => {
      const next = { ...current };
      if (next[key] === nextRating) {
        delete next[key];
      } else {
        next[key] = nextRating;
      }
      return next;
    });
  }

  function handleSubmitFeedback() {
    if (!rating) return;
    const part_feedback: PartFeedbackRequest[] = artifact.items.flatMap((item) => {
      const selectedRating = partRatings[feedbackPartKey(item)];
      if (!selectedRating) return [];
      return [
        {
          slot: item.slot,
          sku: item.sku,
          rating: selectedRating
        }
      ];
    });
    onSubmit({
      rating,
      reason_tags: reasonTags,
      comment_vi: comment.trim() ? comment.trim() : null,
      part_feedback
    });
  }

  if (feedback) {
    return (
      <section className="feedback-panel saved" data-testid="feedback-panel">
        <div className="feedback-heading">
          <div>
            <h3>Đánh giá cấu hình</h3>
            <p>Đã ghi nhận góp ý cho cấu hình phiên bản {feedback.build_version}.</p>
          </div>
          <span
            className={
              feedback.review_queue_status === "queued" ? "status warning" : "status confirmed"
            }
          >
            {feedback.review_queue_status === "queued"
              ? "Đang được xem lại"
              : "Đã ghi nhận"}
          </span>
        </div>
        <div className="feedback-saved-grid">
          <Metric
            label="Đánh giá"
            value={feedback.rating === "thumbs_up" ? "Hữu ích" : "Chưa phù hợp"}
          />
          <Metric label="Linh kiện" value={`${feedback.part_feedback.length} mục`} />
          <Metric label="Phiên bản" value={`v${feedback.build_version}`} />
          <Metric
            label="Trạng thái"
            value={feedback.review_queue_status === "queued" ? "Đang xem lại" : "Đã ghi nhận"}
          />
        </div>
        {feedback.review_queue_reason_vi ? <p>{friendlyFeedbackReason(feedback.review_queue_reason_vi)}</p> : null}
      </section>
    );
  }

  return (
    <section className="feedback-panel" data-testid="feedback-panel">
      <div className="feedback-heading">
        <div>
          <h3>Góp ý về cấu hình</h3>
          <p>Cho biết cấu hình này có đúng nhu cầu không để đội tư vấn cải thiện đề xuất.</p>
        </div>
        <span className="status">Phiên bản {artifact.build_version}</span>
      </div>

      <div className="feedback-rating-row" aria-label="Đánh giá tổng thể">
        <button
          type="button"
          className={rating === "thumbs_up" ? "selected" : ""}
          data-testid="feedback-thumbs-up"
          onClick={() => handleRating("thumbs_up")}
        >
          Hữu ích
        </button>
        <button
          type="button"
          className={rating === "thumbs_down" ? "selected" : ""}
          data-testid="feedback-thumbs-down"
          onClick={() => handleRating("thumbs_down")}
        >
          Chưa phù hợp
        </button>
      </div>

      {rating ? (
        <div className="feedback-reasons" aria-label="Lý do đánh giá">
          {reasonOptions.map((reason) => (
            <button
              key={reason.value}
              type="button"
              className={reasonTags.includes(reason.value) ? "selected" : ""}
              data-testid={`feedback-reason-${reason.value}`}
              onClick={() => toggleReason(reason.value)}
            >
              {reason.label}
            </button>
          ))}
        </div>
      ) : null}

      <div className="feedback-parts">
        <h4>Đánh giá từng linh kiện</h4>
        <div className="feedback-part-list">
          {artifact.items.map((item) => {
            const selectedRating = partRatings[feedbackPartKey(item)];
            return (
              <div className="feedback-part-row" key={`${item.slot}-${item.sku}`}>
                <div>
                  <strong>{slotLabel(item.slot)}</strong>
                  <span>{item.name}</span>
                  <small>{item.sku}</small>
                </div>
                <div className="feedback-part-actions">
                  <button
                    type="button"
                    className={selectedRating === "thumbs_up" ? "selected" : ""}
                    data-testid={`part-feedback-${item.slot}-up`}
                    onClick={() => togglePartRating(item, "thumbs_up")}
                  >
                    Ổn
                  </button>
                  <button
                    type="button"
                    className={selectedRating === "thumbs_down" ? "selected" : ""}
                    data-testid={`part-feedback-${item.slot}-down`}
                    onClick={() => togglePartRating(item, "thumbs_down")}
                  >
                    Xem lại
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <label htmlFor="feedback-comment">Ghi chú thêm</label>
      <textarea
        id="feedback-comment"
        data-testid="feedback-comment"
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        rows={4}
      />

      <div className="feedback-submit-row">
        <button
          type="button"
          data-testid="submit-feedback"
          disabled={isSubmitting || !rating}
          onClick={handleSubmitFeedback}
        >
          {isSubmitting ? "Đang gửi..." : "Gửi góp ý"}
        </button>
      </div>
    </section>
  );
}

function TraceReplayPanel({
  trace,
  copyState,
  onCopyExport
}: {
  trace: SessionTraceReplay;
  copyState: "idle" | "copied" | "failed";
  onCopyExport: () => void;
}) {
  const totalEvents = trace.builds.reduce((count, build) => count + build.events.length, 0);

  return (
    <section className="trace-replay" data-testid="trace-replay-panel">
      <div className="trace-replay-heading">
        <div>
          <h3>Nhật ký hỗ trợ</h3>
          <p>{trace.redaction_policy_vi}</p>
        </div>
        <div className="trace-replay-actions">
          <span className="status">
            {trace.generated_build_count} cấu hình / {totalEvents} bước
          </span>
          <button type="button" className="secondary" onClick={onCopyExport}>
            {copyState === "copied"
              ? "Đã copy nhật ký"
              : copyState === "failed"
                ? "Không copy được"
                : "Copy nhật ký hỗ trợ"}
          </button>
        </div>
      </div>

      <div className="trace-builds">
        {trace.builds.map((build) => (
          <article className="trace-build-card" key={build.build_id}>
            <div className="trace-build-card-heading">
              <div>
                <h4>Phiên bản {build.build_version}</h4>
                <p>{build.build_id}</p>
              </div>
              <span className={build.replay_status === "complete" ? "status confirmed" : "status"}>
                {build.replay_status === "complete" ? `${build.events.length} bước` : "Không có bước"}
              </span>
            </div>

            {build.events.length ? (
              <ol className="trace-event-list">
                {build.events.map((event) => (
                  <TraceReplayEventRow event={event} key={event.event_id} />
                ))}
              </ol>
            ) : (
              <p className="trace-empty">
                Phiên bản này được tạo từ thao tác đổi linh kiện nên không có nhật ký xử lý riêng.
              </p>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function TraceReplayEventRow({ event }: { event: TraceReplayEvent }) {
  const labels: Record<TraceReplayEvent["agent"], string> = {
    intent: "Nhu cầu",
    catalog: "Sản phẩm",
    optimizer: "Tối ưu",
    compatibility: "Tương thích",
    performance: "Hiệu năng",
    explainer: "Giải thích",
    commerce: "Mua hàng",
    validator: "Kiểm tra cuối"
  };

  return (
    <li>
      <div className="trace-event-main">
        <span className={event.status === "completed" ? "trace-dot" : "trace-dot blocked"} />
        <div>
          <div className="trace-event-title">
            <strong>
              {event.sequence}. {labels[event.agent]}
            </strong>
            <span>{event.latency_ms} ms</span>
          </div>
          <p>{event.summary_vi}</p>
          <dl className="trace-event-facts">
            <div>
              <dt>Model</dt>
              <dd>{event.model_version}</dd>
            </div>
            <div>
              <dt>Công cụ</dt>
              <dd>{event.tool_calls.length ? event.tool_calls.join(", ") : "Không có"}</dd>
            </div>
          </dl>
          <details className="trace-event-payload">
            <summary>Dữ liệu vào / ra</summary>
            <div>
              <pre>{formatPayload(event.inputs_redacted)}</pre>
              <pre>{formatPayload(event.outputs_redacted)}</pre>
            </div>
          </details>
        </div>
      </div>
    </li>
  );
}

function AgentTracePanel({ steps }: { steps: BuildOrchestrationStep[] }) {
  const labels: Record<BuildOrchestrationStep["agent"], string> = {
    intent: "Nhu cầu",
    catalog: "Sản phẩm",
    optimizer: "Tối ưu",
    compatibility: "Tương thích",
    performance: "Hiệu năng",
    explainer: "Giải thích",
    commerce: "Mua hàng",
    validator: "Kiểm tra cuối"
  };

  return (
    <section className="agent-trace" data-testid="agent-trace-panel">
      <div className="agent-trace-heading">
        <div>
          <h3>Các bước xử lý</h3>
          <p>Hệ thống tách từng bước để chọn linh kiện, kiểm tra tương thích và giải thích kết quả.</p>
        </div>
        <span className="status">{steps.length} bước</span>
      </div>
      <ol className="agent-trace-list">
        {steps.map((step) => (
          <li key={`${step.agent}-${step.summary_vi}`}>
            <span className={step.status === "completed" ? "trace-dot" : "trace-dot blocked"} />
            <div>
              <strong>{labels[step.agent]}</strong>
              <p>{step.summary_vi}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function OptimizerTracePanel({ trace }: { trace: OptimizerTrace }) {
  const weights = Object.entries(trace.budget_allocation.weights);
  const decisions = trace.iterations.slice(0, 8);

  return (
    <section className="optimizer-trace" data-testid="optimizer-trace-panel">
      <div className="optimizer-trace-heading">
        <div>
          <h3>Quyết định tối ưu</h3>
          <p>Chi tiết cách ngân sách, ưu tiên và từng lựa chọn linh kiện được xét trước khi chốt.</p>
        </div>
        <span className="status">
          {trace.applied_iteration_count}/{trace.max_iterations} vòng áp dụng
        </span>
      </div>

      <div className="optimizer-summary-grid">
        <Metric label="Nhu cầu" value={trace.budget_allocation.use_case} />
        <Metric
          label="Ưu tiên"
          value={trace.priority_overrides.length ? trace.priority_overrides.join(", ") : "Không có"}
        />
        <Metric label="Không chọn" value={`${trace.rejected_iteration_count}`} />
      </div>

      <div className="optimizer-weights" aria-label="Phân bổ ngân sách">
        {weights.map(([slot, weight]) => (
          <div key={slot}>
            <span>{slotLabel(slot as BuildItem["slot"])}</span>
            <strong>{weight}%</strong>
          </div>
        ))}
      </div>

      <ul className="optimizer-notes">
        {trace.budget_allocation.notes_vi.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>

      {decisions.length ? (
        <ol className="optimizer-decisions">
          {decisions.map((decision, index) => (
            <li key={`${decision.iteration}-${decision.candidate_kind ?? "skip"}-${index}`}>
              <span className={`decision-badge ${decision.decision}`}>{decisionLabel(decision.decision)}</span>
              <div>
                <strong>
                  Vòng {decision.iteration}
                  {decision.candidate_label_vi ? ` · ${decision.candidate_label_vi}` : ""}
                </strong>
                <p>{decision.reason_vi}</p>
                {decision.score !== null ? (
                  <small>
                    Score {decision.score}/100
                    {decision.price_delta_vnd !== null
                      ? ` · ${formatDeltaVnd(decision.price_delta_vnd)}`
                      : ""}
                  </small>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="optimizer-empty">Chưa cần thử thêm lựa chọn trong lượt này.</p>
      )}
    </section>
  );
}

function SupportDetailsPanel({
  isOpen,
  trace,
  copyState,
  orchestrationSteps,
  optimizerTrace,
  onCopyExport,
  onToggle
}: {
  isOpen: boolean;
  trace: SessionTraceReplay | null;
  copyState: "idle" | "copied" | "failed";
  orchestrationSteps: BuildOrchestrationStep[];
  optimizerTrace: OptimizerTrace | null;
  onCopyExport: () => void;
  onToggle: () => void;
}) {
  const hasDetails = Boolean(trace || orchestrationSteps.length || optimizerTrace);
  if (!hasDetails) return null;

  return (
    <section className="support-details" data-testid="support-details-panel">
      <div className="support-details-heading">
        <div>
          <h3>Chi tiết kỹ thuật</h3>
          <p>Thông tin dành cho nhân viên hỗ trợ khi cần kiểm tra lại cách cấu hình được tạo.</p>
        </div>
        <button
          type="button"
          className="secondary"
          data-testid="toggle-support-details"
          onClick={onToggle}
        >
          {isOpen ? "Ẩn chi tiết" : "Hiện chi tiết kỹ thuật"}
        </button>
      </div>

      {isOpen ? (
        <div className="support-details-stack">
          {trace ? (
            <TraceReplayPanel trace={trace} copyState={copyState} onCopyExport={onCopyExport} />
          ) : null}
          {orchestrationSteps.length ? (
            <AgentTracePanel steps={orchestrationSteps} />
          ) : null}
          {optimizerTrace ? <OptimizerTracePanel trace={optimizerTrace} /> : null}
        </div>
      ) : null}
    </section>
  );
}

function UpgradePlannerPanel({
  currentPc,
  budgetText,
  parseResult,
  confirmedSystem,
  plan,
  isParsing,
  isLoading,
  onCurrentPcChange,
  onBudgetChange,
  onParse,
  onConfirmedSystemChange,
  onSubmit
}: {
  currentPc: string;
  budgetText: string;
  parseResult: ExistingSystemParseResponse | null;
  confirmedSystem: ExistingSystemOverrides;
  plan: UpgradePlanResponse | null;
  isParsing: boolean;
  isLoading: boolean;
  onCurrentPcChange: (value: string) => void;
  onBudgetChange: (value: string) => void;
  onParse: () => void;
  onConfirmedSystemChange: <K extends keyof ExistingSystemOverrides>(
    field: K,
    value: ExistingSystemOverrides[K]
  ) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const recommendation = plan?.recommendations[0] ?? null;
  const canPlan = Boolean(parseResult && currentPc.trim());

  return (
    <section className="panel upgrade-panel" data-testid="upgrade-planner-panel">
      <div className="panel-heading">
        <div>
          <h2>Nâng cấp GPU</h2>
          <p>Nhập cấu hình hiện tại để chọn GPU thật từ catalog và kiểm tra PSU/case.</p>
        </div>
        {plan ? (
          <span className={recommendation ? upgradeStatusClass(recommendation.compatibility_status) : "status warning"}>
            {recommendation ? upgradeStatusLabel(recommendation.compatibility_status) : "Chưa có GPU"}
          </span>
        ) : (
          <span className="status">Phase 7</span>
        )}
      </div>

      <form className="upgrade-form" onSubmit={onSubmit}>
        <label htmlFor="upgrade-current-pc">Máy hiện tại</label>
        <textarea
          id="upgrade-current-pc"
          data-testid="upgrade-current-pc"
          value={currentPc}
          onChange={(event) => onCurrentPcChange(event.target.value)}
          rows={3}
        />

        <div className="upgrade-actions-row">
          <button type="button" className="secondary" disabled={isParsing || !currentPc.trim()} onClick={onParse}>
            {isParsing ? "Đang tóm tắt..." : "Tóm tắt cấu hình"}
          </button>
          <span className={parseResult ? "status confirmed" : "status warning"}>
            {parseResult ? "Đã tóm tắt" : "Cần tóm tắt"}
          </span>
        </div>

        {parseResult ? (
          <div className="upgrade-confirmation" data-testid="upgrade-confirmation">
            <div className="upgrade-confirmation-heading">
              <div>
                <h3>Cấu hình đã nhận diện</h3>
                <p>{parseResult.summary_vi}</p>
              </div>
              <span className={parseResult.existing_system.unknown_fields.length ? "status warning" : "status confirmed"}>
                {parseResult.existing_system.unknown_fields.length
                  ? `${parseResult.existing_system.unknown_fields.length} unknown`
                  : "Đủ dữ liệu"}
              </span>
            </div>

            <div className="upgrade-confirmation-grid">
              <label>
                CPU
                <input
                  value={confirmedSystem.cpu_name ?? ""}
                  onChange={(event) => onConfirmedSystemChange("cpu_name", emptyToNull(event.target.value))}
                />
              </label>
              <label>
                Mainboard
                <input
                  value={confirmedSystem.mainboard_name ?? ""}
                  onChange={(event) => onConfirmedSystemChange("mainboard_name", emptyToNull(event.target.value))}
                />
              </label>
              <label>
                RAM GB
                <input
                  inputMode="numeric"
                  value={confirmedSystem.ram_gb ?? ""}
                  onChange={(event) => onConfirmedSystemChange("ram_gb", parseOptionalNumber(event.target.value))}
                />
              </label>
              <label>
                GPU hiện tại
                <input
                  value={confirmedSystem.gpu_name ?? ""}
                  onChange={(event) => onConfirmedSystemChange("gpu_name", emptyToNull(event.target.value))}
                />
              </label>
              <label>
                PSU W
                <input
                  inputMode="numeric"
                  value={confirmedSystem.psu_wattage_w ?? ""}
                  onChange={(event) => onConfirmedSystemChange("psu_wattage_w", parseOptionalNumber(event.target.value))}
                />
              </label>
              <label>
                PCIe 8-pin
                <input
                  inputMode="numeric"
                  value={confirmedSystem.psu_pcie_8pin_connectors ?? ""}
                  onChange={(event) =>
                    onConfirmedSystemChange("psu_pcie_8pin_connectors", parseOptionalNumber(event.target.value))
                  }
                />
              </label>
              <label>
                Case GPU mm
                <input
                  inputMode="numeric"
                  value={confirmedSystem.case_gpu_clearance_mm ?? ""}
                  onChange={(event) =>
                    onConfirmedSystemChange("case_gpu_clearance_mm", parseOptionalNumber(event.target.value))
                  }
                />
              </label>
              <label>
                Lưu trữ
                <input
                  value={confirmedSystem.storage_summary ?? ""}
                  onChange={(event) => onConfirmedSystemChange("storage_summary", emptyToNull(event.target.value))}
                />
              </label>
            </div>

            {parseResult.warnings_vi.length ? (
              <div className="upgrade-parse-warning">
                {parseResult.warnings_vi.map((warning) => (
                  <span key={warning}>{warning}</span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="upgrade-budget-row">
          <div>
            <label htmlFor="upgrade-budget">Ngân sách nâng GPU</label>
            <input
              id="upgrade-budget"
              inputMode="numeric"
              data-testid="upgrade-budget"
              value={budgetText}
              onChange={(event) => onBudgetChange(event.target.value)}
            />
          </div>
          <button type="submit" disabled={isLoading || isParsing || !canPlan}>
            {isLoading ? "Đang kiểm tra..." : "Lập kế hoạch nâng GPU"}
          </button>
        </div>
      </form>

      {plan ? (
        <div className="upgrade-result" data-testid="upgrade-plan-result">
          <div className="build-metrics compact">
            <Metric label="Catalog" value={plan.catalog_version} />
            <Metric label="Chi phí GPU" value={formatVnd(plan.total_upgrade_cost_vnd)} />
            <Metric label="Thiếu dữ liệu" value={`${plan.existing_system.unknown_fields.length} mục`} />
          </div>

          {recommendation ? (
            <article className="upgrade-recommendation">
              <div className="upgrade-recommendation-heading">
                <div>
                  <span className="addon-kind">GPU đề xuất</span>
                  <h3>
                    <a href={recommendation.url} target="_blank" rel="noreferrer">
                      {recommendation.name}
                    </a>
                  </h3>
                </div>
                <strong>{formatVnd(recommendation.price_vnd)}</strong>
              </div>

              <div className="risk-tags" aria-label="Đánh giá nâng cấp">
                <span className={upgradeStatusClass(recommendation.compatibility_status)}>
                  {upgradeStatusLabel(recommendation.compatibility_status)}
                </span>
                <span className="risk-tag neutral">{upgradeImpactLabel(recommendation.impact)}</span>
                <span className="risk-tag neutral">
                  {specConfidenceLabel(recommendation.specs_confidence)}
                </span>
              </div>

              <ul className="upgrade-reasons">
                {recommendation.reasons_vi.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>

              <div className="upgrade-checks">
                {recommendation.checks.map((check) => (
                  <div className={`upgrade-check ${check.status}`} key={check.code}>
                    <strong>{upgradeStatusLabel(check.status)}</strong>
                    <span>{check.explanation_vi}</span>
                  </div>
                ))}
              </div>
            </article>
          ) : (
            <p className="empty">Chưa tìm được GPU phù hợp ngân sách trong catalog hiện tại.</p>
          )}

          <div className="upgrade-decisions">
            <h3>Giữ hay thay linh kiện</h3>
            <div className="upgrade-decision-grid">
              {plan.reuse_decisions.map((decision) => (
                <div className="upgrade-decision" key={`${decision.slot}-${decision.decision}`}>
                  <strong>{slotLabel(decision.slot)}</strong>
                  <span>{upgradeDecisionLabel(decision.decision)}</span>
                  <p>{decision.reason_vi}</p>
                </div>
              ))}
            </div>
          </div>

          {plan.warnings_vi.length ? (
            <div className="customer-warning-panel compact">
              <h3>Điểm cần xác nhận</h3>
              <ul>
                {plan.warnings_vi.slice(0, 4).map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="upgrade-next-steps">
            {plan.next_steps_vi.map((step) => (
              <span key={step}>{step}</span>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function AddOnRecommendationsPanel({
  addons,
  isAdvanced,
  selectedSkus,
  disabled,
  onToggle
}: {
  addons: BuildRecommendedAddOn[];
  isAdvanced: boolean;
  selectedSkus: string[];
  disabled: boolean;
  onToggle: (sku: string, checked: boolean) => void;
}) {
  if (!addons.length) return null;
  const selected = new Set(selectedSkus);

  return (
    <section className="addon-panel" data-testid="addon-recommendations">
      <div className="addon-heading">
        <div>
          <h3>Gợi ý thêm</h3>
          <p>Không tính vào tổng giá PC; dùng khi bạn muốn mua thêm cùng cấu hình.</p>
        </div>
        <span className="status">{addons.length} tùy chọn</span>
      </div>

      <div className="addon-grid">
        {addons.map((addon) => (
          <article className="addon-card" key={`${addon.kind}-${addon.sku}`}>
            <div className="addon-card-heading">
              <div className="addon-title-row">
                <ProductThumb
                  token={`addon-${addon.kind}`}
                  imageUrl={addon.image_url}
                  label={addonKindLabel(addon.kind)}
                />
                <div>
                  <span className="addon-kind">{addonKindLabel(addon.kind)}</span>
                  <h4>
                    <a href={addon.url} target="_blank" rel="noreferrer">
                      {addon.name}
                    </a>
                  </h4>
                  <div className="product-meta-line">
                    {addon.brand ? <span>{addon.brand}</span> : null}
                    {addon.warranty_text ? <span>BH {addon.warranty_text}</span> : null}
                    <span className={stockStatusClass(addon.stock_status)}>
                      {stockStatusLabel(addon.stock_status, addon.stock_quantity)}
                    </span>
                  </div>
                </div>
              </div>
              <strong>{formatVnd(addon.price_vnd)}</strong>
            </div>

            <p>{addon.reason_vi}</p>

            <div className="addon-tags" aria-label="Trạng thái gợi ý">
              <span className="risk-tag ok">Tùy chọn</span>
              {addon.warnings_vi.length ? (
                <span className="risk-tag warning" title={addon.warnings_vi[0]}>
                  Cần xem lại
                </span>
              ) : null}
              {isAdvanced ? (
                <span className="risk-tag neutral" title="Mức đầy đủ thông số trong snapshot">
                  {specConfidenceLabel(addon.specs_confidence)}
                </span>
              ) : null}
            </div>

            {isAdvanced ? (
              <ul className="addon-fit-notes">
                {addon.fit_notes_vi.map((note) => (
                  <li key={`${addon.sku}-${note}`}>{note}</li>
                ))}
                {addon.warnings_vi.map((warning) => (
                  <li key={`${addon.sku}-${warning}`}>{warning}</li>
                ))}
              </ul>
            ) : null}

            <a className="addon-link" href={addon.url} target="_blank" rel="noreferrer">
              Xem sản phẩm
            </a>

            <label className="addon-select">
              <input
                type="checkbox"
                checked={selected.has(addon.sku)}
                disabled={disabled}
                onChange={(event) => onToggle(addon.sku, event.currentTarget.checked)}
              />
              <span>Thêm vào danh sách mua</span>
            </label>
          </article>
        ))}
      </div>
    </section>
  );
}

function CustomerWarningsPanel({ artifact }: { artifact: BuildArtifact }) {
  const warnings = [
    ...artifact.warnings_vi,
    ...artifact.compatibility_report.results
      .filter((result) => result.severity !== "pass")
      .map((result) => result.explanation_vi)
  ];

  if (!warnings.length) return null;

  return (
    <section className="customer-warning-panel" data-testid="customer-warning-panel">
      <h3>Điểm cần lưu ý</h3>
      <ul>
        {warnings.slice(0, 3).map((item) => (
          <li key={item}>{friendlyWarning(item)}</li>
        ))}
      </ul>
    </section>
  );
}

function BuildAlternativesPanel({
  response,
  isAdvanced,
  isApplying,
  onApplyAlternative
}: {
  response: BuildAlternativesResponse;
  isAdvanced: boolean;
  isApplying: boolean;
  onApplyAlternative: (alternative: BuildAlternative) => void;
}) {
  if (!response.alternatives.length) return null;

  return (
    <section className="alternatives-panel" data-testid="alternatives-panel">
      <div className="alternatives-heading">
        <div>
          <h3>Phương án thay thế</h3>
          <p>
            Các lựa chọn đổi linh kiện vẫn dùng sản phẩm Phong Vu và đã kiểm tra
            tương thích lại.
          </p>
        </div>
        <span className="status">{response.alternatives.length} lựa chọn</span>
      </div>

      <div className="alternatives-grid">
        {response.alternatives.map((alternative) => (
          <article className="alternative-card" key={alternative.variant_id}>
            <div className="alternative-card-heading">
              <div>
                <h4>{alternative.label_vi}</h4>
                <p>{alternative.summary_vi}</p>
              </div>
              <span className={alternativeStatusClass(alternative)}>
                {alternativeStatusLabel(alternative)}
              </span>
            </div>

            <div className="alternative-metrics">
              {isAdvanced ? (
                <Metric
                  label="Ưu tiên"
                  value={`#${alternative.ranking.rank} · ${alternative.ranking.score}/100`}
                />
              ) : null}
              <Metric label="Tổng giá" value={formatVnd(alternative.total_price_vnd)} />
              <Metric label="Chênh lệch" value={formatDeltaVnd(alternative.price_delta_vnd)} />
            </div>

            <AlternativeRiskTags alternative={alternative} />

            <div className="alternative-changes">
              <h5>Thay đổi</h5>
              <ul>
                {alternative.changed_slots.map((change) => (
                  <li key={`${alternative.variant_id}-${change.slot}`}>
                    <strong>{slotLabel(change.slot)}</strong>
                    <span>
                      {change.current_name} sang {change.candidate_name}
                    </span>
                    <small>{formatDeltaVnd(change.price_delta_vnd)}</small>
                  </li>
                ))}
              </ul>
            </div>

            {isAdvanced ? (
              <ul className="alternative-reasons">
                {alternative.ranking.reasons_vi.map((reason) => (
                  <li key={`${alternative.variant_id}-ranking-${reason}`}>
                    {reason}
                  </li>
                ))}
                {alternative.changed_slots.map((change) => (
                  <li key={`${alternative.variant_id}-${change.slot}-reason`}>
                    {change.reason_vi}
                  </li>
                ))}
                {alternative.warnings_vi.map((warning) => (
                  <li key={`${alternative.variant_id}-${warning}`}>{warning}</li>
                ))}
              </ul>
            ) : null}

            <button
              type="button"
              className="alternative-apply"
              data-testid={`apply-alternative-${alternative.kind}`}
              disabled={isApplying}
              onClick={() => onApplyAlternative(alternative)}
            >
              Áp dụng lựa chọn
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

function AlternativeRiskTags({ alternative }: { alternative: BuildAlternative }) {
  const tags = alternativeRiskTags(alternative);
  return (
    <div className="risk-tags" aria-label="Đánh giá rủi ro">
      {tags.map((tag) => (
        <span className={`risk-tag ${tag.tone}`} key={tag.label} title={tag.title}>
          {tag.label}
        </span>
      ))}
    </div>
  );
}

function BuildIterationPanel({
  command,
  isLoading,
  lastIteration,
  onCommandChange,
  onSubmitCommand
}: {
  command: string;
  isLoading: boolean;
  lastIteration: BuildIterationResponse | null;
  onCommandChange: (command: string) => void;
  onSubmitCommand: (commandOverride?: string) => void;
}) {
  const presets = [
    "Tăng SSD nhưng giữ dưới 20 triệu",
    "Giảm xuống dưới 18 triệu",
    "Êm hơn",
    "Ưu tiên NVIDIA"
  ];

  return (
    <section className="iteration-panel" data-testid="iteration-panel">
      <div className="iteration-heading">
        <div>
          <h3>Điều chỉnh cấu hình</h3>
          <p>Nhập yêu cầu ngắn, hệ thống sẽ đổi linh kiện và kiểm tra lại.</p>
        </div>
        {lastIteration ? (
          <span className="status confirmed">Phiên bản {lastIteration.applied_build.build_version}</span>
        ) : (
          <span className="status">Sẵn sàng</span>
        )}
      </div>

      <div className="iteration-preset-row" aria-label="Lệnh mẫu">
        {presets.map((item) => (
          <button
            key={item}
            type="button"
            disabled={isLoading}
            onClick={() => {
              onCommandChange(item);
              onSubmitCommand(item);
            }}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="iteration-command-row">
        <input
          aria-label="Yêu cầu điều chỉnh"
          data-testid="iteration-command-input"
          value={command}
          onChange={(event) => onCommandChange(event.target.value)}
        />
        <button
          type="button"
          data-testid="iterate-build"
          disabled={isLoading || !command.trim()}
          onClick={() => onSubmitCommand()}
        >
          Áp dụng
        </button>
      </div>

      {lastIteration ? (
        <div className="iteration-result" data-testid="iteration-result">
          <Metric label="Lệnh" value={lastIteration.command.priority_label_vi} />
          <Metric label="Lựa chọn" value={lastIteration.selected_alternative.label_vi} />
          <Metric
            label="Chênh lệch"
            value={formatDeltaVnd(lastIteration.selected_alternative.price_delta_vnd)}
          />
        </div>
      ) : null}
    </section>
  );
}

function PerformanceProfilePanel({
  profile,
  isAdvanced
}: {
  profile: PerformanceProfile;
  isAdvanced: boolean;
}) {
  const statusClassName =
    profile.fit_level === "good"
      ? "status confirmed"
      : profile.fit_level === "adequate"
        ? "status warning"
        : profile.fit_level === "limited"
          ? "status blocked"
          : "status";

  return (
    <section className="performance-fit" data-testid="performance-profile">
      <div className="performance-fit-heading">
        <div>
          <h3>Mức phù hợp</h3>
          <p>{profile.summary_vi}</p>
        </div>
        <div className="performance-fit-status">
          <span className={statusClassName}>{performanceFitLabel(profile.fit_level)}</span>
          <small>{performanceConfidenceLabel(profile.confidence)}</small>
        </div>
      </div>

      {profile.evidence.length ? (
        <div className="performance-evidence" aria-label="Performance facts">
          {profile.evidence.map((fact) => (
            <div key={`${fact.label}-${fact.value}`}>
              <span>{fact.label}</span>
              <strong>{fact.value}</strong>
              {fact.source_url ? (
                <a href={fact.source_url} target="_blank" rel="noreferrer">
                  {fact.source_label ?? "Nguồn benchmark"}
                </a>
              ) : fact.source_label ? (
                <small>{fact.source_label}</small>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      {profile.balance && isAdvanced ? (
        <div className="performance-balance" aria-label="Balance score">
          <div>
            <span>Balance</span>
            <strong>{profile.balance.score}/100</strong>
          </div>
          <p>{profile.balance.interpretation_vi}</p>
          <small>Giới hạn: {balanceComponentLabel(profile.balance.limiting_component)}</small>
          {profile.balance.suggestions_vi.length ? (
            <ul>
              {profile.balance.suggestions_vi.map((suggestion) => (
                <li key={suggestion}>{suggestion}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {profile.workload_profiles.length && isAdvanced ? (
        <div className="workload-profiles" aria-label="App workload fit">
          <h4>Ứng dụng</h4>
          {profile.workload_profiles.map((workload) => (
            <div key={`${workload.name}-${workload.category}`}>
              <div>
                <span>{workloadCategoryLabel(workload.category)}</span>
                <strong>{workload.name}</strong>
              </div>
              <span className={`workload-fit-level ${workload.fit_level}`}>
                {performanceFitLabel(workload.fit_level)}
              </span>
              <p>{workload.recommendation_vi}</p>
              <small>{workload.requirement_summary_vi}</small>
            </div>
          ))}
        </div>
      ) : null}

      {isAdvanced ? (
        <div className="performance-notes">
          {profile.fit_notes_vi.length ? (
            <div>
              <h4>Phù hợp</h4>
              <ul>
                {profile.fit_notes_vi.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {profile.bottleneck_notes_vi.length ? (
            <div>
              <h4>Điểm cần lưu ý</h4>
              <ul>
                {profile.bottleneck_notes_vi.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {profile.warnings_vi.length ? (
            <div>
              <h4>Lưu ý</h4>
              <ul>
                {profile.warnings_vi.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : profile.warnings_vi.length ? (
        <div className="customer-warning-panel compact">
          <h3>Điểm cần lưu ý</h3>
          <ul>
            {profile.warnings_vi.slice(0, 2).map((note) => (
              <li key={note}>{friendlyWarning(note)}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function balanceComponentLabel(component: NonNullable<PerformanceProfile["balance"]>["limiting_component"]) {
  const labels: Record<NonNullable<PerformanceProfile["balance"]>["limiting_component"], string> = {
    cpu: "CPU",
    gpu: "GPU",
    ram: "RAM",
    storage: "SSD",
    unknown: "Chưa rõ"
  };
  return labels[component];
}

function performanceFitLabel(fitLevel: PerformanceProfile["fit_level"]) {
  const labels: Record<PerformanceProfile["fit_level"], string> = {
    good: "Phù hợp tốt",
    adequate: "Đủ dùng",
    limited: "Còn hạn chế",
    unknown: "Chưa đủ dữ liệu"
  };
  return labels[fitLevel];
}

function performanceConfidenceLabel(confidence: PerformanceProfile["confidence"]) {
  const labels: Record<PerformanceProfile["confidence"], string> = {
    high: "Dữ liệu cao",
    medium: "Dữ liệu vừa",
    low: "Dữ liệu thấp"
  };
  return labels[confidence];
}

function workloadCategoryLabel(category: PerformanceProfile["workload_profiles"][number]["category"]) {
  const labels: Record<PerformanceProfile["workload_profiles"][number]["category"], string> = {
    video_editing: "Video",
    three_d: "3D",
    photo_editing: "Photo",
    streaming: "Stream",
    local_llm: "AI cá nhân"
  };
  return labels[category];
}

function LlmAgentPanel({ analysis }: { analysis: IntentAgentAnalysis }) {
  const statusLabel: Record<IntentAgentAnalysis["status"], string> = {
    available: "Đang hoạt động",
    degraded: "Dự phòng",
    disabled: "Chưa bật"
  };
  const statusClassName =
    analysis.status === "available"
      ? "status confirmed"
      : analysis.status === "degraded"
        ? "status warning"
        : "status";

  return (
    <section className="llm-agent" data-testid="llm-agent-panel">
      <div className="llm-agent-heading">
        <div>
          <h3>Tóm tắt nhu cầu</h3>
          <p>Phần tóm tắt giúp bạn kiểm tra lại nhu cầu trước khi sinh cấu hình.</p>
        </div>
        <span className={statusClassName}>{statusLabel[analysis.status]}</span>
      </div>

      {analysis.summary_vi ? (
        <div className="llm-agent-block">
          <strong>Tóm tắt tự động</strong>
          <p>{analysis.summary_vi}</p>
        </div>
      ) : null}

      {analysis.clarification_vi ? (
        <div className="llm-agent-block">
          <strong>Câu hỏi gợi ý</strong>
          <p>{analysis.clarification_vi}</p>
        </div>
      ) : null}

      {analysis.error_vi ? <p className="llm-agent-error">{analysis.error_vi}</p> : null}

      {analysis.confidence_notes_vi.length || analysis.safety_notes_vi.length ? (
        <details className="llm-agent-details">
          <summary>Chi tiết phân tích</summary>
          {analysis.confidence_notes_vi.length ? (
            <div className="llm-agent-block">
              <strong>Ghi chú hiểu nhu cầu</strong>
              <ul>
                {analysis.confidence_notes_vi.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {analysis.safety_notes_vi.length ? (
            <div className="llm-agent-block">
              <strong>Ghi chú kiểm tra</strong>
              <ul>
                {analysis.safety_notes_vi.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </details>
      ) : null}
    </section>
  );
}

function CartReadyPanel({ handoff }: { handoff: CartReadyHandoff }) {
  const shoppingTotal = handoff.shopping_list_total_price_vnd || handoff.total_price_vnd;
  const cartSummary = [
    ["PC build", formatVnd(handoff.total_price_vnd)],
    ["Gợi ý thêm", formatVnd(handoff.add_on_total_price_vnd)],
    ["Tổng danh sách", formatVnd(shoppingTotal)],
    ["Sản phẩm", `${handoff.item_count}`]
  ] as const;

  return (
    <section className="cart-ready" data-testid="cart-ready-panel">
      <div className="panel-heading">
        <h3>Danh sách mua</h3>
        <span className="status confirmed">Sẵn sàng mở sản phẩm</span>
      </div>
      <dl className="cart-ready-summary" aria-label="Tóm tắt danh sách mua">
        {cartSummary.map(([label, value]) => (
          <div key={label} className={label === "Tổng danh sách" ? "total" : undefined}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="cart-ready-copy">
        Danh sách này dùng link sản phẩm Phong Vu để bạn kiểm tra giá, tồn kho và thêm vào
        giỏ hàng trên website chính thức.
      </p>
      {handoff.selected_addons.length ? (
        <div className="cart-addon-summary">
          <strong>Gợi ý thêm đã chọn</strong>
          <ul>
            {handoff.selected_addons.map((addon) => (
              <li key={addon.sku}>
                {addonKindLabel(addon.kind)} · {addon.name} · {formatVnd(addon.price_vnd)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <ol className="cart-links" aria-label="Link sản phẩm Phong Vũ">
        {handoff.mock_cart_payload.items.map((item, index) => (
          <li key={item.sku}>
            <span className="cart-link-index">{index + 1}</span>
            <a href={item.url} target="_blank" rel="noreferrer">
              {item.name || `Sản phẩm ${item.sku}`}
            </a>
          </li>
        ))}
      </ol>
      <ul className="cart-warnings">
        {handoff.warnings_vi.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatBudget(min: number | null, max: number | null) {
  const format = (value: number) =>
    new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
      maximumFractionDigits: 0
    }).format(value);

  if (min && max) return `${format(min)} - ${format(max)}`;
  if (max) return `Tối đa ${format(max)}`;
  if (min) return `Từ ${format(min)}`;
  return "Chưa có";
}

function formatVnd(value: number) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0
  }).format(value);
}

function formatDeltaVnd(value: number) {
  const formatted = formatVnd(Math.abs(value));
  if (value > 0) return `+${formatted}`;
  if (value < 0) return `-${formatted}`;
  return formatted;
}

function formatBudgetHeadroom(artifact: BuildArtifact) {
  if (!artifact.budget_max_vnd) return "Chưa có";
  return formatDeltaVnd(artifact.budget_max_vnd - artifact.total_price_vnd);
}

function compactPerformanceFitLabel(level: PerformanceProfile["fit_level"]) {
  return {
    good: "Rất cao",
    adequate: "Đủ dùng",
    limited: "Hạn chế",
    unknown: "Chưa rõ"
  }[level];
}

function compactPerformanceFitNote(profile: PerformanceProfile) {
  return {
    good: "Phù hợp với nhu cầu đã nhập.",
    adequate: "Ổn cho mục tiêu chính.",
    limited: "Nên nâng GPU hoặc giảm setting.",
    unknown: profile.summary_vi
  }[profile.fit_level];
}

function upgradeReadinessLabel(artifact: BuildArtifact) {
  if (!artifact.budget_max_vnd) return "Chưa rõ";
  return artifact.total_price_vnd <= artifact.budget_max_vnd ? "Tốt" : "Cần xem lại";
}

function compactBudgetHeadroomNote(artifact: BuildArtifact) {
  if (!artifact.budget_max_vnd) return "Theo ngân sách hiện tại";
  const delta = artifact.budget_max_vnd - artifact.total_price_vnd;
  return delta >= 0 ? `Còn ${formatVnd(delta)}` : `Vượt ${formatVnd(Math.abs(delta))}`;
}

function formatShortDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function shortId(value: string) {
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function extractBudgetMillions(value: string) {
  const match = value.match(/(\d+)\s*triệu/i);
  return match ? Number(match[1]) : null;
}

function applyBudgetText(value: string, budgetMillions: number) {
  const nextBudget = `${budgetMillions} triệu`;
  if (/\d+\s*triệu/i.test(value)) {
    return value.replace(/\d+\s*triệu/i, nextBudget);
  }
  const trimmed = value.trim();
  return trimmed ? `${trimmed}, ngân sách ${nextBudget}` : `Ngân sách ${nextBudget}`;
}

function toggleListItem(list: string[], item: string) {
  return list.includes(item) ? list.filter((current) => current !== item) : [...list, item];
}

function parseVndInput(value: string) {
  const digits = value.replace(/\D/g, "");
  if (!digits) return null;
  return Number(digits);
}

function parseOptionalNumber(value: string) {
  const digits = value.replace(/\D/g, "");
  if (!digits) return null;
  return Number(digits);
}

function emptyToNull(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function existingSystemToOverrides(system: ExistingSystemParseResponse["existing_system"]): ExistingSystemOverrides {
  return {
    cpu_name: system.cpu_name,
    mainboard_name: system.mainboard_name,
    ram_gb: system.ram_gb,
    gpu_name: system.gpu_name,
    psu_wattage_w: system.psu_wattage_w,
    psu_pcie_8pin_connectors: system.psu_pcie_8pin_connectors,
    case_gpu_clearance_mm: system.case_gpu_clearance_mm,
    storage_summary: system.storage_summary
  };
}

function slotLabel(slot: BuildItem["slot"]) {
  const labels: Record<BuildItem["slot"], string> = {
    cpu: "CPU",
    mainboard: "Mainboard",
    ram: "RAM",
    storage: "SSD",
    vga: "GPU",
    psu: "PSU",
    case: "Case",
    cooler: "Cooler"
  };
  return labels[slot];
}

function addonKindLabel(kind: BuildRecommendedAddOn["kind"]) {
  const labels: Record<BuildRecommendedAddOn["kind"], string> = {
    monitor: "Màn hình",
    cooler: "Tản nhiệt"
  };
  return labels[kind];
}

function stockStatusLabel(status: BuildItem["stock_status"], quantity?: number) {
  if (status === "in_stock") return quantity && quantity > 0 ? `Còn hàng (${quantity})` : "Còn hàng";
  if (status === "low_stock") return quantity && quantity > 0 ? `Sắp hết (${quantity})` : "Sắp hết";
  if (status === "out_of_stock") return "Tạm hết";
  if (status === "preorder") return "Đặt trước";
  return "Chưa rõ tồn";
}

function stockStatusClass(status: BuildItem["stock_status"]) {
  if (status === "in_stock") return "stock-pill in-stock";
  if (status === "low_stock") return "stock-pill low-stock";
  if (status === "out_of_stock") return "stock-pill out-of-stock";
  if (status === "preorder") return "stock-pill preorder";
  return "stock-pill unknown";
}

function upgradeStatusLabel(status: "pass" | "warn" | "block") {
  const labels: Record<"pass" | "warn" | "block", string> = {
    pass: "Qua kiểm tra",
    warn: "Cần xác nhận",
    block: "Bị chặn"
  };
  return labels[status];
}

function upgradeStatusClass(status: "pass" | "warn" | "block") {
  if (status === "pass") return "status confirmed";
  if (status === "warn") return "status warning";
  return "status blocked";
}

function upgradeImpactLabel(impact: "high" | "medium" | "low") {
  const labels: Record<"high" | "medium" | "low", string> = {
    high: "Tác động cao",
    medium: "Tác động vừa",
    low: "Tác động nhẹ"
  };
  return labels[impact];
}

function upgradeDecisionLabel(decision: "reuse" | "replace" | "optional_upgrade" | "unknown") {
  const labels: Record<"reuse" | "replace" | "optional_upgrade" | "unknown", string> = {
    reuse: "Giữ lại",
    replace: "Thay",
    optional_upgrade: "Có thể nâng",
    unknown: "Cần xác nhận"
  };
  return labels[decision];
}

function specConfidenceLabel(confidence: BuildItem["specs_confidence"]) {
  const labels: Record<BuildItem["specs_confidence"], string> = {
    verified: "đã kiểm tra",
    partial: "cần kiểm tra thêm",
    inferred: "ước tính"
  };
  return labels[confidence];
}

function feedbackPartKey(item: BuildItem) {
  return `${item.slot}:${item.sku}`;
}

function friendlyWarning(value: string) {
  if (value.includes("PERF_BELOW_TARGET")) {
    return "Hiệu năng đang thấp hơn mục tiêu màn hình đã chọn; nên nâng GPU hoặc giảm thiết lập game.";
  }
  return value;
}

function friendlyFeedbackReason(value: string) {
  if (value.toLowerCase().includes("review")) {
    return "Đội tư vấn sẽ xem lại góp ý này để cải thiện cấu hình.";
  }
  return value;
}

function alternativeRiskTags(alternative: BuildAlternative) {
  const tags: Array<{ label: string; title: string; tone: "ok" | "warning" | "danger" }> = [];

  if (!alternative.can_approve || alternative.budget_status !== "within_budget") {
    tags.push({
      label: "Cần xem lại",
      title: "Phương án này chưa qua đủ điều kiện ngân sách hoặc tương thích.",
      tone: "danger"
    });
  }

  if (alternative.warnings_vi.some((warning) => warning.includes("PERF_BELOW_TARGET"))) {
    tags.push({
      label: "FPS chưa đạt mục tiêu",
      title: "Benchmark hiện có thấp hơn mục tiêu tần số quét đã nhập.",
      tone: "warning"
    });
  }

  if (alternative.performance_profile.fit_level === "limited") {
    const limiting = alternative.performance_profile.balance?.limiting_component;
    tags.push({
      label: limiting && limiting !== "unknown"
        ? `Hạn chế: ${balanceComponentLabel(limiting)}`
        : "Hiệu năng còn hạn chế",
      title: "Cấu hình có thể chưa mượt với mục tiêu hoặc workload nặng.",
      tone: "warning"
    });
  }

  if (!tags.length) {
    tags.push({
      label: "Qua kiểm tra",
      title: "Phương án này nằm trong ngân sách và qua kiểm tra tương thích.",
      tone: "ok"
    });
  }

  return tags;
}

function decisionLabel(decision: OptimizerTrace["iterations"][number]["decision"]) {
  const labels: Record<OptimizerTrace["iterations"][number]["decision"], string> = {
    accepted: "Chọn",
    rejected: "Loại",
    skipped: "Bỏ qua"
  };
  return labels[decision];
}

function buildStatusLabel(artifact: BuildArtifact) {
  if (artifact.status === "generated") return "Hợp lệ";
  if (artifact.status === "over_budget") return "Vượt ngân sách";
  return "Bị chặn";
}

function statusClass(artifact: BuildArtifact) {
  if (artifact.status === "generated") return "status confirmed";
  if (artifact.status === "over_budget") return "status warning";
  return "status blocked";
}

function alternativeStatusLabel(alternative: BuildAlternative) {
  if (alternative.status === "generated") return "Hợp lệ";
  if (alternative.status === "over_budget") return "Vượt ngân sách";
  return "Bị chặn";
}

function alternativeStatusClass(alternative: BuildAlternative) {
  if (alternative.status === "generated") return "status confirmed";
  if (alternative.status === "over_budget") return "status warning";
  return "status blocked";
}

function formatPayload(payload: Record<string, string | number | boolean | null>) {
  if (!Object.keys(payload).length) return "{}";
  return JSON.stringify(payload, null, 2);
}

function toErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Có lỗi khi gọi Agent API";
}
