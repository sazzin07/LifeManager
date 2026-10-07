import { cn } from "@/lib/utils";

const CONF = {
  exact: { bg: "bg-emerald-50 dark:bg-emerald-500/10", text: "text-emerald-700 dark:text-emerald-300", border: "border-emerald-200 dark:border-emerald-500/30", label: "Exact" },
  estimated: { bg: "bg-amber-50 dark:bg-amber-500/10", text: "text-amber-700 dark:text-amber-300", border: "border-amber-200 dark:border-amber-500/30", label: "Estimated" },
  historical: { bg: "bg-indigo-50 dark:bg-indigo-500/10", text: "text-indigo-700 dark:text-indigo-300", border: "border-indigo-200 dark:border-indigo-500/30", label: "Historical" },
  unknown: { bg: "bg-slate-100 dark:bg-slate-800", text: "text-slate-600 dark:text-slate-300", border: "border-slate-200 dark:border-slate-700", label: "Unknown" },
};

export function ConfidenceBadge({ type = "exact", children }) {
  const c = CONF[type] || CONF.unknown;
  return (
    <span data-testid={`confidence-${type}`} className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold", c.bg, c.text, c.border)}>
      {children || c.label}
    </span>
  );
}

export function SectionHeading({ title, sub, action }) {
  return (
    <div className="flex items-end justify-between gap-4 mb-4">
      <div>
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50">{title}</h2>
        {sub && <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

export function Label({ children }) {
  return <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{children}</span>;
}

export function Card({ className, children, ...props }) {
  return (
    <div className={cn("rounded-2xl border border-border bg-card card-ambient", className)} {...props}>
      {children}
    </div>
  );
}

export function StatCard({ label, value, hint, icon: Icon, accent = "text-slate-900 dark:text-slate-50", testid, className }) {
  return (
    <Card className={cn("p-5 lm-in", className)} data-testid={testid}>
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        {Icon && <Icon className="h-4 w-4 text-slate-400" />}
      </div>
      <div className={cn("mt-2 stat-num text-2xl sm:text-3xl font-extrabold tracking-tight", accent)}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</div>}
    </Card>
  );
}

export function EmptyState({ icon: Icon, title, sub, action }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-14 px-6">
      {Icon && <div className="mb-4 rounded-2xl bg-slate-100 dark:bg-slate-800 p-4"><Icon className="h-7 w-7 text-slate-400" /></div>}
      <p className="font-semibold text-slate-900 dark:text-slate-100">{title}</p>
      {sub && <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-sm">{sub}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function SkeletonCard({ className }) {
  return (
    <Card className={cn("p-5", className)}>
      <div className="skeleton h-3 w-24" />
      <div className="skeleton h-8 w-32 mt-3" />
      <div className="skeleton h-3 w-20 mt-3" />
    </Card>
  );
}

export function Avatar({ name, photo, size = "h-9 w-9" }) {
  const initials = (name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  return photo ? (
    <img src={photo} alt={name} className={cn("rounded-full object-cover", size)} />
  ) : (
    <div className={cn("rounded-full grid place-items-center bg-gradient-to-br from-emerald-500 to-teal-600 text-white font-semibold text-xs", size)}>
      {initials}
    </div>
  );
}
