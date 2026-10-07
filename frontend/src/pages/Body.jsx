import { useState, useRef } from "react";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";
import { Plus, Trash2, Scale, Camera, GitCompare, X } from "lucide-react";
import { api, API } from "@/lib/api";
import { useFetch, refreshAll } from "@/lib/useFetch";
import { Card, StatCard, SectionHeading, EmptyState, Label } from "@/components/common";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const photoSrc = (p) => `${API}/photos/file/${p.storage_path}?auth=${localStorage.getItem("lm_token")}`;

export default function Body() {
  const { data: weight, loading } = useFetch("/weight");
  const { data: photos } = useFetch("/photos");
  const [w, setW] = useState("");
  const [compare, setCompare] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const add = async () => { if (!parseFloat(w)) return; await api.post("/weight", { weight: parseFloat(w) }); setW(""); toast.success("Weight recorded"); refreshAll(); };
  const del = async (id) => { await api.delete(`/weight/${id}`); refreshAll(); };
  const delPhoto = async (id) => { await api.delete(`/photos/${id}`); setCompare((c) => c.filter((x) => x !== id)); refreshAll(); };

  const upload = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", f);
    try { await api.post("/photos", fd); toast.success("Photo added"); refreshAll(); }
    catch { toast.error("Could not upload photo"); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const toggleCompare = (id) => setCompare((c) => c.includes(id) ? c.filter((x) => x !== id) : c.length >= 2 ? [c[1], id] : [...c, id]);

  const arr = weight || [];
  const last = arr.length ? arr[arr.length - 1] : null;
  const first = arr.length ? arr[0] : null;
  const delta = last && first ? (last.weight - first.weight).toFixed(1) : null;
  const pics = photos || [];
  const comparePics = compare.map((id) => pics.find((p) => p.id === id)).filter(Boolean);

  return (
    <div className="space-y-6">
      <SectionHeading title="Body" sub="Weekly weight check-ins, trend and progress photos" />
      <div className="grid grid-cols-2 gap-4">
        <StatCard testid="body-current" label="Current" value={last ? `${last.weight} kg` : "—"} icon={Scale} hint={last ? last.date : "No check-in"} />
        <StatCard testid="body-delta" label="Total change" value={delta ? `${delta > 0 ? "+" : ""}${delta} kg` : "—"} accent="text-emerald-600 dark:text-emerald-400" hint="Since first entry" />
      </div>
      <Card className="p-4">
        <div className="flex gap-2">
          <Input placeholder="Weight in kg" type="number" step="0.1" value={w} onChange={(e) => setW(e.target.value)} onKeyDown={(e) => e.key === "Enter" && add()} data-testid="body-weight-input" />
          <Button onClick={add} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="body-weight-add"><Plus className="h-4 w-4 mr-1" />Check in</Button>
        </div>
      </Card>

      {loading ? <div className="skeleton h-56 rounded-2xl" /> : arr.length === 0 ? (
        <Card><EmptyState icon={Scale} title="Your body log starts here" sub="Record your weight to see your trend over time." /></Card>
      ) : (
        <Card className="p-5">
          <Label>Weight trend</Label>
          <ResponsiveContainer width="100%" height={200} className="mt-3">
            <LineChart data={arr}>
              <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(d) => d.slice(5)} stroke="#94A3B8" />
              <YAxis domain={["dataMin - 1", "dataMax + 1"]} tick={{ fontSize: 10 }} stroke="#94A3B8" width={30} />
              <Tooltip formatter={(v) => `${v} kg`} contentStyle={{ borderRadius: 12, fontSize: 12 }} />
              <Line type="monotone" dataKey="weight" stroke="#10B981" strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Progress photos */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2"><Camera className="h-4 w-4 text-emerald-600" /><h3 className="font-semibold">Progress photos</h3><span className="text-xs text-slate-400">private</span></div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={upload} data-testid="photo-input" />
          <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} disabled={uploading} data-testid="photo-upload-btn"><Plus className="h-4 w-4 mr-1" />{uploading ? "Uploading…" : "Add photo"}</Button>
        </div>

        {comparePics.length === 2 && (
          <div className="mb-4 rounded-xl border border-emerald-200 dark:border-emerald-500/30 p-3" data-testid="compare-view">
            <div className="flex items-center gap-2 mb-2 text-sm font-medium text-emerald-700 dark:text-emerald-300"><GitCompare className="h-4 w-4" />Comparison</div>
            <div className="grid grid-cols-2 gap-3">
              {comparePics.map((p) => (
                <div key={p.id}>
                  <img src={photoSrc(p)} alt={p.date} className="rounded-lg w-full aspect-[3/4] object-cover" />
                  <p className="text-xs text-center text-slate-500 mt-1">{p.date}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {pics.length === 0 ? (
          <EmptyState icon={Camera} title="No progress photos yet" sub="Add a photo to start tracking your progress visually. Tap two photos to compare them." />
        ) : (
          <>
            <p className="text-xs text-slate-500 mb-3">Tap photos to compare (up to 2)</p>
            <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-3">
              {pics.map((p) => (
                <div key={p.id} data-testid={`photo-${p.id}`} className="relative group">
                  <button onClick={() => toggleCompare(p.id)} className={cn("block w-full rounded-lg overflow-hidden border-2 transition-colors", compare.includes(p.id) ? "border-emerald-500" : "border-transparent")}>
                    <img src={photoSrc(p)} alt={p.date} className="w-full aspect-[3/4] object-cover" />
                  </button>
                  <span className="absolute bottom-1 left-1 right-1 text-[10px] text-white bg-black/50 rounded px-1 text-center">{p.date}</span>
                  <button onClick={() => delPhoto(p.id)} className="absolute top-1 right-1 h-6 w-6 grid place-items-center rounded-full bg-black/50 text-white opacity-0 group-hover:opacity-100" data-testid={`photo-del-${p.id}`}><X className="h-3.5 w-3.5" /></button>
                </div>
              ))}
            </div>
          </>
        )}
      </Card>

      {arr.length > 0 && (
        <Card>
          <div className="divide-y divide-border">
            {[...arr].reverse().map((e) => (
              <div key={e.id} className="flex items-center gap-3 px-5 py-3 group">
                <span className="stat-num font-semibold">{e.weight} kg</span>
                <span className="text-sm text-slate-500 flex-1">{e.date}</span>
                <button onClick={() => del(e.id)} className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
