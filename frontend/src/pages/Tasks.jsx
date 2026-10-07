import { useState } from "react";
import { Plus, Trash2, CheckSquare } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch, refreshAll } from "@/lib/useFetch";
import { Card, SectionHeading, EmptyState } from "@/components/common";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

export default function Tasks() {
  const { data: tasks, loading } = useFetch("/tasks");
  const [title, setTitle] = useState("");

  const add = async () => { if (!title.trim()) return; await api.post("/tasks", { title, priority: "normal" }); setTitle(""); refreshAll(); };
  const toggle = async (t) => { await api.put(`/tasks/${t.id}`, { ...t, done: !t.done }); refreshAll(); };
  const del = async (id) => { await api.delete(`/tasks/${id}`); refreshAll(); };

  const open = (tasks || []).filter((t) => !t.done);
  const done = (tasks || []).filter((t) => t.done);

  return (
    <div className="space-y-6">
      <SectionHeading title="Tasks" sub="Your lightweight daily list" />
      <Card className="p-4">
        <div className="flex gap-2">
          <Input placeholder="Add a task…" value={title} onChange={(e) => setTitle(e.target.value)} onKeyDown={(e) => e.key === "Enter" && add()} data-testid="task-input" />
          <Button onClick={add} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="task-add"><Plus className="h-4 w-4" /></Button>
        </div>
      </Card>
      {loading ? <div className="skeleton h-40 rounded-2xl" /> : (
        <Card>
          {open.length === 0 && done.length === 0 ? <EmptyState icon={CheckSquare} title="No tasks yet" sub="Add your first task above." /> : (
            <div className="divide-y divide-border">
              {[...open, ...done].map((t) => (
                <div key={t.id} data-testid={`task-${t.id}`} className="flex items-center gap-3 px-5 py-3 group">
                  <Checkbox checked={t.done} onCheckedChange={() => toggle(t)} data-testid={`task-check-${t.id}`} />
                  <div className={cn("h-2 w-2 rounded-full", t.priority === "high" ? "bg-red-500" : t.priority === "low" ? "bg-slate-300" : "bg-emerald-500")} />
                  <span className={cn("flex-1 text-sm", t.done && "line-through text-slate-400")}>{t.title}</span>
                  {t.due && <span className="text-xs text-slate-400">{t.due}</span>}
                  <button onClick={() => del(t.id)} className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
