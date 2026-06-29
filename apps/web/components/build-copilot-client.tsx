"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

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
  BuildSession,
  CartReadyHandoff,
  IntentAgentAnalysis,
  IntentResponse,
  OptimizerTrace,
  PartFeedbackRequest,
  PerformanceProfile,
  SessionTraceReplay,
  TraceReplayEvent,
  UseCase,
  applyBuildAlternative,
  approveBuild,
  createSession,
  generateBuild,
  getBuildAlternatives,
  getSessionTrace,
  iterateBuild,
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
    label: "AI/local LLM",
    sample: "PC AI local LLM 40 triệu, ưu tiên NVIDIA và 32GB RAM"
  }
];

const useCaseLabels: Record<UseCase, string> = {
  gaming: "Gaming",
  creator: "Creator/đồ họa",
  office: "Văn phòng",
  student: "Sinh viên",
  ai: "AI/local LLM",
  streaming: "Streaming",
  compact: "Compact/Mini ITX",
  unknown: "Chưa rõ"
};

type DisplayMode = "basic" | "advanced";

export function BuildCopilotClient() {
  const intentTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [session, setSession] = useState<BuildSession | null>(null);
  const [message, setMessage] = useState(presets[0].sample);
  const [preset, setPreset] = useState<UseCase>("gaming");
  const [intentResponse, setIntentResponse] = useState<IntentResponse | null>(null);
  const [agentAnalysis, setAgentAnalysis] = useState<IntentAgentAnalysis | null>(null);
  const [buildArtifact, setBuildArtifact] = useState<BuildArtifact | null>(null);
  const [buildAlternatives, setBuildAlternatives] = useState<BuildAlternativesResponse | null>(null);
  const [sessionTrace, setSessionTrace] = useState<SessionTraceReplay | null>(null);
  const [cartHandoff, setCartHandoff] = useState<CartReadyHandoff | null>(null);
  const [buildFeedback, setBuildFeedback] = useState<BuildFeedback | null>(null);
  const [appliedAlternativeLabel, setAppliedAlternativeLabel] = useState<string | null>(null);
  const [iterationCommand, setIterationCommand] = useState("Tăng SSD nhưng giữ dưới 20 triệu");
  const [lastIteration, setLastIteration] = useState<BuildIterationResponse | null>(null);
  const [displayMode, setDisplayMode] = useState<DisplayMode>("basic");
  const [showSupportDetails, setShowSupportDetails] = useState(false);
  const [traceCopyState, setTraceCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const [isLoading, setIsLoading] = useState(false);
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
      ? "Intent đã xác nhận, bước tiếp theo là sinh cấu hình."
      : intentResponse && !needsClarification
        ? "Bước này sẽ xác nhận nhu cầu và tạo cấu hình ngay."
        : "Mô tả nhu cầu, ngân sách và ưu tiên của bạn.";

  const budget = useMemo(() => {
    if (!intent) return "Chưa có";
    return formatBudget(intent.budget_min, intent.budget_max);
  }, [intent]);

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
      const handoff = await approveBuild(buildArtifact.build_id);
      setCartHandoff(handoff);
      setSession((current) => (current ? { ...current, state: "cart_ready" } : current));
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
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

  return (
    <>
      <BackgroundAnimation />
      <main className={`app-shell${isLoading ? " is-loading" : ""}`}>
        <header className="site-header">
          <div className="brand-lockup">
            <span className="brand-mark" aria-hidden="true">
              PV
            </span>
            <div>
              <strong>PC Build Copilot</strong>
              <span>Phong Vu · Agentic AI</span>
            </div>
          </div>
          <div className="header-meta">
            <span className="header-pill">SKU Phong Vu</span>
            <span className="header-pill">Kiểm tra tương thích</span>
            <span className="header-pill accent">Tư vấn AI</span>
          </div>
        </header>

        <FlowProgress
          hasSession={Boolean(session)}
          isConfirmed={isConfirmed}
          hasBuild={Boolean(buildArtifact)}
          isCartReady={Boolean(cartHandoff)}
        />

        <section className="hero-panel">
          <div className="hero-copy">
            <span className="hero-eyebrow">Tư vấn cấu hình thông minh</span>
            <h1>
              Xây PC đúng nhu cầu,
              <em> đúng ngân sách</em>
            </h1>
            <p>
              Tư vấn cấu hình từ nhu cầu thật, dùng dữ liệu SKU Phong Vu và kiểm tra
              tương thích bằng luật trước khi tạo build.
            </p>
            <div className="hero-stats">
              <div className="hero-stat">
                <strong>7+</strong>
                <span>slot linh kiện</span>
              </div>
              <div className="hero-stat">
                <strong>SKU</strong>
                <span>Phong Vu</span>
              </div>
              <div className="hero-stat">
                <strong>0</strong>
                <span>đoán tương thích</span>
              </div>
            </div>
          </div>
        </section>

      <section className="workspace-grid">
        <form className="panel composer" onSubmit={handleSubmit}>
          <div className="panel-heading">
            <h2>Nhu cầu build PC</h2>
            <button type="button" onClick={handleStart} disabled={isLoading}>
              {session ? "Tạo phiên mới" : "Bắt đầu phiên"}
            </button>
          </div>

          <div className="preset-row" aria-label="Preset">
            {presets.map((item) => (
              <button
                key={item.value}
                type="button"
                className={preset === item.value ? "selected" : ""}
                onClick={() => {
                  setPreset(item.value);
                  setMessage(item.sample);
                }}
              >
                {item.label}
              </button>
            ))}
          </div>

          <label htmlFor="intent">Mô tả nhu cầu</label>
          <div className="prompt-box">
            <textarea
              id="intent"
              ref={intentTextareaRef}
              data-testid="intent-input"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              rows={3}
            />
            <div className="prompt-footer">
              <span>{primaryActionHint}</span>
              <button
                type="submit"
                data-testid="primary-flow-action"
                disabled={isLoading || !message.trim()}
              >
                {isLoading ? "Đang xử lý..." : primaryActionLabel}
              </button>
            </div>
          </div>

          {error ? <p className="error">{error}</p> : null}
        </form>

        <aside className="panel summary">
          <div className="panel-heading">
            <h2>Tóm tắt intent</h2>
            <span className={isConfirmed ? "status confirmed" : "status"}>
              {isConfirmed ? "Đã xác nhận" : session?.state ?? "Chưa có phiên"}
            </span>
          </div>

          <dl className="facts">
            <div>
              <dt>Trạng thái</dt>
              <dd>{session ? "Đang tư vấn" : "Chưa tạo"}</dd>
            </div>
            <div>
              <dt>Use case</dt>
              <dd>{intent ? useCaseLabels[intent.use_case] : "Chưa phân tích"}</dd>
            </div>
            <div>
              <dt>Ngân sách</dt>
              <dd>{budget}</dd>
            </div>
            <div>
              <dt>Game</dt>
              <dd>{intent?.target_games.length ? intent.target_games.join(", ") : "Chưa có"}</dd>
            </div>
            <div>
              <dt>Ứng dụng</dt>
              <dd>{intent?.target_apps.length ? intent.target_apps.join(", ") : "Chưa có"}</dd>
            </div>
            <div>
              <dt>Mục tiêu</dt>
              <dd>
                {intent?.performance_targets.length
                  ? intent.performance_targets.join(", ")
                  : "Chưa có"}
              </dd>
            </div>
          </dl>

          {intentResponse?.revision.clarification.question ? (
            <div className="clarification">
              <strong>Cần hỏi thêm</strong>
              <p>{intentResponse.revision.clarification.question}</p>
            </div>
          ) : null}

          {agentAnalysis ? <LlmAgentPanel analysis={agentAnalysis} /> : null}

          {intent ? (
            <div className="chips">
              {intent.brand_preferences.map((brand) => (
                <span key={brand}>{brand}</span>
              ))}
              {intent.mentioned_components.map((component) => (
                <span key={component}>{component}</span>
              ))}
              {intent.safe_defaults.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          ) : (
            <p className="empty">Phiên tư vấn sẽ lưu intent trước khi sinh cấu hình.</p>
          )}
        </aside>
      </section>

      <section className="panel build-panel" aria-live="polite" data-testid="build-panel">
        <div className="panel-heading">
          <h2>Build đề xuất</h2>
          <span className={buildArtifact ? statusClass(buildArtifact) : "status"}>
            {buildArtifact ? buildStatusLabel(buildArtifact) : "Chưa sinh build"}
          </span>
        </div>

        {buildArtifact ? (
          <>
            <div className="build-metrics">
              <Metric label="Tổng giá" value={formatVnd(buildArtifact.total_price_vnd)} />
              <Metric
                label="Ngân sách"
                value={
                  buildArtifact.budget_max_vnd
                    ? formatVnd(buildArtifact.budget_max_vnd)
                    : "Chưa có"
                }
              />
              <Metric label="Còn dư" value={formatBudgetHeadroom(buildArtifact)} />
              <Metric label="Phiên bản" value={`Build v${buildArtifact.build_version}`} />
            </div>

            <DisplayModeToggle mode={displayMode} onModeChange={setDisplayMode} />

            {appliedAlternativeLabel ? (
              <p className="build-version-note" data-testid="applied-alternative-note">
                Đã áp dụng biến thể {appliedAlternativeLabel} vào build version{" "}
                {buildArtifact.build_version}. Bạn có thể duyệt build mới sau khi kiểm tra bảng
                linh kiện.
              </p>
            ) : null}

            <PerformanceProfilePanel
              profile={buildArtifact.performance_profile}
              isAdvanced={displayMode === "advanced"}
            />

            <div className="table-wrap">
              <table className={`parts-table ${displayMode}`}>
                <thead>
                  <tr>
                    <th>Slot</th>
                    {displayMode === "advanced" ? <th>SKU</th> : null}
                    <th>Linh kiện</th>
                    <th>Giá</th>
                    {displayMode === "advanced" ? <th>Lý do chọn</th> : null}
                  </tr>
                </thead>
                <tbody>
                  {buildArtifact.items.map((item) => (
                    <tr key={`${item.slot}-${item.sku}`}>
                      <td>{slotLabel(item.slot)}</td>
                      {displayMode === "advanced" ? <td>{item.sku}</td> : null}
                      <td>
                        <a href={item.url} target="_blank" rel="noreferrer">
                          {item.name}
                        </a>
                        <span className="confidence">{specConfidenceLabel(item.specs_confidence)}</span>
                      </td>
                      <td>{formatVnd(item.price_vnd)}</td>
                      {displayMode === "advanced" ? <td>{item.explanation_vi}</td> : null}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {buildAlternatives ? (
              <BuildAlternativesPanel
                response={buildAlternatives}
                isAdvanced={displayMode === "advanced"}
                isApplying={isLoading}
                onApplyAlternative={handleApplyAlternative}
              />
            ) : null}

            <BuildIterationPanel
              command={iterationCommand}
              isLoading={isLoading}
              lastIteration={lastIteration}
              onCommandChange={setIterationCommand}
              onSubmitCommand={handleIterateBuild}
            />

            {displayMode === "advanced" ? (
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
            ) : (
              <CustomerWarningsPanel artifact={buildArtifact} />
            )}

            <div className="approval-strip">
              <div>
                <h3>Duyệt build & handoff</h3>
                <p>
                  {cartHandoff
                    ? "Build đã được duyệt và có handoff giỏ mock từ các link SKU Phong Vu."
                    : canApprove
                      ? "Build đã qua kiểm tra tương thích và nằm trong ngân sách, có thể tạo giỏ mock."
                      : "Build chưa đủ điều kiện duyệt vì bị chặn, vượt ngân sách hoặc thiếu thông tin."}
                </p>
              </div>
              <button
                type="button"
                data-testid="approve-build"
                disabled={isLoading || !canApprove}
                onClick={handleApprove}
              >
                {cartHandoff ? "Đã tạo giỏ mock" : "Duyệt & tạo giỏ mock"}
              </button>
            </div>

            <BuildFeedbackPanel
              artifact={buildArtifact}
              feedback={buildFeedback}
              isSubmitting={isSubmittingFeedback}
              onSubmit={handleSubmitFeedback}
            />

            {cartHandoff ? <CartReadyPanel handoff={cartHandoff} /> : null}

            {displayMode === "advanced" ? (
              <SupportDetailsPanel
                isOpen={showSupportDetails}
                trace={sessionTrace}
                copyState={traceCopyState}
                orchestrationSteps={buildArtifact.orchestration_trace}
                optimizerTrace={buildArtifact.optimizer_trace}
                onCopyExport={handleCopyTraceExport}
                onToggle={() => setShowSupportDetails((current) => !current)}
              />
            ) : null}
          </>
        ) : (
          <p className="empty">
            Xác nhận intent rồi sinh cấu hình để xem bảng linh kiện, tổng giá,
            mức phù hợp và link SKU Phong Vu.
          </p>
        )}
      </section>
      </main>
    </>
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
    { label: "Intent", active: hasSession && !isConfirmed, done: isConfirmed },
    { label: "Build", active: isConfirmed && !hasBuild, done: hasBuild },
    { label: "Giỏ mock", active: hasBuild && !isCartReady, done: isCartReady }
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
        Xem cơ bản
      </button>
      <button
        type="button"
        className={mode === "advanced" ? "selected" : ""}
        data-testid="view-advanced"
        onClick={() => onModeChange("advanced")}
      >
        Xem nâng cao
      </button>
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
            <h3>Đánh giá build</h3>
            <p>Đã lưu đánh giá cho build version {feedback.build_version}.</p>
          </div>
          <span
            className={
              feedback.review_queue_status === "queued" ? "status warning" : "status confirmed"
            }
          >
            {feedback.review_queue_status === "queued"
              ? "Đã đưa vào review queue"
              : "Đã ghi nhận"}
          </span>
        </div>
        <div className="feedback-saved-grid">
          <Metric
            label="Đánh giá"
            value={feedback.rating === "thumbs_up" ? "Hữu ích" : "Chưa phù hợp"}
          />
          <Metric label="Linh kiện" value={`${feedback.part_feedback.length} mục`} />
          <Metric label="Build" value={`v${feedback.build_version}`} />
          <Metric
            label="Trạng thái"
            value={feedback.review_queue_status === "queued" ? "Đang xem lại" : "Đã ghi nhận"}
          />
        </div>
        {feedback.review_queue_reason_vi ? <p>{feedback.review_queue_reason_vi}</p> : null}
      </section>
    );
  }

  return (
    <section className="feedback-panel" data-testid="feedback-panel">
      <div className="feedback-heading">
        <div>
          <h3>Đánh giá build</h3>
          <p>Ghi nhận cảm nhận tổng thể và từng linh kiện cho vòng review sau demo.</p>
        </div>
        <span className="status">Build v{artifact.build_version}</span>
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
          {isSubmitting ? "Đang lưu..." : "Lưu feedback"}
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
          <h3>Support trace</h3>
          <p>{trace.redaction_policy_vi}</p>
        </div>
        <div className="trace-replay-actions">
          <span className="status">
            {trace.generated_build_count} build / {totalEvents} event
          </span>
          <button type="button" className="secondary" onClick={onCopyExport}>
            {copyState === "copied"
              ? "Đã copy trace"
              : copyState === "failed"
                ? "Không copy được"
                : "Copy support trace"}
          </button>
        </div>
      </div>

      <div className="trace-builds">
        {trace.builds.map((build) => (
          <article className="trace-build-card" key={build.build_id}>
            <div className="trace-build-card-heading">
              <div>
                <h4>Build v{build.build_version}</h4>
                <p>{build.build_id}</p>
              </div>
              <span className={build.replay_status === "complete" ? "status confirmed" : "status"}>
                {build.replay_status === "complete" ? `${build.events.length} event` : "Không có event"}
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
                Build version này được tạo từ thao tác apply deterministic nên không có bước
                LangGraph riêng.
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
    catalog: "Catalog",
    optimizer: "Optimizer",
    compatibility: "Compatibility",
    performance: "Performance",
    explainer: "Explainer",
    validator: "Validator"
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
              <dt>Tool calls</dt>
              <dd>{event.tool_calls.length ? event.tool_calls.join(", ") : "none"}</dd>
            </div>
          </dl>
          <details className="trace-event-payload">
            <summary>Inputs / outputs</summary>
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
    catalog: "Catalog",
    optimizer: "Optimizer",
    compatibility: "Compatibility",
    performance: "Performance",
    explainer: "Explainer",
    validator: "Validator"
  };

  return (
    <section className="agent-trace" data-testid="agent-trace-panel">
      <div className="agent-trace-heading">
        <div>
          <h3>Agent steps</h3>
          <p>LangGraph chạy các agent theo thứ tự, còn rule và số liệu vẫn là deterministic.</p>
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
          <h3>Optimizer decisions</h3>
          <p>Phase 5 agent dùng allocation config, priority override và gate deterministic.</p>
        </div>
        <span className="status">
          {trace.applied_iteration_count}/{trace.max_iterations} vòng áp dụng
        </span>
      </div>

      <div className="optimizer-summary-grid">
        <Metric label="Use case" value={trace.budget_allocation.use_case} />
        <Metric
          label="Priority"
          value={trace.priority_overrides.length ? trace.priority_overrides.join(", ") : "Không có"}
        />
        <Metric label="Rejected" value={`${trace.rejected_iteration_count}`} />
      </div>

      <div className="optimizer-weights" aria-label="Budget allocation">
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
        <p className="optimizer-empty">Optimizer chưa cần thử biến thể trong lượt này.</p>
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
          <h3>Chi tiết hỗ trợ</h3>
          <p>Thông tin dành cho kiểm tra demo hoặc gửi kỹ thuật khi cần.</p>
        </div>
        <button
          type="button"
          className="secondary"
          data-testid="toggle-support-details"
          onClick={onToggle}
        >
          {isOpen ? "Ẩn chi tiết" : "Hiện chi tiết"}
        </button>
      </div>

      {isOpen ? (
        <div className="support-details-stack">
          {trace ? (
            <TraceReplayPanel trace={trace} copyState={copyState} onCopyExport={onCopyExport} />
          ) : orchestrationSteps.length ? (
            <AgentTracePanel steps={orchestrationSteps} />
          ) : null}
          {optimizerTrace ? <OptimizerTracePanel trace={optimizerTrace} /> : null}
        </div>
      ) : null}
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
            Các lựa chọn đổi linh kiện vẫn dùng SKU Phong Vu và đã kiểm tra
            tương thích lại.
          </p>
        </div>
        <span className="status">{response.alternatives.length} biến thể</span>
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
              Áp dụng biến thể
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
          <h3>Điều chỉnh build</h3>
          <p>Nhập yêu cầu ngắn, hệ thống sẽ đổi linh kiện và kiểm tra lại.</p>
        </div>
        {lastIteration ? (
          <span className="status confirmed">Build v{lastIteration.applied_build.build_version}</span>
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
          <Metric label="Biến thể" value={lastIteration.selected_alternative.label_vi} />
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
  const fitLabel: Record<PerformanceProfile["fit_level"], string> = {
    good: "Phù hợp tốt",
    adequate: "Đủ dùng",
    limited: "Còn hạn chế",
    unknown: "Chưa đủ dữ liệu"
  };
  const confidenceLabel: Record<PerformanceProfile["confidence"], string> = {
    high: "Dữ liệu cao",
    medium: "Dữ liệu vừa",
    low: "Dữ liệu thấp"
  };
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
          <span className={statusClassName}>{fitLabel[profile.fit_level]}</span>
          <small>{confidenceLabel[profile.confidence]}</small>
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
                {fitLabel[workload.fit_level]}
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

function workloadCategoryLabel(category: PerformanceProfile["workload_profiles"][number]["category"]) {
  const labels: Record<PerformanceProfile["workload_profiles"][number]["category"], string> = {
    video_editing: "Video",
    three_d: "3D",
    photo_editing: "Photo",
    streaming: "Stream",
    local_llm: "Local LLM"
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
          <p>AI hỗ trợ diễn giải; cấu hình vẫn được kiểm tra bằng luật.</p>
        </div>
        <span className={statusClassName}>{statusLabel[analysis.status]}</span>
      </div>

      {analysis.summary_vi ? (
        <div className="llm-agent-block">
          <strong>Tóm tắt từ LLM</strong>
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
  return (
    <section className="cart-ready" data-testid="cart-ready-panel">
      <div className="panel-heading">
        <h3>Giỏ mock</h3>
        <span className="status confirmed">Sẵn sàng chuyển giỏ</span>
      </div>
      <div className="build-metrics compact">
        <Metric label="Tổng giá" value={formatVnd(handoff.total_price_vnd)} />
        <Metric label="Số SKU" value={`${handoff.item_count}`} />
        <Metric label="Duyệt build" value="Đã duyệt" />
        <Metric label="Giỏ mock" value="Sẵn sàng" />
      </div>
      <p>{handoff.mock_cart_payload.disclaimer_vi}</p>
      <ol className="cart-links">
        {handoff.mock_cart_payload.items.map((item) => (
          <li key={item.sku}>
            <a href={item.url} target="_blank" rel="noreferrer">
              SKU {item.sku}
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
