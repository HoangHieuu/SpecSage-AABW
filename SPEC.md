# PC Build Copilot — Product Specification

**Product:** PC Build Copilot for Phong Vũ (Retail Track)  
**Version:** 1.0  
**Status:** Draft  
**Primary language:** Vietnamese (UI, explanations, error messages)  
**Secondary language:** English (technical labels, SKU references)

---

## 1. Document Purpose

This specification defines the complete functional and non-functional requirements for **PC Build Copilot** — an agentic AI system that helps Phong Vũ customers and staff design compatible, budget-aware, purchase-ready PC configurations from natural-language intent.

The document is organized by **product phases**. Each phase contains user stories and acceptance criteria. Phases describe capability maturity, not delivery deadlines.

---

## 2. Product Vision

### 2.1 Problem Statement

Phong Vũ offers a manual PC configurator at [phongvu.vn/buildpc](https://phongvu.vn/buildpc) and human consultation via Messenger. Customers must understand component categories, compatibility constraints, and budget trade-offs without intelligent guidance. This creates:

- High abandonment for first-time builders
- Compatibility mistakes (socket, PSU, RAM, case clearance)
- Suboptimal budget allocation (CPU/GPU imbalance)
- Pressure on human consultants for repeatable questions
- Missed upsell and promo opportunities

### 2.2 Product Vision

> A multi-agent PC advisory system that converts customer intent into validated, explained, and commerce-ready builds using Phong Vũ's catalog, compatibility rules, and promotional context.

### 2.3 Product Principles

1. **Agentic, not conversational** — The system plans, uses tools, iterates, validates, and outputs actionable builds.
2. **Deterministic where safety matters** — Compatibility and PSU rules are code-enforced, not LLM-guessed.
3. **Explain every trade-off** — Users understand *why* each part was chosen.
4. **Commerce-aware** — Recommendations respect stock, price, promos, and cart readiness.
5. **Vietnamese-first** — Natural interaction and education in Vietnamese; technical accuracy preserved.
6. **Staff-augmenting** — Same intelligence available to showroom consultants.

### 2.4 Goals

| Goal | Success Indicator |
|------|-------------------|
| Reduce time-to-valid-config | User receives a complete compatible build in one session |
| Increase build confidence | User can explain why each major part fits their needs |
| Prevent compatibility errors | Zero invalid builds pass final validation |
| Improve conversion | Generated configs are cart-ready with correct SKUs and prices |
| Scale expert knowledge | Staff and customers receive consistent recommendations |

### 2.5 Non-Goals

- Selling components outside Phong Vũ catalog
- Providing overclocking tutorials or hardware modification guides
- Replacing Phong Vũ warranty, RMA, or repair services
- General tech support unrelated to PC building
- Autonomous payment or checkout without user confirmation
- Medical, legal, or financial advice

---

## 3. Users & Personas

| Persona | Description | Primary Needs |
|---------|-------------|---------------|
| **First-time Builder** | Limited hardware knowledge, budget-conscious | Simple language, safe defaults, full-build guidance |
| **Gaming Enthusiast** | Knows brands/games, wants performance per đồng | FPS estimates, GPU focus, upgrade headroom |
| **Creator / Pro User** | Video, 3D, AI workloads | VRAM, RAM, storage, stability over RGB |
| **Upgrade Buyer** | Owns existing PC, wants targeted improvements | Bottleneck analysis, reuse compatibility |
| **Parent / Gift Buyer** | Buying for someone else | Age-appropriate performance, value, warranty clarity |
| **Showroom Staff** | Sales consultant on floor | Fast config generation, objection handling, promo recall |
| **Ops / Merchandising Admin** | Internal Phong Vũ team | Rule management, catalog health, analytics |

---

## 4. System Overview

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
│   Web Copilot  │  Staff Console  │  Embed Widget  │  API       │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     Orchestrator (Build Session)                 │
│          state machine · iteration loop · audit trail            │
└────────────────────────────┬────────────────────────────────────┘
                             │
     ┌───────────┬───────────┼───────────┬───────────┐
     ▼           ▼           ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Intent  │ │ Catalog │ │Compat.  │ │Perform. │ │Commerce │
│ Agent   │ │ Agent   │ │ Agent   │ │ Agent   │ │ Agent   │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │           │           │           │           │
     └───────────┴───────────┴─────┬─────┴───────────┘
                                   ▼
                    ┌──────────────────────────┐
                    │ Optimizer Agent          │
                    └────────────┬─────────────┘
                                 ▼
                    ┌──────────────────────────┐
                    │ Explainer Agent          │
                    └────────────┬─────────────┘
                                 ▼
                    ┌──────────────────────────┐
                    │ Validator Agent            │
                    └────────────┬─────────────┘
                                 ▼
                    ┌──────────────────────────┐
                    │ Build Artifact + Actions   │
                    └──────────────────────────┘
```

### 4.2 Core Domain Objects

| Object | Description |
|--------|-------------|
| **Build Session** | A single advisory conversation with state, iterations, and outputs |
| **Build Intent** | Structured representation of user goals, constraints, and preferences |
| **Component Slot** | Required or optional part category (CPU, GPU, RAM, etc.) |
| **SKU** | Phong Vũ product with price, specs, stock, promo eligibility |
| **Build Configuration** | A set of selected SKUs across slots |
| **Compatibility Report** | Pass/fail checks with severity and remediation |
| **Performance Profile** | Estimated workload suitability and bottleneck notes |
| **Build Artifact** | Final export: parts list, explanations, warnings, cart payload |
| **Upgrade Plan** | Ordered list of recommended replacements for existing systems |

### 4.3 Required Component Slots (Full Build)

| Slot | Required | Notes |
|------|----------|-------|
| CPU | Yes | |
| Mainboard | Yes | |
| RAM | Yes | |
| Storage (SSD and/or HDD) | Yes | At least one boot storage |
| GPU | Conditional | Required for gaming/creator; optional for office if iGPU sufficient |
| PSU | Yes | |
| Case | Yes | |
| Cooler | Conditional | Required if CPU TDP exceeds stock cooler rating or user requests |
| Monitor | Optional | Strongly recommended for gaming/creator presets |
| Keyboard | Optional | |
| Mouse | Optional | |
| Headset / Speakers | Optional | |
| OS / Software | Optional | Windows, Office, antivirus bundles |

---

## 5. Phases

---

## Phase 1 — Session Foundation & Intent Capture

Establish a build session, collect structured intent from natural language, and confirm understanding before generating parts.

### US-1.1 Start a Build Session

**As a** customer  
**I want to** start a new PC build session from the Phong Vũ website  
**So that** I can describe what I need without knowing component terminology

**Acceptance Criteria:**

- [ ] User can open PC Build Copilot from a dedicated page and from contextual entry points (Build PC page, Gaming PC category, PC AI category)
- [ ] A unique `build_session_id` is created and persisted for the duration of the session
- [ ] Session stores timestamp, locale (`vi-VN` default), channel (`web`, `staff`, `api`)
- [ ] User sees a welcome state explaining what the copilot can and cannot do
- [ ] User can start without logging in; logged-in users have sessions linked to account when available

### US-1.2 Express Intent in Natural Language

**As a** first-time builder  
**I want to** describe my needs in plain Vietnamese  
**So that** I don't have to learn hardware jargon first

**Acceptance Criteria:**

- [ ] User can submit free-text intent (e.g., "PC gaming 25 triệu chơi Valorant và LMHT")
- [ ] System extracts and stores structured fields: `use_case`, `budget_min`, `budget_max`, `target_games`, `target_apps`, `performance_targets`, `form_factor`, `brand_preferences`, `noise_preferences`, `aesthetic_preferences`
- [ ] System handles partial information without failing — missing budget triggers a clarifying question, not an error
- [ ] System supports mixed Vietnamese-English input (e.g., "RTX 5060 Ti", "144Hz")
- [ ] Ambiguous budget phrases ("khoảng 20 triệu", "dưới 25 triệu", "tầm trung") map to numeric ranges with documented interpretation

### US-1.3 Guided Intent Clarification

**As a** customer with vague requirements  
**I want to** answer a short set of smart follow-up questions  
**So that** the copilot understands my priorities before recommending parts

**Acceptance Criteria:**

- [ ] When required fields are missing, system asks at most one focused question per turn
- [ ] Clarification questions adapt to detected use case (gaming asks games/resolution; creator asks apps; office asks monitor count)
- [ ] User can skip non-critical questions; skipped fields use safe defaults documented in the session
- [ ] User can change prior answers without restarting the session
- [ ] Intent summary card is shown and requires explicit or implicit confirmation before build generation

### US-1.4 Use Case Presets

**As a** customer  
**I want to** select a preset use case  
**So that** I can start quickly without writing a long description

**Acceptance Criteria:**

- [ ] Presets available: Gaming, Creator/Đồ họa, Office/Văn phòng, Student/Sinh viên, AI/Local LLM, Streaming, Compact/Mini ITX
- [ ] Each preset pre-fills budget allocation weights and required slots
- [ ] Selecting a preset does not skip budget and performance confirmation
- [ ] Preset labels and descriptions match Phong Vũ site taxonomy (PC Gaming, PC Đồ Họa, PC Văn Phòng, PC AI)

### US-1.5 Session Recovery

**As a** returning customer  
**I want to** resume an interrupted build session  
**So that** I don't lose my progress

**Acceptance Criteria:**

- [ ] Session state survives page refresh within TTL (configurable, default 7 days for logged-in, 24h for anonymous via local storage token)
- [ ] User can view prior generated builds within the same session
- [ ] User can fork a prior build into a new variation ("cheaper", "more FPS", "quieter")
- [ ] Session history records each intent revision and configuration version

---

## Phase 2 — Catalog Intelligence & Product Grounding

Connect recommendations to real Phong Vũ products with accurate specs, pricing, and availability signals.

### US-2.1 Grounded Product Catalog

**As a** system  
**I need to** recommend only real Phong Vũ SKUs  
**So that** users can actually purchase what is suggested

**Acceptance Criteria:**

- [ ] Catalog contains SKU ID, name, brand, category, price (VND), list price, promo price, product URL, image URL, warranty info
- [ ] Catalog includes structured specs per category (see Section 8 — Data Model)
- [ ] No recommendation references SKUs absent from catalog
- [ ] Catalog refresh pipeline documented with source, frequency, and fallback behavior
- [ ] Catalog versioning is stored per `build_session_id` so builds are reproducible

### US-2.2 Category-Aware Search & Retrieval

**As a** catalog agent  
**I want to** query products by structured filters  
**So that** candidates are relevant before optimization

**Acceptance Criteria:**

- [ ] Supports filters: category, price range, brand, socket, chipset, memory type, wattage, form factor, VRAM, capacity, slot type
- [ ] Returns ranked candidates with relevance score and exclusion reason for rejected items
- [ ] Supports semantic search for fuzzy queries ("card đồ họa tầm trung cho 1080p")
- [ ] Retrieval is deterministic given the same intent, catalog version, and rules version
- [ ] Query latency target documented in NFRs (Section 12)

### US-2.3 Price & Promotion Awareness

**As a** customer  
**I want to** see accurate prices and applicable promotions  
**So that** the total cost matches what I'll pay on Phong Vũ

**Acceptance Criteria:**

- [ ] Build total uses promo price when eligible; shows strikethrough list price when discounted
- [ ] Promo badges displayed per SKU (combo discount, bundle gift, flash sale, trade-in)
- [ ] System detects catalog-level promos: combo PC + monitor, free assembly, bundled peripherals
- [ ] Total price breakdown shows parts subtotal, discounts, estimated assembly service, optional peripherals
- [ ] Price snapshot timestamp included in build artifact

### US-2.4 Stock & Fulfillment Signals

**As a** customer  
**I want to** know if parts are available before I commit  
**So that** I don't plan a build I can't buy

**Acceptance Criteria:**

- [ ] Each SKU shows stock status: In Stock, Low Stock, Out of Stock, Pre-order, Showroom Only
- [ ] Out-of-stock SKUs are excluded from auto-generated builds unless user explicitly requests keep-and-notify
- [ ] System can substitute in-stock alternatives of same tier with explanation
- [ ] Optional showroom availability by region when data is provided
- [ ] Fulfillment estimate shown when data exists (ship-to-home vs pickup)

### US-2.5 Catalog Integrity Monitoring

**As an** admin  
**I want to** detect broken or incomplete catalog records  
**So that** the copilot doesn't recommend unusable products

**Acceptance Criteria:**

- [ ] Admin dashboard flags SKUs missing required specs for their category
- [ ] Warnings for duplicate SKUs, stale prices, broken URLs, discontinued items still indexed
- [ ] Builds blocked if critical catalog fields missing for a selected SKU
- [ ] Catalog health score computed daily

---

## Phase 3 — Compatibility & Safety Engine

Enforce hardware compatibility and safety constraints with deterministic rules.

### US-3.1 CPU ↔ Mainboard Socket Validation

**As a** system  
**I need to** ensure CPU and mainboard sockets match  
**So that** the build is physically compatible

**Acceptance Criteria:**

- [ ] Every CPU + mainboard pair validates `cpu.socket == mainboard.socket`
- [ ] Invalid pairs are hard-blocked with error code `COMPAT_SOCKET_MISMATCH`
- [ ] Suggested fix includes alternative mainboards or CPUs in the same budget tier

### US-3.2 Chipset & BIOS / Generation Support

**As a** system  
**I need to** validate chipset and CPU generation compatibility  
**So that** the PC boots without BIOS surprises

**Acceptance Criteria:**

- [ ] Rules enforce supported CPU generations per chipset (e.g., B760 + 14th gen, X870 + Ryzen 9000)
- [ ] Warning issued when CPU requires BIOS update on selected board (`COMPAT_BIOS_RISK`, severity: warning)
- [ ] Explanation includes whether Phong Vũ assembly service can perform BIOS update when applicable

### US-3.3 Memory Type, Speed & Capacity

**As a** system  
**I need to** validate RAM compatibility with CPU and mainboard  
**So that** memory runs at supported specifications

**Acceptance Criteria:**

- [ ] RAM type (DDR4/DDR5) must match mainboard support
- [ ] Total RAM capacity must not exceed mainboard max
- [ ] Module count must not exceed available DIMM slots
- [ ] Warn if RAM speed exceeds board official support (`COMPAT_RAM_SPEED`, severity: warning)
- [ ] Creator and AI presets enforce minimum RAM thresholds by use case

### US-3.4 GPU ↔ Case Clearance & Slot Validation

**As a** system  
**I need to** ensure the GPU fits the case and PSU can connect  
**So that** the build assembles without physical conflicts

**Acceptance Criteria:**

- [ ] `gpu.length_mm <= case.max_gpu_length_mm` enforced
- [ ] `gpu.slot_width <= case.available_pcie_slots` considered where data exists
- [ ] Warn on tight clearance (<15mm margin) with `COMPAT_GPU_TIGHT_FIT`
- [ ] iGPU-only office builds may omit discrete GPU with explicit performance disclaimer

### US-3.5 PSU Wattage & Rail Adequacy

**As a** system  
**I need to** size PSU correctly for the configuration  
**So that** the system is stable and safe

**Acceptance Criteria:**

- [ ] Required wattage = CPU TDP + GPU TDP + 100W base + peripheral headroom (formula documented)
- [ ] Selected PSU rated wattage must be ≥ required wattage × safety factor (default 1.2)
- [ ] Hard-block if PSU lacks required GPU power connectors (8-pin, 12VHPWR, etc.)
- [ ] Efficiency rating (80+ Bronze/Gold) surfaced as recommendation, not hard rule
- [ ] Report shows wattage budget breakdown per component

### US-3.6 Cooler ↔ Case & CPU TDP

**As a** system  
**I need to** validate cooler compatibility and thermal adequacy  
**So that** thermal throttling and clearance issues are avoided

**Acceptance Criteria:**

- [ ] Cooler socket support must match CPU socket
- [ ] Cooler height must fit case `max_cooler_height_mm`
- [ ] AIO radiator size supported by case radiator mounts when applicable
- [ ] Stock cooler auto-selected for low-TDP CPUs unless user requests aftermarket cooling
- [ ] High-TDP CPUs (threshold configurable) require adequate cooler — hard-block undersized air coolers

### US-3.7 Storage ↔ M.2 / SATA Port Limits

**As a** system  
**I need to** validate storage devices against board ports  
**So that** all drives are installable and bootable

**Acceptance Criteria:**

- [ ] Total M.2 drives ≤ mainboard M.2 slot count
- [ ] SATA drives ≤ mainboard SATA port count
- [ ] Warn when M.2 slot shares lanes with SATA ports (board-specific rules)
- [ ] Boot drive must be present; NVMe recommended for OS with documented rationale
- [ ] Creator builds enforce minimum storage capacity and type mix rules

### US-3.8 Compatibility Report Artifact

**As a** customer  
**I want to** see a clear compatibility report  
**So that** I trust the build before purchase

**Acceptance Criteria:**

- [ ] Report lists all checks with status: Pass, Warning, Block
- [ ] Each failed check includes human-readable Vietnamese explanation and remediation
- [ ] Final build cannot reach `approved` status with any Block-level issue
- [ ] Report version stored with rules version and catalog version

---

## Phase 4 — Performance Modeling & Workload Fit

Estimate whether the configuration meets the user's performance goals.

### US-4.1 Gaming Performance Estimates

**As a** gaming customer  
**I want to** see expected FPS for my target games  
**So that** I know the build matches my expectations

**Acceptance Criteria:**

- [ ] Supports estimates for user-specified games from a maintained benchmark lookup table
- [ ] Estimates include resolution and quality preset (e.g., 1080p High, 1440p Ultra)
- [ ] FPS shown as range (p50–p90) with disclaimer that results vary
- [ ] System flags when target (e.g., 144 FPS) is unlikely at selected resolution (`PERF_BELOW_TARGET`)
- [ ] Suggests GPU tier upgrade or resolution adjustment when target missed

### US-4.2 Creator & Productivity Workload Fit

**As a** creator  
**I want to** know if my build suits Premiere, Blender, Photoshop, or AI tools  
**So that** I invest in the right GPU, RAM, and storage

**Acceptance Criteria:**

- [ ] Use case profiles for: video editing, 3D rendering, photo editing, streaming, local LLM inference
- [ ] Outputs bottleneck summary: CPU-bound, GPU-bound, RAM-limited, storage-limited
- [ ] VRAM and RAM minimum thresholds enforced per app profile
- [ ] NVMe speed and capacity recommendations differ for scratch disk vs archive storage
- [ ] AI/LLM profile recommends GPU VRAM tiers for specified model classes (e.g., 7B, 13B, 70B) with qualitative labels (entry, good, ideal)

### US-4.3 Office & General Use Adequacy

**As an** office buyer  
**I want to** avoid overspending on unnecessary gaming hardware  
**So that** budget goes to reliability and warranty instead

**Acceptance Criteria:**

- [ ] Office profile may recommend iGPU configurations when discrete GPU unnecessary
- [ ] Quiet operation and power efficiency weighted in optimizer
- [ ] Supports multi-monitor count as input; validates GPU output and dock requirements
- [ ] Explains why discrete GPU was included or omitted

### US-4.4 Bottleneck & Balance Analysis

**As an** enthusiast  
**I want to** understand component balance  
**So that** I don't pair a weak CPU with a flagship GPU

**Acceptance Criteria:**

- [ ] Balance score computed for CPU/GPU pairing (0–100) with plain-language interpretation
- [ ] Warn on severe imbalance (`PERF_IMBALANCE`, severity: warning)
- [ ] Upgrade suggestions identify the limiting component first
- [ ] Comparison mode can show balanced vs max-FPS skewed variants

### US-4.5 Monitor Pairing Recommendations

**As a** customer  
**I want to** get a monitor matched to my PC capability  
**So that** I don't buy 240Hz when my GPU sustains 120 FPS

**Acceptance Criteria:**

- [ ] Recommends resolution and refresh rate aligned to GPU tier and target games
- [ ] Warns when monitor exceeds PC capability (`PERF_MONITOR_OVERSPEC`)
- [ ] Includes panel type guidance (IPS vs VA) as optional preference, not hard rule
- [ ] Supports ultrawide and dual-monitor setups as explicit user options

---

## Phase 5 — Build Optimization & Iteration

Automatically assemble and refine configurations within constraints.

### US-5.1 Initial Build Generation

**As a** customer  
**I want to** receive a complete parts list after confirming intent  
**So that** I have a starting point without manual picking

**Acceptance Criteria:**

- [ ] System generates all required slots populated with catalog SKUs
- [ ] Generation completes in bounded iterations (max documented; default 5)
- [ ] Total price respects `budget_max`; if impossible, returns closest option with explicit over-budget notice and gap amount
- [ ] Output includes version `build_v1`, timestamp, and intent snapshot

### US-5.2 Budget Allocation Strategy

**As a** system  
**I need to** allocate budget by use case  
**So that** money goes to components that matter most

**Acceptance Criteria:**

- [ ] Allocation weights configurable per use case (e.g., gaming: GPU 40–50%; office: CPU/SSD weighted)
- [ ] User priority overrides supported: "ưu tiên VGA", "ưu tiên im lặng", "ưu tiên RGB"
- [ ] Peripheral budget reserved only when user includes monitor/peripherals
- [ ] Assembly and Windows license optionally included in budget when user selects

### US-5.3 Iterative Refinement Loop

**As a** customer  
**I want to** ask for adjustments in natural language  
**So that** the build evolves without starting over

**Acceptance Criteria:**

- [ ] Supports commands: cheaper, quieter, more FPS, Intel instead of AMD, add monitor, remove RGB, keep under X triệu
- [ ] Each iteration produces a new `build_vN` with diff from previous version
- [ ] Diff highlights changed SKUs, price delta, and compatibility/performance impact
- [ ] Prior approved builds remain accessible in session history

### US-5.4 Alternative Options per Slot

**As a** customer  
**I want to** see 2–3 alternatives for major components  
**So that** I can choose based on preference without breaking compatibility

**Acceptance Criteria:**

- [ ] Alternatives offered for CPU, GPU, RAM, SSD at minimum
- [ ] Each alternative shows price delta, performance delta, and compatibility status
- [ ] One-click swap re-runs validation and performance analysis
- [ ] Alternatives filtered to in-stock SKUs by default

### US-5.5 Pareto-Efficient Variants

**As a** customer  
**I want to** compare "Best Value", "Best Performance", and "Balanced" variants  
**So that** I can choose my preferred trade-off

**Acceptance Criteria:**

- [ ] System can generate three labeled variants from same intent
- [ ] Variants share intent but differ in optimizer weights
- [ ] Side-by-side comparison table: total price, FPS estimate, RAM, VRAM, wattage, noise tier
- [ ] User can promote any variant to primary build

---

## Phase 6 — Explanation & Customer Education

Make recommendations understandable and trustworthy.

### US-6.1 Per-Part Rationale

**As a** first-time builder  
**I want to** understand why each part was chosen  
**So that** I learn and feel confident purchasing

**Acceptance Criteria:**

- [ ] Every required slot includes a 1–3 sentence Vietnamese explanation
- [ ] Explanation references user intent (game, app, budget) — not generic marketing copy
- [ ] Technical terms include brief parenthetical definitions on first use
- [ ] Explanations regenerated when SKU changes, not copied from prior build

### US-6.2 Trade-off Narratives

**As a** customer  
**I want to** see what I gain and lose with key decisions  
**So that** I can make informed choices

**Acceptance Criteria:**

- [ ] For major forks (e.g., RTX 5060 vs 5070), shows cost delta, FPS delta, power delta
- [ ] Uses comparison format: "Nếu chọn A → ...; Nếu chọn B → ..."
- [ ] Links trade-offs to user's stated priorities when possible

### US-6.3 Anti-Hallucination Guardrails

**As a** business stakeholder  
**I need** explanations grounded in catalog and rules  
**So that** the copilot never invents specs or prices

**Acceptance Criteria:**

- [ ] Explainer agent receives only validated build data and catalog fields as context
- [ ] Numeric claims (price, FPS, wattage) must trace to source fields in build artifact
- [ ] If data missing, system says "không đủ dữ liệu" instead of guessing
- [ ] Citation links to Phong Vũ product pages included per SKU

### US-6.4 Glossary & Contextual Help

**As a** novice user  
**I want to** tap on terms like "DDR5" or "80 Plus"  
**So that** I understand without leaving the flow

**Acceptance Criteria:**

- [ ] Glossary covers top 50 PC building terms in Vietnamese
- [ ] Inline tooltips available on part spec chips
- [ ] Glossary entries are short (<80 words), neutral, and non-brand-biased unless factual

### US-6.5 Build Summary for Sharing

**As a** customer  
**I want to** share a readable summary with family or friends  
**So that** I can get a second opinion before buying

**Acceptance Criteria:**

- [ ] Shareable link or image card with parts, total, use case, and key rationale
- [ ] Shared view is read-only and does not expose internal session tokens
- [ ] Optional hide-price mode for gift scenarios
- [ ] QR code for showroom staff scan

---

## Phase 7 — Upgrade Planning & Existing Systems

Support customers improving an existing PC, not only greenfield builds.

### US-7.1 Existing System Intake

**As an** upgrade buyer  
**I want to** input my current specs  
**So that** recommendations respect what I already own

**Acceptance Criteria:**

- [ ] User can enter current CPU, mainboard, RAM, GPU, PSU, case, storage via form or natural language
- [ ] Partial specs accepted; unknown fields marked `unknown` with conservative assumptions
- [ ] User can import a prior Phong Vũ order by order ID when authenticated and integrated
- [ ] System confirms parsed existing spec summary before planning upgrades

### US-7.2 Bottleneck-Driven Upgrade Priority

**As an** upgrade buyer  
**I want to** know which component to upgrade first  
**So that** I spend money where it matters

**Acceptance Criteria:**

- [ ] Outputs ordered upgrade recommendations with expected impact (High/Medium/Low)
- [ ] Each item includes compatibility check against existing system
- [ ] Warns when upgrade requires cascading changes (e.g., new CPU → new board → new RAM)
- [ ] Estimates total cost for single-step and full-path upgrades

### US-7.3 Reuse vs Replace Decisions

**As a** budget-conscious upgrader  
**I want to** keep reusable parts when safe  
**So that** I don't replace components unnecessarily

**Acceptance Criteria:**

- [ ] System marks each existing part: Reuse, Replace, Optional Upgrade
- [ ] PSU reuse validated against new GPU power draw
- [ ] Case reuse validated against new GPU length and cooler height
- [ ] Clear warnings when reusing old part limits performance (DDR4 platform, PCIe 3.0)

### US-7.4 Incremental Upgrade Plans

**As a** customer planning over months  
**I want to** a phased upgrade roadmap  
**So that** I can buy in stages

**Acceptance Criteria:**

- [ ] Roadmap split into Phase A / B / C with monthly or budget-based triggers
- [ ] Each phase produces a valid intermediate system state
- [ ] No phase recommends a part that will be incompatible with planned future phase without explicit warning
- [ ] Exportable roadmap PDF or share link

---

## Phase 8 — Commerce Actions & Checkout Handoff

Turn validated builds into Phong Vũ purchases.

### US-8.1 Add Build to Cart

**As a** customer  
**I want to** add all parts to my Phong Vũ cart in one action  
**So that** I don't search for each SKU manually

**Acceptance Criteria:**

- [ ] One-click "Thêm vào giỏ" adds all in-stock SKUs from approved build
- [ ] Out-of-stock items skipped with user confirmation dialog listing omissions
- [ ] Cart payload uses Phong Vũ/Teko commerce identifiers
- [ ] User sees confirmation with item count and cart subtotal

### US-8.2 Assembly & Service Bundling

**As a** customer  
**I want to** add assembly service and Windows license  
**So that** my build is turnkey

**Acceptance Criteria:**

- [ ] Optional toggles: lắp ráp tại showroom, cài Windows, dịch vụ dọn dẹp cable
- [ ] Services priced and added as separate line items
- [ ] Services only offered where Phong Vũ policy allows (region, SKU type)
- [ ] Explanation of warranty implications for assembly service

### US-8.3 Promo & Bundle Optimization

**As a** customer  
**I want to** the build to use active combos and discounts  
**So that** I get the best deal Phong Vũ offers

**Acceptance Criteria:**

- [ ] Commerce agent evaluates bundle rules (PC + monitor, peripheral combos, seasonal promos)
- [ ] Suggests SKU swaps that unlock promos when performance impact is within tolerance
- [ ] Shows savings amount per applied promo
- [ ] Never applies promos that require unrelated purchases without user opt-in

### US-8.4 Save & Retrieve Builds

**As a** registered customer  
**I want to** save builds to my account  
**So that** I can purchase later

**Acceptance Criteria:**

- [ ] Saved builds list with name, date, total, use case tag
- [ ] Saved build re-validates against current catalog on load; flags price/stock changes
- [ ] User can duplicate and edit saved builds
- [ ] Max saved builds per user configurable (default 20)

### US-8.5 Quote Export for Business Buyers

**As a** business customer  
**I want to** export a formal quote  
**So that** I can submit for procurement approval

**Acceptance Criteria:**

- [ ] PDF quote with SKU, qty, unit price, total, VAT note, validity period
- [ ] Company header fields when user provides tax ID and company name
- [ ] Quote references Phong Vũ business sales channel when applicable
- [ ] Quote watermark with generation date and catalog version

---

## Phase 9 — Staff Copilot & Showroom Operations

Equip Phong Vũ consultants with the same intelligence in a staff-optimized interface.

### US-9.1 Staff Console

**As a** showroom staff member  
**I want to** a fast staff-facing console  
**So that** I can serve customers on the floor efficiently

**Acceptance Criteria:**

- [ ] Staff login with role-based access (`staff`, `lead`, `admin`)
- [ ] Console supports dual-pane: conversation + live build table
- [ ] Keyboard shortcuts for slot swap, apply promo, print quote
- [ ] Session tagged with `staff_id` and optional `showroom_id`

### US-9.2 Customer-Assist Mode

**As a** staff member  
**I want to** co-browse with a customer  
**So that** we can decide together in real time

**Acceptance Criteria:**

- [ ] Staff can share session to customer device via QR or short code
- [ ] Either party can suggest changes; staff can lock fields to prevent accidental swaps
- [ ] Staff-only notes field not visible to customer
- [ ] Session records who initiated each change

### US-9.3 Objection Handling Cards

**As a** staff member  
**I want to** quick answers for common objections  
**So that** I respond consistently

**Acceptance Criteria:**

- [ ] Cards for: "AMD hay Intel?", "Có cần RTX không?", "PSU bao nhiêu W là đủ?", "DDR5 có cần không?"
- [ ] Cards contextualized to current build data
- [ ] Admin can edit card library

### US-9.4 Showroom Handoff from Online

**As a** online customer  
**I want to** bring my online build to a showroom  
**So that** staff can finalize purchase in person

**Acceptance Criteria:**

- [ ] QR on build summary encodes session reference
- [ ] Staff scan loads build with latest catalog revalidation
- [ ] Shows delta since online generation (price changes, stock changes)
- [ ] Customer identity linked when logged in

### US-9.5 Lead Capture

**As a** sales manager  
**I want to** capture leads from copilot sessions that didn't convert  
**So that** follow-up is possible

**Acceptance Criteria:**

- [ ] Optional phone/Zalo opt-in for follow-up (consent required)
- [ ] Abandoned session defined by inactivity threshold with build generated but no cart action
- [ ] Lead export to CRM webhook when integrated
- [ ] PII handling complies with consent and retention policy (Section 12)

---

## Phase 10 — Administration, Rules & Content Management

Internal tools to keep the copilot accurate and on-brand.

### US-10.1 Compatibility Rules Management

**As an** admin  
**I want to** manage compatibility rules without code deploys  
**So that** new chipsets and products are supported quickly

**Acceptance Criteria:**

- [ ] Rule types editable: socket map, chipset CPU support, PSU formulas, case clearance, port limits
- [ ] Rules versioned with effective date
- [ ] Dry-run test against sample builds before publish
- [ ] Rollback to prior rules version

### US-10.2 Use Case & Optimizer Weight Configuration

**As a** merchandising admin  
**I want to** tune budget allocation weights per use case  
**So that** recommendations match commercial strategy

**Acceptance Criteria:**

- [ ] Weights editable per use case and per price band
- [ ] Preview impact on 5 canonical sample intents before publish
- [ ] Audit log of weight changes with author and timestamp

### US-10.3 Benchmark & Performance Table Management

**As a** admin  
**I want to** update game and app performance lookup tables  
**So that** FPS and workload estimates stay current

**Acceptance Criteria:**

- [ ] CRUD for benchmark entries: game/app, GPU tier, resolution, quality, FPS range
- [ ] Import CSV with validation
- [ ] Stale entries flagged after configurable age

### US-10.4 Glossary & Explanation Templates

**As a** content admin  
**I want to** edit glossary and explanation templates  
**So that** language stays consistent and on-brand

**Acceptance Criteria:**

- [ ] Glossary terms editable with approval workflow
- [ ] Templates support variables: `{gpu_name}`, `{fps_estimate}`, `{budget_remaining}`
- [ ] Vietnamese tone guidelines documented and enforced in review

### US-10.5 Feature Flags & Channel Controls

**As a** platform admin  
**I want to** enable features per channel  
**So that** rollout is controlled

**Acceptance Criteria:**

- [ ] Flags for: upgrade planner, cart handoff, staff console, AI/LLM profile, showroom stock
- [ ] Per-channel overrides: web, staff, api
- [ ] Kill switch for copilot without taking down main site

---

## Phase 11 — Observability, Quality & Governance

Ensure the system is measurable, debuggable, and safe in production.

### US-11.1 Agent Trace & Session Replay

**As a** engineer  
**I want to** replay agent decisions for a session  
**So that** I can debug wrong recommendations

**Acceptance Criteria:**

- [ ] Full trace: agent name, input, tool calls, output, latency, model version
- [ ] Trace linked to `build_session_id` and `build_vN`
- [ ] PII redaction in traces per policy
- [ ] Export trace for support tickets

### US-11.2 Quality Evaluation Suite

**As a** product owner  
**I want to** regression-test canonical build scenarios  
**So that** changes don't break core flows

**Acceptance Criteria:**

- [ ] Test suite includes ≥30 canonical intents across personas and budgets
- [ ] Automated checks: compatibility pass, budget compliance, required slots filled, no hallucinated SKUs
- [ ] Human review rubric score for explanation quality (clarity, grounding, tone)
- [ ] CI gate blocks release on critical regression failures

### US-11.3 User Feedback Loop

**As a** customer  
**I want to** rate the build and leave feedback  
**So that** the service improves

**Acceptance Criteria:**

- [ ] Thumbs up/down on overall build and per-part relevance
- [ ] Optional free-text feedback
- [ ] Feedback tied to session, build version, catalog version
- [ ] Low ratings surfaced in admin review queue

### US-11.4 Safety & Policy Enforcement

**As a** compliance owner  
**I want to** block unsafe or out-of-scope requests  
**So that** the copilot stays within retail advisory bounds

**Acceptance Criteria:**

- [ ] Blocks instructions for illegal modifications, piracy, crypto mining farm abuse guidance when policy forbids
- [ ] Refuses medical, legal, unrelated topics with branded fallback message
- [ ] Does not disparage competitors; compares on specs neutrally when asked
- [ ] Warranty disclaimers shown where performance estimates are shown

### US-11.5 Analytics & Business Metrics

**As a** Phong Vũ stakeholder  
**I want to** a metrics dashboard  
**So that** I can measure business impact

**Acceptance Criteria:**

- [ ] Metrics: sessions started, builds generated, approval rate, cart adds, conversion, AOV, upgrade vs new build ratio
- [ ] Funnel: intent → build → cart → purchase (purchase when integrated)
- [ ] Breakdown by use case, budget band, channel, showroom
- [ ] Export CSV for BI tools

---

## Phase 12 — API & Embeddable Integration

Expose copilot capabilities to Phong Vũ digital ecosystem.

### US-12.1 Public Build API

**As a** Phong Vũ engineer  
**I want to** a documented API  
**So that** other surfaces can consume build generation

**Acceptance Criteria:**

- [ ] Endpoints: create session, submit intent, generate build, validate build, get alternatives, export cart payload
- [ ] Auth via API key and OAuth for staff apps
- [ ] Rate limits per key documented
- [ ] OpenAPI spec published and versioned

### US-12.2 Web Embed Widget

**As a** product manager  
**I want to** embed the copilot on category pages  
**So that** users get advice in context

**Acceptance Criteria:**

- [ ] JS embed with configurable entry context (gaming, creator, office)
- [ ] Passes category context into intent defaults
- [ ] Responsive layout for mobile and desktop
- [ ] Theming matches Phong Vũ design tokens

### US-12.3 Webhook Events

**As an** integration engineer  
**I want to** webhooks for key events  
**So that** CRM and analytics systems react in real time

**Acceptance Criteria:**

- [ ] Events: `build.generated`, `build.approved`, `cart.added`, `session.abandoned`, `lead.captured`
- [ ] Signed payloads with retry policy
- [ ] Subscriber management in admin console

---

## 6. Agent Definitions & Responsibilities

| Agent | Responsibility | Tools |
|-------|----------------|-------|
| **Intent Agent** | Parse NL → `BuildIntent`, manage clarifications | intent schema validator, preset loader |
| **Catalog Agent** | Retrieve SKU candidates per slot | catalog search, filter API, semantic retrieval |
| **Compatibility Agent** | Run deterministic rules, produce report | rules engine, spec comparator |
| **Performance Agent** | FPS estimates, bottleneck analysis | benchmark tables, balance scorer |
| **Commerce Agent** | Promos, bundles, stock, cart payload | promo engine, inventory service, cart API |
| **Optimizer Agent** | Assemble and refine builds within budget | optimizer solver, diff generator |
| **Explainer Agent** | Vietnamese rationales and trade-offs | template engine, glossary, grounded LLM |
| **Validator Agent** | Final gate: blocks, warnings, approval status | aggregates all reports |

### Orchestration Rules

1. Optimizer may not run until `BuildIntent` reaches `confirmed` state.
2. Explainer runs only after compatibility blocks are resolved.
3. Validator is the only agent that can set `build_status = approved`.
4. Any catalog or rules version change triggers revalidation on save/load.

---

## 7. Build Session State Machine

```
created → intent_draft → intent_confirmed → generating → generated
    → reviewing → approved → cart_ready → completed
                      ↘ rejected (with remediation)
```

| State | Description |
|-------|-------------|
| `created` | Session initialized |
| `intent_draft` | Partial intent, clarifications in progress |
| `intent_confirmed` | User confirmed summary |
| `generating` | Optimizer running |
| `generated` | Build produced, pending user review |
| `reviewing` | User editing slots or requesting iteration |
| `approved` | Passes validation, explanations attached |
| `cart_ready` | Cart payload generated |
| `completed` | Cart added or quote exported |
| `rejected` | Hard compatibility failure without resolution |

---

## 8. Data Model (Catalog Spec Fields)

### 8.1 CPU

`socket`, `generation`, `cores`, `threads`, `base_clock_ghz`, `boost_clock_ghz`, `tdp_w`, `igpu`, `cooler_included`, `pcie_version`

### 8.2 Mainboard

`socket`, `chipset`, `form_factor`, `memory_type[]`, `max_memory_gb`, `dimms`, `m2_slots`, `sata_ports`, `pcie_slots`, `max_gpu_length_mm` (if applicable), `supported_cpu_generations[]`

### 8.3 RAM

`type` (DDR4/DDR5), `capacity_gb`, `modules`, `speed_mt_s`, `ecc`

### 8.4 GPU

`chipset`, `vram_gb`, `length_mm`, `tdp_w`, `power_connectors[]`, `slot_width`

### 8.5 PSU

`wattage_w`, `efficiency_rating`, `connectors[]`, `form_factor`

### 8.6 Case

`supported_form_factors[]`, `max_gpu_length_mm`, `max_cooler_height_mm`, `radiator_support[]`

### 8.7 Cooler

`type` (air/aio), `sockets[]`, `height_mm`, `radiator_mm`, `tdp_rating_w`

### 8.8 Storage

`type` (NVMe/SATA/HDD), `capacity_gb`, `interface`, `pcie_gen`

### 8.9 Monitor

`size_inch`, `resolution`, `refresh_hz`, `panel_type`, `response_time_ms`

---

## 9. Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| `COMPAT_SOCKET_MISMATCH` | Block | CPU socket ≠ mainboard socket |
| `COMPAT_BIOS_RISK` | Warning | CPU may need BIOS update |
| `COMPAT_RAM_TYPE` | Block | DDR type unsupported |
| `COMPAT_RAM_CAPACITY` | Block | RAM exceeds board max |
| `COMPAT_GPU_LENGTH` | Block | GPU too long for case |
| `COMPAT_PSU_WATTAGE` | Block | PSU underpowered |
| `COMPAT_PSU_CONNECTOR` | Block | Missing GPU power connector |
| `COMPAT_COOLER_SOCKET` | Block | Cooler doesn't support socket |
| `COMPAT_COOLER_HEIGHT` | Block | Cooler too tall for case |
| `COMPAT_M2_SLOTS` | Block | Too many M.2 drives |
| `PERF_BELOW_TARGET` | Warning | FPS below user target |
| `PERF_IMBALANCE` | Warning | CPU/GPU severely mismatched |
| `PERF_MONITOR_OVERSPEC` | Warning | Monitor exceeds PC capability |
| `COMM_OUT_OF_STOCK` | Warning | SKU unavailable |
| `COMM_OVER_BUDGET` | Warning | Cannot meet budget constraint |
| `DATA_MISSING_SPEC` | Warning | Catalog spec incomplete |

---

## 10. Non-Functional Requirements

### 10.1 Performance

| Requirement | Target |
|-------------|--------|
| Intent parsing response | < 3s p95 |
| Full build generation | < 15s p95 |
| Slot swap revalidation | < 5s p95 |
| Catalog search | < 500ms p95 |
| Concurrent sessions | Horizontally scalable |

### 10.2 Availability & Reliability

- Service availability target: 99.5% monthly (production)
- Graceful degradation: if LLM unavailable, rules-based build still works with template explanations
- Idempotent cart payload generation

### 10.3 Security & Privacy

- TLS everywhere; secrets in vault
- Staff RBAC; least privilege
- PII encrypted at rest; retention policy configurable
- Consent required for phone/Zalo follow-up
- No storage of payment credentials

### 10.4 Localization

- Primary UI and explanations: Vietnamese
- Currency: VND with `.` thousands separator
- Number parsing accepts Vietnamese input ("25 triệu", "25tr", "25.000.000")

### 10.5 Accessibility

- WCAG 2.1 AA for web UI
- Keyboard navigation for staff console
- Screen reader labels on part tables and warnings

### 10.6 Maintainability

- OpenAPI for public endpoints
- Rules and catalog versioned
- Feature flags for progressive rollout
- Structured JSON logging with correlation IDs

---

## 11. Canonical Test Scenarios (Regression Suite)

| ID | Persona | Input Summary | Expected Outcome |
|----|---------|---------------|------------------|
| T-01 | First-time | Gaming 20M, LMHT + Valorant 1080p | Valid build, GPU-weighted, under budget |
| T-02 | Parent | Office + study, 12M, quiet | iGPU or entry GPU, SSD 512GB+, approved |
| T-03 | Creator | Premiere + After Effects, 35M | ≥32GB RAM, strong GPU VRAM, NVMe |
| T-04 | Enthusiast | 30M, Cyberpunk 1440p High | Flags if FPS target missed at 1440p |
| T-05 | Upgrader | i5-12400F + B660 + 3060, GPU budget 10M | Compatible GPU options, PSU check |
| T-06 | Edge | Budget 8M gaming | Honest over-budget notice with closest config |
| T-07 | Edge | Request incompatible CPU+board swap | Hard block with remediation |
| T-08 | Staff | Same as T-01 via staff console | QR share works, cart payload valid |
| T-09 | Commerce | Build with active combo promo | Promo applied, savings shown |
| T-10 | AI use case | Local LLM 13B, 40M | VRAM guidance, RAM ≥32GB |

---

## 12. Open Integration Assumptions

| Integration | Assumption |
|-------------|------------|
| Phong Vũ Catalog | Teko commerce product API or approved scraper pipeline |
| Cart | Teko cart API with SKU IDs |
| Inventory | Stock per SKU and optional per-showroom feed |
| Promotions | Rules engine fed by merchandising promo feed |
| Auth | Phong Vũ customer account OAuth for save/load |
| CRM | Webhook to Zalo OA or internal CRM for leads |

---

## 13. Glossary

| Term | Definition |
|------|------------|
| **Agentic** | System plans, calls tools, iterates, and validates — not single-shot chat |
| **Build Artifact** | Immutable snapshot of a generated configuration and metadata |
| **Slot** | Component category in a PC build |
| **SKU** | Sellable Phong Vũ product unit |
| **Grounded** | Output tied to catalog fields and rules, not invented |
| **Approved Build** | Passed all block-level compatibility checks and has explanations |

---

## 14. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-26 | — | Initial complete specification |

---

*PC Build Copilot — Phong Vũ Retail Track — Agentic AI Build Week 2026*