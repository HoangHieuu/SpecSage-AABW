"use client";

import { FormEvent, useMemo, useState } from "react";

import {
  BuildArtifact,
  BuildItem,
  BuildSession,
  CartReadyHandoff,
  IntentResponse,
  UseCase,
  approveBuild,
  createSession,
  generateBuild,
  submitIntent
} from "@/lib/api";

const presets: Array<{ value: UseCase; label: string; sample: string }> = [
  {
    value: "gaming",
    label: "Gaming",
    sample: "PC gaming 25 triệu chơi Valorant và LMHT 144Hz"
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
  const [buildArtifact, setBuildArtifact] = useState<BuildArtifact | null>(null);
  const [cartHandoff, setCartHandoff] = useState<CartReadyHandoff | null>(null);
  const [isLoading, setIsLoading] = useState(false);
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
      setBuildArtifact(null);
      setCartHandoff(null);
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
      setBuildArtifact(null);
      setCartHandoff(null);
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
      setBuildArtifact(artifact);
      setCartHandoff(null);
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

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <h1>PC Build Copilot</h1>
          <p>
            Tư vấn cấu hình từ nhu cầu thật, dùng dữ liệu SKU Phong Vu và kiểm tra
            tương thích bằng luật trước khi tạo build.
          </p>
        </div>
        <div className="rig-visual" aria-hidden="true">
          <div className="rig-frame">
            <span className="fan fan-one" />
            <span className="fan fan-two" />
            <span className="gpu-bar" />
            <span className="ram-stick" />
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

function toErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Có lỗi khi gọi Agent API";
}
