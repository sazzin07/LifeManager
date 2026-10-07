import { useState } from "react";
import { Sun, Moon, Monitor, Sparkles, Plus, Trash2, LogOut } from "lucide-react";
import { api, eur } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useSettings } from "@/context/SettingsContext";
import { useFetch, refreshAll } from "@/lib/useFetch";
import { Card, SectionHeading, Label, Avatar } from "@/components/common";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export default function Settings() {
  const { user, logout } = useAuth();
  const { theme, setTheme, animations, setAnimations } = useSettings();
  const { data: cats } = useFetch("/categories");
  const { data: accounts } = useFetch("/accounts");
  const [newCat, setNewCat] = useState("");

  const addCat = async () => { if (!newCat.trim()) return; await api.post("/categories", { name: newCat }); setNewCat(""); refreshAll(); toast.success("Category added"); };
  const delCat = async (id) => { await api.delete(`/categories/${id}`); refreshAll(); };

  const themes = [{ k: "light", i: Sun, l: "Light" }, { k: "dark", i: Moon, l: "Dark" }, { k: "system", i: Monitor, l: "System" }];

  return (
    <div className="space-y-6 max-w-3xl">
      <SectionHeading title="Settings" sub="Appearance, categories and your account" />

      <Card className="p-5 flex items-center gap-4">
        <Avatar name={user?.name || "Sá"} size="h-12 w-12" />
        <div className="flex-1"><p className="font-semibold">{user?.name || "Sá"}</p><p className="text-sm text-slate-500">{user?.email}</p></div>
        <Button variant="outline" onClick={logout} data-testid="settings-logout"><LogOut className="h-4 w-4 mr-1" />Sign out</Button>
      </Card>

      <Card className="p-5">
        <Label>Appearance</Label>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {themes.map((t) => (
            <button key={t.k} data-testid={`theme-${t.k}`} onClick={() => setTheme(t.k)}
              className={cn("flex flex-col items-center gap-2 rounded-xl border p-4 transition-colors", theme === t.k ? "border-emerald-400 bg-emerald-50 dark:bg-emerald-500/15" : "border-border hover:bg-slate-50 dark:hover:bg-slate-800/50")}>
              <t.i className={cn("h-5 w-5", theme === t.k ? "text-emerald-600" : "text-slate-500")} />
              <span className="text-sm font-medium">{t.l}</span>
            </button>
          ))}
        </div>
        <div className="mt-5 flex items-center justify-between">
          <div><p className="font-medium text-sm">Animations</p><p className="text-xs text-slate-500">Entry and transition motion</p></div>
          <Switch checked={animations} onCheckedChange={setAnimations} data-testid="anim-toggle" />
        </div>
      </Card>

      <Card className="p-5">
        <Label>Accounts</Label>
        <div className="mt-3 space-y-2">
          {(accounts || []).map((a) => (
            <div key={a.id} className="flex items-center justify-between text-sm border-b border-border pb-2 last:border-0">
              <span className="font-medium">{a.name}</span><span className="stat-num font-semibold">{eur(a.balance)}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-5">
        <Label>Finance categories</Label>
        <div className="mt-3 flex gap-2">
          <Input placeholder="New category" value={newCat} onChange={(e) => setNewCat(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addCat()} data-testid="category-input" />
          <Button onClick={addCat} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="category-add"><Plus className="h-4 w-4" /></Button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {(cats || []).map((c) => (
            <span key={c.id} className="group inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-sm">
              <span className="h-2 w-2 rounded-full" style={{ background: c.color }} />{c.name}
              <button onClick={() => delCat(c.id)} className="text-slate-300 hover:text-red-500"><Trash2 className="h-3 w-3" /></button>
            </span>
          ))}
        </div>
      </Card>

      <Card className="p-5 flex items-center gap-3">
        <Sparkles className="h-5 w-5 text-emerald-600" />
        <div><p className="font-medium text-sm">AI assistant</p><p className="text-xs text-slate-500">Powered by Gemini · text, voice and receipt photos. Your key is stored securely on the server.</p></div>
      </Card>
    </div>
  );
}
