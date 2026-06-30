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
export type BuildFeedbackRating = "thumbs_up" | "thumbs_down";
export type BuildFeedbackReason =
  | "fits_need"
  | "good_value"
  | "clear_explanation"
  | "confusing_explanation"
  | "over_budget"
  | "missing_part"
  | "wrong_performance_fit"
  | "compatibility_concern"
  | "price_or_stock_concern"
  | "other";
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
  monitor_count: number | null;
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

export type BuildRecommendedAddOn = {
  kind: "monitor" | "cooler";
  sku: string;
  name: string;
  category: string;
  price_vnd: number;
  url: string;
  brand: string | null;
  specs_confidence: "verified" | "partial" | "inferred";
  reason_vi: string;
  fit_notes_vi: string[];
  warnings_vi: string[];
  optional: boolean;
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
    source: "catalog_spec" | "intent" | "rule" | "benchmark";
    source_label: string | null;
    source_url: string | null;
  }>;
  balance: {
    score: number;
    interpretation_vi: string;
    limiting_component: "cpu" | "gpu" | "ram" | "storage" | "unknown";
    suggestions_vi: string[];
    factors: Record<string, number>;
  } | null;
  workload_profiles: Array<{
    name: string;
    category: "video_editing" | "three_d" | "photo_editing" | "streaming" | "local_llm";
    fit_level: PerformanceProfile["fit_level"];
    bottlenecks: Array<
      | "cpu_bound"
      | "gpu_bound"
      | "ram_limited"
      | "storage_limited"
      | "vram_limited"
      | "cuda_preferred"
    >;
    requirement_summary_vi: string;
    recommendation_vi: string;
  }>;
};

export type BuildOrchestrationStep = {
  agent:
    | "intent"
    | "catalog"
    | "optimizer"
    | "compatibility"
    | "performance"
    | "explainer"
    | "commerce"
    | "validator";
  status: "completed" | "blocked";
  summary_vi: string;
  inputs: Record<string, string | number | boolean | null>;
  outputs: Record<string, string | number | boolean | null>;
  tool_calls: string[];
  latency_ms: number;
  model_version: string;
  started_at: string;
  completed_at: string;
};

export type OptimizerTrace = {
  max_iterations: number;
  applied_iteration_count: number;
  rejected_iteration_count: number;
  priority_overrides: string[];
  budget_allocation: {
    use_case: string;
    budget_max_vnd: number | null;
    weights: Record<string, number>;
    target_amounts_vnd: Record<string, number>;
    reserved_peripherals_vnd: number;
    reserved_services_vnd: number;
    notes_vi: string[];
  };
  iterations: Array<{
    iteration: number;
    candidate_kind: string | null;
    candidate_label_vi: string | null;
    decision: "accepted" | "rejected" | "skipped";
    score: number | null;
    priority: string | null;
    price_delta_vnd: number | null;
    total_price_vnd: number | null;
    changed_slots: string[];
    reason_vi: string;
  }>;
};

export type TraceReplayEvent = {
  event_id: string;
  sequence: number;
  build_session_id: string;
  build_id: string;
  build_version: number;
  generated_at: string;
  agent: BuildOrchestrationStep["agent"];
  status: BuildOrchestrationStep["status"];
  summary_vi: string;
  inputs_redacted: Record<string, string | number | boolean | null>;
  tool_calls: string[];
  outputs_redacted: Record<string, string | number | boolean | null>;
  latency_ms: number;
  model_version: string;
};

export type BuildTraceReplay = {
  build_session_id: string;
  build_id: string;
  build_version: number;
  generated_at: string;
  replay_status: "complete" | "empty";
  events: TraceReplayEvent[];
};

export type SessionTraceReplay = {
  build_session_id: string;
  generated_build_count: number;
  redaction_policy_vi: string;
  support_export_text: string;
  builds: BuildTraceReplay[];
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
  optimizer_trace: OptimizerTrace | null;
  recommended_addons: BuildRecommendedAddOn[];
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

export type BuildAlternativeRanking = {
  rank: number;
  score: number;
  priority: "recommended" | "good_fit" | "situational" | "low_priority";
  reasons_vi: string[];
};

export type BuildAlternative = {
  variant_id: string;
  kind: "ram_upgrade" | "storage_upgrade" | "nvidia_gpu" | "psu_headroom" | "budget_saver";
  label_vi: string;
  summary_vi: string;
  ranking: BuildAlternativeRanking;
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

export type ParsedBuildIterationCommand = {
  command_vi: string;
  command_type:
    | "cheaper"
    | "quieter"
    | "more_performance"
    | "more_storage"
    | "more_memory"
    | "nvidia_gpu"
    | "unknown";
  target_budget_max_vnd: number | null;
  priority_label_vi: string;
  summary_vi: string;
};

export type BuildIterationResponse = {
  source_build_id: string;
  source_build_version: number;
  command: ParsedBuildIterationCommand;
  selected_alternative: BuildAlternative;
  applied_build: BuildArtifact;
  rejected_candidates: OptimizerTrace["iterations"];
};

export type UpgradePlanRequest = {
  current_pc: string;
  target_use_case?: UseCase;
  upgrade_budget_max_vnd?: number | null;
  target_resolution?: string | null;
  target_refresh_hz?: number | null;
  confirmed_existing_system?: ExistingSystemOverrides | null;
};

export type ExistingSystemParseRequest = {
  current_pc: string;
};

export type ExistingSystemOverrides = {
  cpu_name?: string | null;
  mainboard_name?: string | null;
  ram_gb?: number | null;
  gpu_name?: string | null;
  psu_wattage_w?: number | null;
  psu_pcie_8pin_connectors?: number | null;
  case_gpu_clearance_mm?: number | null;
  storage_summary?: string | null;
};

export type ExistingSystemSpec = {
  raw_text: string;
  cpu_name: string | null;
  cpu_tdp_w: number | null;
  mainboard_name: string | null;
  ram_gb: number | null;
  gpu_name: string | null;
  gpu_tier_score: number | null;
  psu_wattage_w: number | null;
  psu_pcie_8pin_connectors: number | null;
  case_name: string | null;
  case_gpu_clearance_mm: number | null;
  storage_summary: string | null;
  unknown_fields: string[];
};

export type ExistingSystemParseResponse = {
  parsed_at: string;
  existing_system: ExistingSystemSpec;
  confirmation_required: boolean;
  summary_vi: string;
  warnings_vi: string[];
  next_steps_vi: string[];
};

export type ExistingPartDecision = {
  slot: BuildSlot;
  decision: "reuse" | "replace" | "optional_upgrade" | "unknown";
  reason_vi: string;
};

export type UpgradeCompatibilityCheck = {
  code: string;
  status: "pass" | "warn" | "block";
  explanation_vi: string;
  facts: Record<string, number | string | null>;
};

export type UpgradeRecommendation = {
  slot: "vga";
  sku: string;
  name: string;
  category: string;
  price_vnd: number;
  url: string;
  brand: string | null;
  specs_confidence: "verified" | "partial" | "inferred";
  impact: "high" | "medium" | "low";
  replaced_component: string | null;
  compatibility_status: "pass" | "warn" | "block";
  checks: UpgradeCompatibilityCheck[];
  reasons_vi: string[];
  warnings_vi: string[];
};

export type UpgradePlanResponse = {
  plan_id: string;
  generated_at: string;
  catalog_version: string;
  rules_version: string;
  request: Required<UpgradePlanRequest>;
  existing_system: ExistingSystemSpec;
  recommendations: UpgradeRecommendation[];
  reuse_decisions: ExistingPartDecision[];
  total_upgrade_cost_vnd: number;
  warnings_vi: string[];
  next_steps_vi: string[];
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

export type BuildApprovalRequest = {
  selected_addon_skus?: string[];
};

export type CartReadyHandoff = {
  handoff_id: string;
  build_id: string;
  build_session_id: string;
  created_at: string;
  status: "cart_ready";
  approval: BuildApproval;
  total_price_vnd: number;
  add_on_total_price_vnd: number;
  shopping_list_total_price_vnd: number;
  item_count: number;
  selected_addons: BuildRecommendedAddOn[];
  mock_cart_payload: {
    provider: string;
    disclaimer_vi: string;
    items: Array<{ sku: string; url: string; name?: string }>;
  };
  warnings_vi: string[];
};

export type PartFeedbackRequest = {
  slot: BuildSlot;
  sku: string;
  rating: BuildFeedbackRating;
  reason_tags?: BuildFeedbackReason[];
  comment_vi?: string | null;
};

export type BuildFeedbackRequest = {
  rating: BuildFeedbackRating;
  reason_tags?: BuildFeedbackReason[];
  comment_vi?: string | null;
  part_feedback?: PartFeedbackRequest[];
};

export type PartFeedback = {
  slot: BuildSlot;
  sku: string;
  name: string;
  rating: BuildFeedbackRating;
  reason_tags: BuildFeedbackReason[];
  comment_vi: string | null;
};

export type BuildFeedback = {
  feedback_id: string;
  build_id: string;
  build_session_id: string;
  build_version: number;
  catalog_version: string;
  rules_version: string;
  created_at: string;
  rating: BuildFeedbackRating;
  reason_tags: BuildFeedbackReason[];
  comment_vi: string | null;
  part_feedback: PartFeedback[];
  review_queue_status: "not_queued" | "queued";
  review_queue_reason_vi: string | null;
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

export function getSessionTrace(buildSessionId: string): Promise<SessionTraceReplay> {
  return request<SessionTraceReplay>(`/sessions/${buildSessionId}/trace`);
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

export function iterateBuild(buildId: string, commandVi: string): Promise<BuildIterationResponse> {
  return request<BuildIterationResponse>(`/builds/${buildId}/iterate`, {
    method: "POST",
    body: JSON.stringify({ command_vi: commandVi })
  });
}

export function createGpuUpgradePlan(payload: UpgradePlanRequest): Promise<UpgradePlanResponse> {
  return request<UpgradePlanResponse>("/upgrade-plans/gpu", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function parseExistingSystem(payload: ExistingSystemParseRequest): Promise<ExistingSystemParseResponse> {
  return request<ExistingSystemParseResponse>("/upgrade-plans/existing-system/parse", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function approveBuild(
  buildId: string,
  payload: BuildApprovalRequest = {}
): Promise<CartReadyHandoff> {
  return request<CartReadyHandoff>(`/builds/${buildId}/approve`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function submitBuildFeedback(
  buildId: string,
  payload: BuildFeedbackRequest
): Promise<BuildFeedback> {
  return request<BuildFeedback>(`/builds/${buildId}/feedback`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getBuildFeedback(buildId: string): Promise<BuildFeedback[]> {
  return request<BuildFeedback[]>(`/builds/${buildId}/feedback`);
}
