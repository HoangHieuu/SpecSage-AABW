export type Channel = "web" | "staff" | "api";
export type SessionState =
  | "created"
  | "intent_draft"
  | "intent_confirmed"
  | "generated"
  | "reviewing"
  | "approved"
  | "cart_ready";
export type BuildSlot =
  | "cpu"
  | "mainboard"
  | "ram"
  | "storage"
  | "vga"
  | "psu"
  | "case"
  | "cooler";
export type UseCase =
  | "gaming"
  | "creator"
  | "office"
  | "student"
  | "ai"
  | "streaming"
  | "compact"
  | "unknown";

export type BuildSession = {
  build_session_id: string;
  created_at: string;
  updated_at: string;
  ttl_expires_at: string;
  locale: string;
  channel: Channel;
  state: SessionState;
};

export type BuildIntent = {
  raw_text: string;
  use_case: UseCase;
  budget_min: number | null;
  budget_max: number | null;
  budget_interpretation: string | null;
  target_games: string[];
  target_apps: string[];
  performance_targets: string[];
  form_factor: string | null;
  brand_preferences: string[];
  noise_preferences: string | null;
  aesthetic_preferences: string | null;
  mentioned_components: string[];
  safe_defaults: string[];
};

export type IntentAgentAnalysis = {
  provider: "openrouter";
  model: string;
  status: "available" | "degraded" | "disabled";
  summary_vi: string | null;
  clarification_vi: string | null;
  confidence_notes_vi: string[];
  safety_notes_vi: string[];
  raw_json_valid: boolean;
  error_vi: string | null;
};

export type IntentResponse = {
  session: BuildSession;
  revision: {
    revision_id: string;
    build_session_id: string;
    created_at: string;
    intent: BuildIntent;
    clarification: {
      field: "budget" | "use_case" | "target_games" | "target_apps" | null;
      question: string | null;
      required: boolean;
    };
    confirmed: boolean;
  };
  agent_analysis: IntentAgentAnalysis | null;
};

export type CompatibilityResult = {
  rule_id: string;
  severity: "pass" | "warn" | "block";
  slots: BuildSlot[];
  skus: string[];
  explanation_key: string;
  explanation_vi: string;
  remediation_vi: string | null;
  facts: Record<string, unknown>;
};

export type CompatibilityReport = {
  build_id: string;
  rules_version: string;
  catalog_version: string;
  checked_at: string;
  status: "approved" | "warning" | "blocked";
  max_severity: "pass" | "warn" | "block";
  can_approve: boolean;
  selected_skus: Partial<Record<BuildSlot, string>>;
  results: CompatibilityResult[];
};

export type BuildItem = {
  slot: BuildSlot;
  sku: string;
  name: string;
  category: string;
  price_vnd: number;
  url: string;
  brand: string | null;
  specs_confidence: "verified" | "partial" | "inferred";
  explanation_vi: string;
};

export type PerformanceProfile = {
  use_case: string;
  fit_level: "good" | "adequate" | "limited" | "unknown";
  confidence: "high" | "medium" | "low";
  summary_vi: string;
  fit_notes_vi: string[];
  bottleneck_notes_vi: string[];
  warnings_vi: string[];
  evidence: Array<{
    label: string;
    value: string;
    source: "catalog_spec" | "intent" | "rule";
  }>;
};

export type BuildOrchestrationStep = {
  agent:
    | "catalog"
    | "optimizer"
    | "compatibility"
    | "performance"
    | "explainer"
    | "validator";
  status: "completed" | "blocked";
  summary_vi: string;
  inputs: Record<string, string | number | boolean | null>;
  outputs: Record<string, string | number | boolean | null>;
};

export type BuildArtifact = {
  build_id: string;
  build_session_id: string;
  build_version: number;
  generated_at: string;
  intent_snapshot: BuildIntent;
  catalog_version: string;
  rules_version: string;
  total_price_vnd: number;
  budget_max_vnd: number | null;
  budget_gap_vnd: number;
  budget_status: "within_budget" | "over_budget" | "unknown_budget";
  status: "generated" | "over_budget" | "blocked";
  can_approve: boolean;
  items: BuildItem[];
  compatibility_report: CompatibilityReport;
  performance_profile: PerformanceProfile;
  explanations_vi: string[];
  warnings_vi: string[];
  orchestration_trace: BuildOrchestrationStep[];
  mock_cart_payload: {
    provider: string;
    disclaimer_vi: string;
    items: Array<{ sku: string; url: string }>;
  };
};

export type BuildAlternativeChangedSlot = {
  slot: BuildSlot;
  current_sku: string;
  current_name: string;
  candidate_sku: string;
  candidate_name: string;
  price_delta_vnd: number;
  reason_vi: string;
};

export type BuildAlternative = {
  variant_id: string;
  kind: "ram_upgrade" | "storage_upgrade" | "nvidia_gpu" | "psu_headroom";
  label_vi: string;
  summary_vi: string;
  total_price_vnd: number;
  price_delta_vnd: number;
  budget_status: "within_budget" | "over_budget" | "unknown_budget";
  budget_gap_vnd: number;
  status: "generated" | "over_budget" | "blocked";
  can_approve: boolean;
  items: BuildItem[];
  changed_slots: BuildAlternativeChangedSlot[];
  compatibility_report: CompatibilityReport;
  performance_profile: PerformanceProfile;
  explanations_vi: string[];
  warnings_vi: string[];
};

export type BuildAlternativesResponse = {
  build_id: string;
  build_session_id: string;
  catalog_version: string;
  rules_version: string;
  base_total_price_vnd: number;
  alternatives: BuildAlternative[];
};

export type BuildApproval = {
  approval_id: string;
  build_id: string;
  build_session_id: string;
  approved_at: string;
  status: "approved";
  selected_skus: Record<string, string>;
  total_price_vnd: number;
  catalog_version: string;
  rules_version: string;
  disclaimer_vi: string;
};

export type CartReadyHandoff = {
  handoff_id: string;
  build_id: string;
  build_session_id: string;
  created_at: string;
  status: "cart_ready";
  approval: BuildApproval;
  total_price_vnd: number;
  item_count: number;
  mock_cart_payload: {
    provider: string;
    disclaimer_vi: string;
    items: Array<{ sku: string; url: string }>;
  };
  warnings_vi: string[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_AGENT_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    }
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function createSession(): Promise<BuildSession> {
  return request<BuildSession>("/sessions", {
    method: "POST",
    body: JSON.stringify({ locale: "vi-VN", channel: "web" })
  });
}

export function submitIntent(
  buildSessionId: string,
  message: string,
  confirm = false,
  preset?: UseCase,
  useLlm = !confirm
): Promise<IntentResponse> {
  return request<IntentResponse>(`/sessions/${buildSessionId}/intent`, {
    method: "POST",
    body: JSON.stringify({ message, confirm, preset, use_llm: useLlm })
  });
}

export function generateBuild(buildSessionId: string): Promise<BuildArtifact> {
  return request<BuildArtifact>(`/sessions/${buildSessionId}/generate`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function getBuild(buildId: string): Promise<BuildArtifact> {
  return request<BuildArtifact>(`/builds/${buildId}`);
}

export function getBuildAlternatives(buildId: string): Promise<BuildAlternativesResponse> {
  return request<BuildAlternativesResponse>(`/builds/${buildId}/alternatives`);
}

export function applyBuildAlternative(buildId: string, variantId: string): Promise<BuildArtifact> {
  return request<BuildArtifact>(`/builds/${buildId}/alternatives/${variantId}/apply`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function approveBuild(buildId: string): Promise<CartReadyHandoff> {
  return request<CartReadyHandoff>(`/builds/${buildId}/approve`, {
    method: "POST",
    body: JSON.stringify({})
  });
}
