import { useMemo } from "react";
import { Trash2, Utensils, Sparkles, ChefHat, Flame } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch, refreshAll } from "@/lib/useFetch";
import { Card, StatCard, SectionHeading, EmptyState, ConfidenceBadge } from "@/components/common";
import { Button } from "@/components/ui/button";
import { openAI } from "@/components/AppShell";
import { toast } from "sonner";

const TARGETS = { cal: 2700, p: 160, c: 300, f: 90 };

export default function Nutrition() {
  const today = new Date().toISOString().slice(0, 10);
  const { data: meals, loading } = useFetch(`/meals?date=${today}`);
  const { data: recipes } = useFetch("/recipes");
  const del = async (id) => { await api.delete(`/meals/${id}`); refreshAll(); };
  const cook = async (r) => {
    try {
      const { data } = await api.post(`/recipes/${r.id}/cook`);
      toast.success(`Cooked ${r.name}`, { description: data.inventory_changes?.join(", ") });
      refreshAll();
    } catch { toast.error("Could not cook recipe"); }
  };
  const tot = useMemo(() => {
    const arr = meals || [];
    return {
      cal: arr.reduce((s, x) => s + (x.calories || 0), 0),
      p: arr.reduce((s, x) => s + (x.protein || 0), 0),
      c: arr.reduce((s, x) => s + (x.carbs || 0), 0),
      f: arr.reduce((s, x) => s + (x.fat || 0), 0),
    };
  }, [meals]);

  return (
    <div className="space-y-6">
      <SectionHeading title="Nutrition" sub="Today's meals, calories and macros"
        action={<Button onClick={() => openAI("Log a meal: ")} variant="outline" className="h-9"><Sparkles className="h-4 w-4 mr-1 text-emerald-600" />Log with AI</Button>} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard testid="nutri-cal" label="Calories" value={`${Math.round(tot.cal)}`} hint={`/ ${TARGETS.cal}`} />
        <StatCard testid="nutri-protein" label="Protein" value={`${Math.round(tot.p)}g`} accent="text-indigo-500" hint={`/ ${TARGETS.p}g`} />
        <StatCard testid="nutri-carbs" label="Carbs" value={`${Math.round(tot.c)}g`} accent="text-amber-500" hint={`/ ${TARGETS.c}g`} />
        <StatCard testid="nutri-fat" label="Fat" value={`${Math.round(tot.f)}g`} accent="text-red-500" hint={`/ ${TARGETS.f}g`} />
      </div>
      {loading ? <div className="skeleton h-40 rounded-2xl" /> : arr.length === 0 ? (
        <Card><EmptyState icon={Utensils} title="No meals logged today" sub="Tell the assistant what you ate and it will estimate the nutrition." action={<Button onClick={() => openAI("I ate ")} className="bg-emerald-600 hover:bg-emerald-700 text-white"><Sparkles className="h-4 w-4 mr-1" />Log a meal</Button>} /></Card>
      ) : (
        <Card>
          <div className="divide-y divide-border">
            {arr.map((m) => (
              <div key={m.id} className="flex items-center gap-3 px-5 py-3 group">
                <div className="h-9 w-9 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 grid place-items-center shrink-0"><Utensils className="h-4 w-4 text-emerald-600" /></div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm">{m.description}</p>
                  <p className="text-xs text-slate-500">{Math.round(m.protein || 0)}P · {Math.round(m.carbs || 0)}C · {Math.round(m.fat || 0)}F</p>
                </div>
                <div className="text-right"><p className="stat-num font-semibold text-sm">{Math.round(m.calories || 0)} kcal</p><ConfidenceBadge type="estimated">Est.</ConfidenceBadge></div>
                <button onClick={() => del(m.id)} className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2"><ChefHat className="h-4 w-4 text-emerald-600" /><h3 className="font-semibold">Recipes</h3></div>
          <Button size="sm" variant="outline" onClick={() => openAI("Create a recipe: ")} data-testid="recipe-ai"><Sparkles className="h-4 w-4 mr-1 text-emerald-600" />New with AI</Button>
        </div>
        {!(recipes || []).length ? (
          <p className="text-sm text-slate-500">No recipes yet. Ask the assistant to create one, then tap Cook to log it and subtract its ingredients from your inventory.</p>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3">
            {recipes.map((r) => (
              <div key={r.id} data-testid={`recipe-${r.id}`} className="rounded-xl border border-border p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-sm">{r.name}</p>
                    <p className="text-xs text-slate-500">{r.servings} serving{r.servings > 1 ? "s" : ""} · {Math.round((r.calories || 0) / (r.servings || 1))} kcal each</p>
                  </div>
                  <Button size="sm" onClick={() => cook(r)} className="bg-emerald-600 hover:bg-emerald-700 text-white h-8" data-testid={`cook-${r.id}`}><Flame className="h-3.5 w-3.5 mr-1" />Cook</Button>
                </div>
                <p className="text-xs text-slate-500 mt-2">{(r.ingredients || []).map((i) => `${i.quantity}${i.unit} ${i.name}`).join(", ")}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
