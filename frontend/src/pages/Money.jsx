import { useEffect, useMemo, useState, useCallback } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, AreaChart, Area, XAxis } from "recharts";
import { Plus, Trash2, ArrowLeftRight, Wallet, CreditCard, Pencil } from "lucide-react";
import { api, eur, CATEGORY_COLORS } from "@/lib/api";
import { refreshAll } from "@/lib/useFetch";
import { Card, StatCard, SectionHeading, EmptyState, Label, SkeletonCard, ConfidenceBadge } from "@/components/common";
import { ExpenseDialog } from "@/components/ExpenseDialog";
import { EditExpenseDialog } from "@/components/EditExpenseDialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const REFUND_BADGE = {
  pending: { type: "unknown", label: "Pending" },
  partial: { type: "estimated", label: "Partly refunded" },
  settled: { type: "exact", label: "Settled" },
};

function periodParams(period) {
  const now = new Date();
  const iso = (d) => d.toISOString().slice(0, 10);
  if (period === "day") return { start: iso(now), end: iso(now) };
  if (period === "week") { const s = new Date(now); s.setDate(s.getDate() - 6); return { start: iso(s), end: iso(now) }; }
  if (period === "all") return {};
  return { month: period }; // yyyy-mm
}

export default function Money() {
  const now = new Date();
  const curYM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const MONTHS = [
    { key: "2026-09", label: "September 2026" },
    { key: "2026-10", label: "October 2026" },
    { key: "2026-11", label: "November 2026" },
  ];
  const PERIODS = [{ id: "day", label: "Day" }, { id: "week", label: "Week" }, { id: "all", label: "All Time" }];

  const [period, setPeriod] = useState("week");
  const [pm, setPm] = useState("all"); // all | card | cash
  const [sum, setSum] = useState(null);
  const [txns, setTxns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expenseOpen, setExpenseOpen] = useState(false);
  const [editTxn, setEditTxn] = useState(null);

  const load = useCallback(async () => {
    const p = periodParams(period);
    const qs = new URLSearchParams(p).toString();
    const tqs = new URLSearchParams({ ...p, ...(pm !== "all" ? { payment_method: pm } : {}) }).toString();
    try {
      const [s, t] = await Promise.all([
        api.get(`/analytics/summary${qs ? `?${qs}` : ""}`),
        api.get(`/transactions${tqs ? `?${tqs}` : ""}`),
      ]);
      setSum(s.data);
      setTxns(t.data);
    } finally { setLoading(false); }
  }, [period, pm]);

  useEffect(() => {
    setLoading(true);
    load();
    const h = () => load();
    window.addEventListener("lm:refresh", h);
    return () => window.removeEventListener("lm:refresh", h);
  }, [load]);

  const del = async (id) => { await api.delete(`/transactions/${id}`); toast.success("Deleted"); refreshAll(); };
  const expenses = useMemo(() => txns.filter((t) => t.type === "expense"), [txns]);

  return (
    <div className="space-y-6">
      <SectionHeading title="Money" sub="Cash, card, shared expenses and refunds"
        action={<Button data-testid="add-expense-btn" onClick={() => setExpenseOpen(true)} className="h-9 bg-emerald-600 hover:bg-emerald-700 text-white"><Plus className="h-4 w-4 mr-1" />Add expense</Button>} />

      {/* Period filter */}
      <div className="flex flex-wrap gap-2">
        {PERIODS.map((p) => (
          <button key={p.id} data-testid={`period-${p.id}`} onClick={() => setPeriod(p.id)}
            className={cn("rounded-full px-4 h-9 text-sm font-medium border transition-colors",
              period === p.id ? "border-emerald-400 bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" : "border-border text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50")}>
            {p.label}
          </button>
        ))}
        {MONTHS.map((m) => {
          const enabled = m.key <= curYM;
          return (
            <button key={m.key} data-testid={`period-${m.key}`} disabled={!enabled} onClick={() => enabled && setPeriod(m.key)}
              title={enabled ? "" : "Available once this month is reached"}
              className={cn("rounded-full px-4 h-9 text-sm font-medium border transition-colors",
                !enabled ? "border-dashed border-border text-slate-300 dark:text-slate-600 cursor-not-allowed"
                  : period === m.key ? "border-emerald-400 bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
                    : "border-border text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50")}>
              {m.label}{!enabled && " · soon"}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}</div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatCard testid="money-cash" label="Cash balance" value={eur(sum?.cash)} icon={Wallet} hint="Wallet" />
            <StatCard testid="money-revolut" label="Card balance" value={eur(sum?.revolut)} accent="text-[#1964FF]" icon={CreditCard} hint="Revolut" />
            <StatCard testid="money-gross" label="Spent (period)" value={eur(sum?.gross)} hint={`Your share ${eur(sum?.personal)}`} />
            <StatCard testid="money-pending" label="Pending refunds" value={eur(sum?.pending)} accent="text-amber-600 dark:text-amber-400" hint={`Refunded ${eur(sum?.refunded)}`} />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard testid="money-card-spent" label="Card spending" value={eur(sum?.card_spent)} icon={CreditCard} />
            <StatCard testid="money-cash-spent" label="Cash spending" value={eur(sum?.cash_spent)} icon={Wallet} />
            <StatCard testid="money-personal" label="Actual personal" value={eur(sum?.personal)} accent="text-emerald-600 dark:text-emerald-400" />
            <StatCard testid="money-reimbursable" label="Owed by others" value={eur(sum?.reimbursable)} />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="p-5 lg:col-span-2">
              <Label>Spending over time</Label>
              {sum?.by_day?.length ? (
                <ResponsiveContainer width="100%" height={200} className="mt-3">
                  <AreaChart data={sum.by_day}>
                    <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#10B981" stopOpacity={0.35} /><stop offset="100%" stopColor="#10B981" stopOpacity={0} /></linearGradient></defs>
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(d) => d.slice(5)} stroke="#94A3B8" />
                    <Tooltip formatter={(v) => eur(v)} contentStyle={{ borderRadius: 12, fontSize: 12 }} />
                    <Area type="monotone" dataKey="value" stroke="#10B981" strokeWidth={2} fill="url(#g)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <p className="text-sm text-slate-500 mt-8 text-center">No spending in this period.</p>}
            </Card>
            <Card className="p-5">
              <Label>By category</Label>
              {sum?.by_category?.length ? (
                <ResponsiveContainer width="100%" height={200} className="mt-3">
                  <PieChart>
                    <Pie data={sum.by_category} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={2}>
                      {sum.by_category.map((e, i) => <Cell key={i} fill={CATEGORY_COLORS[e.name] || "#94A3B8"} />)}
                    </Pie>
                    <Tooltip formatter={(v) => eur(v)} contentStyle={{ borderRadius: 12, fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : <p className="text-sm text-slate-500 mt-8 text-center">No data.</p>}
            </Card>
          </div>

          <Card>
            <div className="p-5 pb-3 flex items-center justify-between gap-3">
              <h3 className="font-semibold">Transactions</h3>
              <div className="flex gap-1 rounded-lg bg-slate-100 dark:bg-slate-800 p-1">
                {["all", "card", "cash"].map((m) => (
                  <button key={m} data-testid={`pm-${m}`} onClick={() => setPm(m)}
                    className={cn("rounded-md px-3 py-1 text-xs font-medium capitalize transition-colors",
                      pm === m ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm" : "text-slate-500")}>
                    {m}
                  </button>
                ))}
              </div>
            </div>
            {expenses.length === 0 ? (
              <EmptyState icon={Wallet} title="No transactions here" sub="Add an expense or change the filters above."
                action={<Button onClick={() => setExpenseOpen(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white"><Plus className="h-4 w-4 mr-1" />Add expense</Button>} />
            ) : (
              <div className="divide-y divide-border">
                {expenses.map((t) => {
                  const badge = REFUND_BADGE[t.refund_status];
                  return (
                    <div key={t.id} data-testid={`txn-${t.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/40 group">
                      <div className="h-9 w-9 rounded-xl grid place-items-center shrink-0" style={{ background: (CATEGORY_COLORS[t.category] || "#94A3B8") + "22" }}>
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: CATEGORY_COLORS[t.category] || "#94A3B8" }} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-medium text-sm truncate">{t.merchant || t.description || t.category}</p>
                          <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1">
                            {t.payment_method === "cash" ? <Wallet className="h-3 w-3" /> : <CreditCard className="h-3 w-3" />}{t.payment_method}
                          </span>
                          {badge && t.reimbursable_amount > 0.005 && <ConfidenceBadge type={badge.type}>{badge.label}</ConfidenceBadge>}
                        </div>
                        <p className="text-xs text-slate-500">{t.date} · {t.category}{t.responsible?.length ? ` · with ${t.responsible.join(", ")}` : ""}</p>
                      </div>
                      <div className="text-right">
                        <p className="stat-num font-semibold text-sm">{eur(t.gross_amount)}</p>
                        {t.reimbursable_amount > 0.005 && <p className="text-xs text-amber-600 dark:text-amber-400">{eur(t.remaining_refund)} owed</p>}
                      </div>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button data-testid={`edit-txn-${t.id}`} onClick={() => setEditTxn(t)} className="text-slate-300 hover:text-emerald-600"><Pencil className="h-4 w-4" /></button>
                        <button data-testid={`del-txn-${t.id}`} onClick={() => del(t.id)} className="text-slate-300 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </>
      )}
      <ExpenseDialog open={expenseOpen} setOpen={setExpenseOpen} />
      <EditExpenseDialog txn={editTxn} open={!!editTxn} setOpen={(v) => !v && setEditTxn(null)} />
    </div>
  );
}
