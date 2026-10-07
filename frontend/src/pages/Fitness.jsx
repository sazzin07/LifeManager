import { useState, useCallback, useEffect } from "react";
import { Dumbbell, Timer, Plus, Trash2, Trophy, Sparkles, Play } from "lucide-react";
import { api } from "@/lib/api";
import { refreshAll } from "@/lib/useFetch";
import { Card, SectionHeading, EmptyState, Label } from "@/components/common";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { openAI } from "@/components/AppShell";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const TEMPLATES = {
  Push: { color: "#10B981", exercises: [
    { name: "Dips", sets: 3, reps: 12, weight: 0 }, { name: "Pike push-ups", sets: 3, reps: 10, weight: 0 },
    { name: "Push-ups", sets: 3, reps: 15, weight: 0 }, { name: "Pseudo planche", sets: 3, reps: 8, weight: 0 },
    { name: "Planche lean", is_isometric: true, duration: 30 }] },
  Pull: { color: "#6366F1", exercises: [
    { name: "Pull-ups", sets: 3, reps: 8, weight: 0 }, { name: "Rows", sets: 3, reps: 10, weight: 20 },
    { name: "Chin-ups", sets: 3, reps: 8, weight: 0 }, { name: "Face pulls", sets: 3, reps: 15, weight: 10 },
    { name: "Dead hang", is_isometric: true, duration: 45 }] },
  Legs: { color: "#F59E0B", exercises: [
    { name: "Pistol squats", sets: 3, reps: 6, weight: 0 }, { name: "Nordic curls", sets: 3, reps: 6, weight: 0 },
    { name: "Calf raises", sets: 3, reps: 20, weight: 0 }, { name: "Lunges", sets: 3, reps: 12, weight: 0 },
    { name: "Wall sit", is_isometric: true, duration: 60 }] },
};

function LogDialog({ open, setOpen }) {
  const [type, setType] = useState("Push");
  const [exs, setExs] = useState([]);
  useEffect(() => { if (open) { setExs(TEMPLATES[type].exercises.map((e) => ({ ...e }))); } }, [open, type]);

  const setEx = (i, k, v) => setExs((a) => a.map((x, idx) => idx === i ? { ...x, [k]: v } : x));

  const save = async () => {
    const exercises = exs.map((e) => e.is_isometric
      ? { name: e.name, is_isometric: true, duration: parseInt(e.duration) || 0, sets: [] }
      : { name: e.name, is_isometric: false, sets: Array.from({ length: parseInt(e.sets) || 1 }).map(() => ({ reps: parseInt(e.reps) || 0, weight: parseFloat(e.weight) || 0 })) });
    try { await api.post("/workouts", { type, exercises }); toast.success(`${type} session logged`); refreshAll(); setOpen(false); }
    catch { toast.error("Could not save session"); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="workout-log-dialog">
        <DialogHeader><DialogTitle>Log workout</DialogTitle>
          <DialogDescription className="sr-only">Record a completed workout session</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Select value={type} onValueChange={setType}>
            <SelectTrigger data-testid="workout-type"><SelectValue /></SelectTrigger>
            <SelectContent>{Object.keys(TEMPLATES).map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
          </Select>
          <div className="space-y-2">
            {exs.map((e, i) => (
              <div key={i} className="rounded-xl border border-border p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Input value={e.name} onChange={(ev) => setEx(i, "name", ev.target.value)} className="h-8 font-medium" />
                  <button onClick={() => setExs((a) => a.filter((_, idx) => idx !== i))} className="text-slate-300 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
                </div>
                {e.is_isometric ? (
                  <div className="flex items-center gap-2 text-sm"><Timer className="h-4 w-4 text-emerald-600" /><Input type="number" value={e.duration} onChange={(ev) => setEx(i, "duration", ev.target.value)} className="h-8 w-24" /> seconds</div>
                ) : (
                  <div className="grid grid-cols-3 gap-2">
                    <div><Label>Sets</Label><Input type="number" value={e.sets} onChange={(ev) => setEx(i, "sets", ev.target.value)} className="h-8 mt-1" /></div>
                    <div><Label>Reps</Label><Input type="number" value={e.reps} onChange={(ev) => setEx(i, "reps", ev.target.value)} className="h-8 mt-1" /></div>
                    <div><Label>Weight (kg)</Label><Input type="number" value={e.weight} onChange={(ev) => setEx(i, "weight", ev.target.value)} className="h-8 mt-1" /></div>
                  </div>
                )}
              </div>
            ))}
            <Button variant="outline" size="sm" className="w-full" onClick={() => setExs((a) => [...a, { name: "New exercise", sets: 3, reps: 10, weight: 0 }])}><Plus className="h-4 w-4 mr-1" />Add exercise</Button>
          </div>
          <Button onClick={save} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="workout-save">Save session</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function Fitness() {
  const [logOpen, setLogOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [prs, setPrs] = useState([]);

  const load = useCallback(async () => {
    const [h, p] = await Promise.all([api.get("/workouts"), api.get("/workouts/prs")]);
    setHistory(h.data); setPrs(p.data);
  }, []);
  useEffect(() => { load(); const fn = () => load(); window.addEventListener("lm:refresh", fn); return () => window.removeEventListener("lm:refresh", fn); }, [load]);

  const del = async (id) => { await api.delete(`/workouts/${id}`); refreshAll(); };

  return (
    <div className="space-y-6">
      <SectionHeading title="Fitness" sub="Calisthenics — log sessions and track personal bests"
        action={<div className="flex gap-2">
          <Button variant="outline" className="h-9" onClick={() => openAI("Log today's workout: ")}><Sparkles className="h-4 w-4 mr-1 text-emerald-600" />AI</Button>
          <Button className="h-9 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => setLogOpen(true)} data-testid="log-workout-btn"><Play className="h-4 w-4 mr-1" />Log session</Button>
        </div>} />

      <div className="grid lg:grid-cols-3 gap-4">
        {Object.entries(TEMPLATES).map(([name, t]) => (
          <Card key={name} className="p-5 lm-in">
            <div className="flex items-center gap-2 mb-3">
              <div className="h-8 w-8 rounded-xl grid place-items-center" style={{ background: t.color + "22" }}><Dumbbell className="h-4 w-4" style={{ color: t.color }} /></div>
              <h3 className="font-bold">{name}</h3>
            </div>
            <div className="space-y-1.5">
              {t.exercises.map((e) => (
                <div key={e.name} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 dark:text-slate-300">{e.name}</span>
                  <span className="stat-num text-xs text-slate-500">{e.is_isometric ? `${e.duration}s` : `${e.sets}×${e.reps}`}</span>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {prs.length > 0 && (
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3"><Trophy className="h-4 w-4 text-amber-500" /><h3 className="font-semibold">Personal bests</h3></div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {prs.map((p) => (
              <div key={p.name} className="rounded-xl bg-slate-50 dark:bg-slate-800/50 p-3">
                <p className="font-medium text-sm">{p.name}</p>
                <p className="stat-num text-lg font-bold text-emerald-600 dark:text-emerald-400">
                  {p.is_isometric ? `${p.best_duration}s` : `${p.best_reps} reps${p.best_weight ? ` @ ${p.best_weight}kg` : ""}`}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <div className="p-5 pb-3"><h3 className="font-semibold">Session history</h3></div>
        {history.length === 0 ? (
          <EmptyState icon={Dumbbell} title="Your training history starts here" sub="Log your first session to build up your personal-best records."
            action={<Button onClick={() => setLogOpen(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white"><Play className="h-4 w-4 mr-1" />Log session</Button>} />
        ) : (
          <div className="divide-y divide-border">
            {history.map((w) => (
              <div key={w.id} data-testid={`workout-${w.id}`} className="px-5 py-3 group">
                <div className="flex items-center gap-3">
                  <span className={cn("text-xs font-bold px-2 py-0.5 rounded-full")} style={{ background: (TEMPLATES[w.type]?.color || "#94A3B8") + "22", color: TEMPLATES[w.type]?.color || "#64748B" }}>{w.type}</span>
                  <span className="text-sm text-slate-500 flex-1">{w.date}</span>
                  <button onClick={() => del(w.id)} className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
                </div>
                <p className="text-xs text-slate-500 mt-1.5">
                  {w.exercises.map((e) => e.is_isometric ? `${e.name} ${e.duration}s` : `${e.name} ${e.sets.length}×${e.sets[0]?.reps || 0}${e.sets[0]?.weight ? `@${e.sets[0].weight}kg` : ""}`).join(" · ")}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>

      <LogDialog open={logOpen} setOpen={setLogOpen} />
    </div>
  );
}
