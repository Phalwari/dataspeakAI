/**
 * DomainMappingWizard — 3-step guided domain setup drawer.
 * Step 1: Domain selection (grid of domain cards)
 * Step 2: Column mapping review with confidence badges
 * Step 3: Confirm & apply → generates the AI dashboard
 *
 * Calls existing backend endpoints (no backend files touched):
 *   GET  /api/analytics/domains
 *   POST /api/analytics/connections/{id}/suggest-mapping
 *   POST /api/analytics/connections/{id}/apply-mapping
 */
import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, ChevronRight, ChevronLeft, Loader2, Check, AlertTriangle, Sparkles } from "lucide-react";
import { API_BASE_URL } from "../../config/api";
import { toast } from "sonner";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../ui/select";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────
interface DomainInfo {
  id: string;
  name: string;
  description: string;
  emoji: string;
}

interface MappingRow {
  variable: string;
  label: string;
  suggested_column: string | null;
  confidence: number;
  all_columns: string[];
}

interface DomainMappingWizardProps {
  open: boolean;
  onClose: () => void;
  connectionId: string;
  onApplied: () => void;
}

// ─────────────────────────────────────────────
// Domain display config (augments backend data)
// ─────────────────────────────────────────────
const DOMAIN_STYLE: Record<string, { emoji: string; bg: string; border: string; description: string }> = {
  ecommerce: {
    emoji: "🛒",
    bg: "from-blue-500/10 to-blue-600/5",
    border: "border-blue-400/30",
    description: "Orders, revenue, customers, products",
  },
  saas: {
    emoji: "📊",
    bg: "from-violet-500/10 to-violet-600/5",
    border: "border-violet-400/30",
    description: "MRR, subscriptions, churn, users",
  },
  healthcare: {
    emoji: "🏥",
    bg: "from-emerald-500/10 to-emerald-600/5",
    border: "border-emerald-400/30",
    description: "Patients, encounters, appointments",
  },
  logistics: {
    emoji: "🚚",
    bg: "from-amber-500/10 to-amber-600/5",
    border: "border-amber-400/30",
    description: "Shipments, deliveries, routes",
  },
  finance: {
    emoji: "💰",
    bg: "from-yellow-500/10 to-yellow-600/5",
    border: "border-yellow-400/30",
    description: "Transactions, portfolio, accounts",
  },
  generic: {
    emoji: "⚙️",
    bg: "from-slate-500/10 to-slate-600/5",
    border: "border-slate-400/30",
    description: "Auto-detect from any schema",
  },
};

// ─────────────────────────────────────────────
// Confidence badge
// ─────────────────────────────────────────────
function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  if (pct >= 80) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-[10px] font-bold text-emerald-700">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
        {pct}% Auto
      </span>
    );
  }
  if (pct >= 50) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-[10px] font-bold text-amber-700">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block" />
        {pct}% Review
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-50 border border-rose-200 text-[10px] font-bold text-rose-700">
      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 inline-block" />
      {pct}% Manual
    </span>
  );
}

// ─────────────────────────────────────────────
// Step indicators
// ─────────────────────────────────────────────
function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-2">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`rounded-full transition-all duration-300 ${
            i + 1 === current
              ? "w-6 h-2.5 bg-indigo-500"
              : i + 1 < current
              ? "w-2.5 h-2.5 bg-indigo-400"
              : "w-2.5 h-2.5 bg-slate-700"
          }`}
        />
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────
export function DomainMappingWizard({
  open,
  onClose,
  connectionId,
  onApplied,
}: DomainMappingWizardProps) {
  const [step, setStep] = useState(1);
  const [direction, setDirection] = useState(1); // 1 = forward, -1 = backward

  // Step 1
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string>("");
  const [domainsLoading, setDomainsLoading] = useState(false);

  // Step 2
  const [mappings, setMappings] = useState<MappingRow[]>([]);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [suggestLoading, setSuggestLoading] = useState(false);

  // Step 3
  const [applyLoading, setApplyLoading] = useState(false);
  const [applySuccess, setApplySuccess] = useState(false);

  const getToken = () => localStorage.getItem("access_token");

  // Fetch available domains on open
  useEffect(() => {
    if (!open) return;
    // Reset state each open
    setStep(1);
    setSelectedDomain("");
    setMappings([]);
    setOverrides({});
    setApplySuccess(false);

    setDomainsLoading(true);
    fetch(`${API_BASE_URL}/api/analytics/domains`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((data) => {
        const list: DomainInfo[] = (data?.domains || Object.keys(data?.domain_templates || {})).map((d: any) => {
          const id = typeof d === "string" ? d : d.id;
          const style = DOMAIN_STYLE[id] || DOMAIN_STYLE.generic;
          return {
            id,
            name: typeof d === "object" ? d.name : id.charAt(0).toUpperCase() + id.slice(1).replace(/_/g, " "),
            description: style.description,
            emoji: style.emoji,
          };
        });
        setDomains(list.length > 0 ? list : Object.entries(DOMAIN_STYLE).map(([id, s]) => ({
          id,
          name: id.charAt(0).toUpperCase() + id.slice(1),
          description: s.description,
          emoji: s.emoji,
        })));
      })
      .catch(() => {
        // Fallback to static list
        setDomains(Object.entries(DOMAIN_STYLE).map(([id, s]) => ({
          id,
          name: id.charAt(0).toUpperCase() + id.slice(1),
          description: s.description,
          emoji: s.emoji,
        })));
      })
      .finally(() => setDomainsLoading(false));
  }, [open]);

  const handleNext = useCallback(async () => {
    if (step === 1) {
      // Fetch mapping suggestions
      setSuggestLoading(true);
      setDirection(1);
      try {
        const res = await fetch(
          `${API_BASE_URL}/api/analytics/connections/${connectionId}/suggest-mapping`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${getToken()}`,
            },
            body: JSON.stringify({ domain: selectedDomain }),
          }
        );
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          toast.error(err?.detail || "Could not load mapping suggestions");
          setSuggestLoading(false);
          return;
        }
        const data = await res.json();
        // Build mapping rows from response
        const rows: MappingRow[] = (data?.mappings || data?.suggested_mappings || []).map((m: any) => ({
          variable: m.variable || m.key,
          label: m.label || m.variable || m.key,
          suggested_column: m.suggested_column || m.column || null,
          confidence: m.confidence ?? 0,
          all_columns: m.all_columns || data?.available_columns || [],
        }));
        setMappings(rows);
        setStep(2);
      } catch {
        toast.error("Network error — could not reach server");
      } finally {
        setSuggestLoading(false);
      }
    } else if (step === 2) {
      setDirection(1);
      setStep(3);
    }
  }, [step, selectedDomain, connectionId]);

  const handleBack = () => {
    setDirection(-1);
    setStep((p) => p - 1);
  };

  const handleApply = async () => {
    setApplyLoading(true);
    try {
      // Build confirmed mapping from overrides + suggestions
      const confirmedMapping: Record<string, string> = {};
      for (const row of mappings) {
        const col = overrides[row.variable] ?? row.suggested_column;
        if (col) confirmedMapping[row.variable] = col;
      }

      const res = await fetch(
        `${API_BASE_URL}/api/analytics/connections/${connectionId}/apply-mapping`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ domain: selectedDomain, mapping: confirmedMapping }),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail || "Failed to apply domain mapping");
        return;
      }
      setApplySuccess(true);
      toast.success("Domain dashboard configured — loading your KPIs...");
      setTimeout(() => {
        onApplied();
        onClose();
      }, 1800);
    } catch {
      toast.error("Network error — could not apply mapping");
    } finally {
      setApplyLoading(false);
    }
  };

  const acceptHighConfidence = () => {
    const auto: Record<string, string> = {};
    for (const row of mappings) {
      if (row.confidence >= 0.8 && row.suggested_column) {
        auto[row.variable] = row.suggested_column;
      }
    }
    setOverrides((p) => ({ ...p, ...auto }));
  };

  const lowConfidenceCount = mappings.filter((m) => {
    const col = overrides[m.variable] ?? m.suggested_column;
    return !col || m.confidence < 0.5;
  }).length;

  if (!open) return null;

  const pageVariants = {
    enter: (dir: number) => ({ x: dir * 50, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: number) => ({ x: dir * -50, opacity: 0 }),
  };

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <motion.div
        initial={{ x: "100%", opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: "100%", opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed top-0 right-0 bottom-0 w-full max-w-lg z-50 flex flex-col shadow-2xl"
        style={{ background: "hsl(222, 47%, 6%)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-white/[0.08] shrink-0">
          <div>
            <h2 className="text-base font-bold text-white">Setup Your Domain Dashboard</h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Step {step} of 3 — {step === 1 ? "Choose Domain" : step === 2 ? "Review Mappings" : "Confirm & Apply"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <StepIndicator current={step} total={3} />
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] flex items-center justify-center transition-colors"
            >
              <X className="w-4 h-4 text-slate-300" />
            </button>
          </div>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait" custom={direction}>
            {/* ── STEP 1: Domain Selection ── */}
            {step === 1 && (
              <motion.div
                key="step1"
                custom={direction}
                variants={pageVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.25, ease: "easeInOut" }}
                className="px-6 py-6"
              >
                <h3 className="text-sm font-bold text-white mb-1">Select your business domain</h3>
                <p className="text-xs text-slate-400 mb-5">
                  We'll auto-generate KPI recipes from your confirmed schema columns.
                </p>

                {domainsLoading ? (
                  <div className="flex justify-center py-10">
                    <Loader2 className="w-7 h-7 animate-spin text-indigo-400" />
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    {domains.map((d) => {
                      const style = DOMAIN_STYLE[d.id] || DOMAIN_STYLE.generic;
                      const isSelected = selectedDomain === d.id;
                      return (
                        <motion.button
                          key={d.id}
                          onClick={() => setSelectedDomain(d.id)}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          className={`relative text-left rounded-xl p-4 border transition-all duration-150 bg-gradient-to-br ${style.bg} ${
                            isSelected
                              ? "border-indigo-400 ring-2 ring-indigo-500/50 shadow-lg shadow-indigo-500/20"
                              : `${style.border} hover:border-white/20`
                          }`}
                        >
                          {isSelected && (
                            <div className="absolute top-2.5 right-2.5 w-5 h-5 rounded-full bg-indigo-500 flex items-center justify-center">
                              <Check className="w-3 h-3 text-white" />
                            </div>
                          )}
                          <span className="text-2xl mb-2 block">{d.emoji}</span>
                          <p className="text-sm font-bold text-white mb-0.5">
                            {d.name.charAt(0).toUpperCase() + d.name.slice(1)}
                          </p>
                          <p className="text-[10px] text-slate-400 leading-relaxed">{d.description}</p>
                        </motion.button>
                      );
                    })}
                  </div>
                )}
              </motion.div>
            )}

            {/* ── STEP 2: Column Mapping ── */}
            {step === 2 && (
              <motion.div
                key="step2"
                custom={direction}
                variants={pageVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.25, ease: "easeInOut" }}
                className="px-6 py-6"
              >
                {suggestLoading ? (
                  <div className="flex flex-col items-center gap-3 py-14">
                    <Loader2 className="w-7 h-7 animate-spin text-indigo-400" />
                    <p className="text-sm text-slate-400">Analyzing your schema...</p>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-sm font-bold text-white mb-0.5">Review column mappings</h3>
                        <p className="text-[11px] text-slate-400">Adjust any mappings before applying</p>
                      </div>
                      <button
                        onClick={acceptHighConfidence}
                        className="text-[11px] font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition-colors"
                      >
                        <Check className="w-3 h-3" />
                        Accept High Confidence
                      </button>
                    </div>

                    {lowConfidenceCount > 0 && (
                      <div className="flex gap-2 rounded-xl bg-amber-500/10 border border-amber-500/20 px-3 py-2.5 mb-4">
                        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                        <p className="text-xs text-amber-300">
                          {lowConfidenceCount} mapping{lowConfidenceCount > 1 ? "s have" : " has"} low confidence — please review before applying.
                        </p>
                      </div>
                    )}

                    {/* Column headers */}
                    <div className="grid grid-cols-[1fr_1fr_auto] gap-3 px-1 pb-2 border-b border-white/[0.06]">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Variable</span>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Column</span>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Confidence</span>
                    </div>

                    <div className="divide-y divide-white/[0.04]">
                      {mappings.map((row) => {
                        const currentVal = overrides[row.variable] ?? row.suggested_column ?? "";
                        const allCols = row.all_columns.length > 0 ? row.all_columns : row.suggested_column ? [row.suggested_column] : [];
                        return (
                          <div key={row.variable} className="py-3 grid grid-cols-[1fr_1fr_auto] gap-3 items-center">
                            <div>
                              <p className="text-xs font-semibold text-white">{row.label}</p>
                              <p className="text-[10px] text-slate-500 font-mono">{row.variable}</p>
                            </div>
                            <div>
                              {allCols.length > 1 ? (
                                <Select
                                  value={currentVal}
                                  onValueChange={(v) => setOverrides((p) => ({ ...p, [row.variable]: v }))}
                                >
                                  <SelectTrigger className="bg-white/[0.06] border-white/[0.1] text-white text-xs h-8">
                                    <SelectValue placeholder="Select column" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {allCols.map((c) => (
                                      <SelectItem key={c} value={c}>
                                        {c}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              ) : (
                                <span className="text-xs font-mono text-slate-300 bg-white/[0.04] px-2 py-1 rounded-lg border border-white/[0.06] block truncate">
                                  {currentVal || "—"}
                                </span>
                              )}
                            </div>
                            <ConfidenceBadge confidence={row.confidence} />
                          </div>
                        );
                      })}
                    </div>

                    {mappings.length === 0 && (
                      <div className="flex flex-col items-center gap-2 py-10 text-center">
                        <AlertTriangle className="w-7 h-7 text-slate-600" />
                        <p className="text-sm text-slate-500">No mappings returned. Try a different domain.</p>
                      </div>
                    )}
                  </>
                )}
              </motion.div>
            )}

            {/* ── STEP 3: Confirm ── */}
            {step === 3 && (
              <motion.div
                key="step3"
                custom={direction}
                variants={pageVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.25, ease: "easeInOut" }}
                className="px-6 py-6"
              >
                {applySuccess ? (
                  <div className="flex flex-col items-center gap-4 py-14 text-center">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 300, damping: 20 }}
                      className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center"
                    >
                      <Check className="w-8 h-8 text-emerald-400" />
                    </motion.div>
                    <div>
                      <p className="text-base font-bold text-white">Dashboard Configured!</p>
                      <p className="text-sm text-slate-400 mt-1">Loading your AI-generated KPIs...</p>
                    </div>
                    <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                  </div>
                ) : (
                  <>
                    <h3 className="text-sm font-bold text-white mb-1">Review &amp; Apply</h3>
                    <p className="text-xs text-slate-400 mb-5">
                      Confirm your selection — this will generate KPI cards, charts, and filter recommendations.
                    </p>

                    <div className="rounded-2xl bg-white/[0.04] border border-white/[0.08] divide-y divide-white/[0.06] overflow-hidden mb-5">
                      <div className="px-4 py-3 flex items-center justify-between">
                        <span className="text-xs text-slate-400">Business Domain</span>
                        <span className="text-xs font-bold text-white capitalize">
                          {DOMAIN_STYLE[selectedDomain]?.emoji} {selectedDomain.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="px-4 py-3 flex items-center justify-between">
                        <span className="text-xs text-slate-400">Mapped Variables</span>
                        <span className="text-xs font-bold text-white">{mappings.length}</span>
                      </div>
                      <div className="px-4 py-3 flex items-center justify-between">
                        <span className="text-xs text-slate-400">High-Confidence Auto</span>
                        <span className="text-xs font-bold text-emerald-400">
                          {mappings.filter((m) => m.confidence >= 0.8).length} mappings
                        </span>
                      </div>
                      <div className="px-4 py-3 flex items-center justify-between">
                        <span className="text-xs text-slate-400">Database Connection</span>
                        <span className="text-xs font-mono text-white">#{connectionId}</span>
                      </div>
                    </div>

                    {lowConfidenceCount > 0 && (
                      <div className="flex gap-2 rounded-xl bg-amber-500/10 border border-amber-500/20 px-3 py-2.5 mb-4">
                        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                        <p className="text-xs text-amber-300">
                          {lowConfidenceCount} low-confidence mapping(s) will be applied as-is.
                        </p>
                      </div>
                    )}
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer buttons */}
        {!applySuccess && (
          <div className="px-6 py-5 border-t border-white/[0.08] flex items-center justify-between shrink-0 bg-black/20">
            <button
              onClick={step === 1 ? onClose : handleBack}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-white/[0.1] text-slate-300 hover:text-white hover:border-white/20 text-sm font-medium transition-all"
            >
              {step === 1 ? (
                <>Cancel</>
              ) : (
                <>
                  <ChevronLeft className="w-4 h-4" />
                  Back
                </>
              )}
            </button>

            {step < 3 ? (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleNext}
                disabled={step === 1 && !selectedDomain || suggestLoading}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold transition-all shadow-lg shadow-indigo-500/25 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {suggestLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    Next
                    <ChevronRight className="w-4 h-4" />
                  </>
                )}
              </motion.button>
            ) : (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleApply}
                disabled={applyLoading}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold transition-all shadow-lg shadow-indigo-500/25 disabled:opacity-40"
              >
                {applyLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Building Dashboard...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Apply &amp; Generate Dashboard
                  </>
                )}
              </motion.button>
            )}
          </div>
        )}
      </motion.div>
    </>
  );
}
