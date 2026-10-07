import { Calendar as CalIcon, Scale, CheckSquare } from "lucide-react";
import { useFetch } from "@/lib/useFetch";
import { Card, SectionHeading, EmptyState } from "@/components/common";

export default function CalendarPage() {
  const { data: tasks } = useFetch("/tasks");
  const withDue = (tasks || []).filter((t) => t.due).sort((a, b) => a.due.localeCompare(b.due));
  const grouped = withDue.reduce((acc, t) => { (acc[t.due] = acc[t.due] || []).push(t); return acc; }, {});

  return (
    <div className="space-y-6">
      <SectionHeading title="Calendar" sub="Reminders, due tasks and weekly check-ins" />
      <Card className="p-5 flex items-center gap-3 border-emerald-200 dark:border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-500/10">
        <Scale className="h-5 w-5 text-emerald-600 shrink-0" />
        <div><p className="font-medium text-sm">Weekly body check-in</p><p className="text-xs text-slate-500">Recurring every week — record your weight in the Body tab.</p></div>
      </Card>
      {Object.keys(grouped).length === 0 ? (
        <Card><EmptyState icon={CalIcon} title="Nothing scheduled" sub="Tasks with a due date will appear here as reminders." /></Card>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([date, items]) => (
            <Card key={date} className="p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">{new Date(date).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" })}</p>
              <div className="space-y-2">
                {items.map((t) => (
                  <div key={t.id} className="flex items-center gap-3 text-sm"><CheckSquare className="h-4 w-4 text-emerald-600" />{t.title}</div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
