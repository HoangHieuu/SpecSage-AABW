"use client";

import { FormEvent, useMemo, useState } from "react";

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

export function BuildCopilotClient() {
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
  const [traceCopyState, setTraceCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const intent = intentResponse?.revision.intent;
  const isConfirmed = intentResponse?.revision.confirmed ?? false;
  const canConfirm = Boolean(intentResponse && !intentResponse.revision.clarification.field);
  const canGenerate = Boolean(session && isConfirmed);
  const canApprove = Boolean(
    buildArtifact && buildArtifact.can_approve && buildArtifact.status === "generated" && !cartHandoff
  );

  const budget = useMemo(() => {
    if (!intent) return "Chưa có";
    return formatBudget(intent.budget_min, intent.budget_max);
  }, [intent]);

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
      setTraceCopyState("idle");
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await sendIntent(false);
  }

  async function sendIntent(confirm: boolean) {
    setIsLoading(true);
    setError(null);
    try {
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
      setTraceCopyState("idle");
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
      setTraceCopyState("idle");
      setSession((current) => (current ? { ...current, state: "generated" } : current));
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
            <span className="header-pill">SKU thật</span>
            <span className="header-pill">Rule deterministic</span>
            <span className="header-pill accent">LangGraph</span>
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
                <span>từ snapshot</span>
              </div>
              <div className="hero-stat">
                <strong>0</strong>
                <span>đoán tương thích</span>
              </div>
            </div>
          </div>
          <div className="rig-visual" aria-hidden="true">
            <div className="rig-glow" />
            <div className="rig-frame">
              <span className="fan fan-one" />
              <span className="fan fan-two" />
              <span className="gpu-bar" />
              <span className="ram-stick" />
              <span className="led led-one" />
              <span className="led led-two" />
              <span className="led led-three" />
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
          <textarea
            id="intent"
            data-testid="intent-input"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={7}
          />

          <div className="action-row">
            <button type="submit" data-testid="analyze-intent" disabled={isLoading || !message.trim()}>
              Phân tích intent
            </button>
            <button
              type="button"
              className="secondary"
              data-testid="confirm-intent"
              disabled={isLoading || !canConfirm}
              onClick={() => sendIntent(true)}
            >
              Xác nhận intent
            </button>
            <button
              type="button"
              className="secondary"
              data-testid="generate-build"
              disabled={isLoading || !canGenerate}
              onClick={handleGenerate}
            >
              Sinh cấu hình
            </button>
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
              <dt>Session</dt>
              <dd>{session?.build_session_id ?? "Chưa tạo"}</dd>
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
              <Metric label="Catalog" value={buildArtifact.catalog_version} />
              <Metric label="Rules" value={buildArtifact.rules_version} />
            </div>

            {appliedAlternativeLabel ? (
              <p className="build-version-note" data-testid="applied-alternative-note">
                Đã áp dụng biến thể {appliedAlternativeLabel} vào build version{" "}
                {buildArtifact.build_version}. Bạn có thể duyệt build mới sau khi kiểm tra bảng
                linh kiện.
              </p>
            ) : null}

            {sessionTrace ? (
              <TraceReplayPanel
                trace={sessionTrace}
                copyState={traceCopyState}
                onCopyExport={handleCopyTraceExport}
              />
            ) : buildArtifact.orchestration_trace.length ? (
              <AgentTracePanel steps={buildArtifact.orchestration_trace} />
            ) : null}

            {buildArtifact.optimizer_trace ? (
              <OptimizerTracePanel trace={buildArtifact.optimizer_trace} />
            ) : null}

            <PerformanceProfilePanel profile={buildArtifact.performance_profile} />

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Slot</th>
                    <th>SKU</th>
                    <th>Linh kiện</th>
                    <th>Giá</th>
                    <th>Lý do chọn</th>
                  </tr>
                </thead>
                <tbody>
                  {buildArtifact.items.map((item) => (
                    <tr key={`${item.slot}-${item.sku}`}>
                      <td>{slotLabel(item.slot)}</td>
                      <td>{item.sku}</td>
                      <td>
                        <a href={item.url} target="_blank" rel="noreferrer">
                          {item.name}
                        </a>
                        <span className="confidence">{item.specs_confidence}</span>
                      </td>
                      <td>{formatVnd(item.price_vnd)}</td>
                      <td>{item.explanation_vi}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {buildAlternatives ? (
              <BuildAlternativesPanel
                response={buildAlternatives}
                isApplying={isLoading}
                onApplyAlternative={handleApplyAlternative}
              />
            ) : null}

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

            <div className="approval-strip">
              <div>
                <h3>Duyệt build & handoff</h3>
                <p>
                  {cartHandoff
                    ? "Build đã được duyệt và có handoff giỏ mock từ các link SKU Phong Vu."
                    : canApprove
                      ? "Build đã đạt rule compatibility và nằm trong ngân sách, có thể tạo handoff giỏ mock."
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
          </>
        ) : (
          <p className="empty">
            Xác nhận intent rồi sinh cấu hình để xem bảng linh kiện, tổng giá,
            compatibility report và link SKU Phong Vu.
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
            <h3>Feedback build</h3>
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
          <Metric label="Part feedback" value={`${feedback.part_feedback.length}`} />
          <Metric label="Catalog" value={feedback.catalog_version} />
          <Metric label="Rules" value={feedback.rules_version} />
        </div>
        {feedback.review_queue_reason_vi ? <p>{feedback.review_queue_reason_vi}</p> : null}
      </section>
    );
  }

  return (
    <section className="feedback-panel" data-testid="feedback-panel">
      <div className="feedback-heading">
        <div>
          <h3>Feedback build</h3>
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
          <h3>Trace replay</h3>
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
          <h3>Agent orchestration</h3>
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
          <h3>Optimizer loop</h3>
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

function BuildAlternativesPanel({
  response,
  isApplying,
  onApplyAlternative
}: {
  response: BuildAlternativesResponse;
  isApplying: boolean;
  onApplyAlternative: (alternative: BuildAlternative) => void;
}) {
  if (!response.alternatives.length) return null;

  return (
    <section className="alternatives-panel" data-testid="alternatives-panel">
      <div className="alternatives-heading">
        <div>
          <h3>Alternatives</h3>
          <p>
            Các biến thể được tạo từ cùng catalog snapshot và đã chạy lại rule
            compatibility.
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
              <Metric
                label="Ưu tiên"
                value={`#${alternative.ranking.rank} · ${alternative.ranking.score}/100`}
              />
              <Metric label="Tổng giá" value={formatVnd(alternative.total_price_vnd)} />
              <Metric label="Chênh lệch" value={formatDeltaVnd(alternative.price_delta_vnd)} />
              <Metric label="Fit" value={fitLevelLabel(alternative.performance_profile.fit_level)} />
            </div>

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

function PerformanceProfilePanel({ profile }: { profile: PerformanceProfile }) {
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
          <h3>Workload fit</h3>
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

      {profile.balance ? (
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

      {profile.workload_profiles.length ? (
        <div className="workload-profiles" aria-label="App workload fit">
          <h4>App fit</h4>
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
            <h4>Bottleneck</h4>
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
          <h3>LLM Agent</h3>
          <p>
            OpenRouter <span>{analysis.model}</span>
          </p>
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

      {analysis.confidence_notes_vi.length ? (
        <div className="llm-agent-block">
          <strong>Ghi chú hiểu intent</strong>
          <ul>
            {analysis.confidence_notes_vi.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {analysis.safety_notes_vi.length ? (
        <div className="llm-agent-block">
          <strong>Ghi chú an toàn</strong>
          <ul>
            {analysis.safety_notes_vi.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function CartReadyPanel({ handoff }: { handoff: CartReadyHandoff }) {
  return (
    <section className="cart-ready" data-testid="cart-ready-panel">
      <div className="panel-heading">
        <h3>Handoff giỏ mock</h3>
        <span className="status confirmed">Sẵn sàng chuyển giỏ</span>
      </div>
      <div className="build-metrics compact">
        <Metric label="Tổng giá" value={formatVnd(handoff.total_price_vnd)} />
        <Metric label="Số SKU" value={`${handoff.item_count}`} />
        <Metric label="Approval" value={handoff.approval.approval_id} />
        <Metric label="Handoff" value={handoff.handoff_id} />
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

function feedbackPartKey(item: BuildItem) {
  return `${item.slot}:${item.sku}`;
}

function fitLevelLabel(level: PerformanceProfile["fit_level"]) {
  const labels: Record<PerformanceProfile["fit_level"], string> = {
    good: "Phù hợp tốt",
    adequate: "Đủ dùng",
    limited: "Hạn chế",
    unknown: "Chưa rõ"
  };
  return labels[level];
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
