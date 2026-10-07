import { useEffect, useState, useCallback } from "react";
import { Trash2, ShoppingCart, AlertTriangle, Plus, Minus, Pencil, Sparkles, Check, Store } from "lucide-react";
import { api, eur } from "@/lib/api";
import { refreshAll } from "@/lib/useFetch";
import { Card, SectionHeading, EmptyState, ConfidenceBadge, Label } from "@/components/common";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { openAI } from "@/components/AppShell";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const CATS = ["Meat", "Fish", "Eggs", "Dairy", "Carbohydrates", "Fruit", "Vegetables", "Frozen", "Pantry", "Snacks", "Drinks", "Other"];

function GroceryDialog({ item, open, setOpen }) {
  const [f, setF] = useState({});
  useEffect(() => {
    setF(item ? { ...item } : { name: "", quantity: 1, unit: "unit", category: "Other", price: "", store: "", low_threshold: 0, notes: "", expiration: "" });
  }, [item, open]);
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  const num = (v) => (v === "" || v == null ? null : parseFloat(v));

  const save = async () => {
    if (!f.name?.trim()) { toast.error("Name required"); return; }
    const body = { name: f.name, quantity: num(f.quantity) ?? 1, unit: f.unit || "unit", category: f.category || "Other",
      price: num(f.price), store: f.store || null, low_threshold: num(f.low_threshold) ?? 0, notes: f.notes || "", expiration: f.expiration || null };
    try {
      if (item) await api.put(`/groceries/${item.id}`, body);
      else await api.post("/groceries", body);
      toast.success("Saved"); refreshAll(); setOpen(false);
    } catch { toast.error("Could not save"); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto" data-testid="grocery-dialog">
        <DialogHeader><DialogTitle>{item ? "Edit item" : "Add item"}</DialogTitle>
          <DialogDescription className="sr-only">Add or edit a grocery inventory item</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Input placeholder="Item name" value={f.name || ""} onChange={set("name")} data-testid="grocery-name-input" />
          <div className="grid grid-cols-3 gap-2">
            <Input placeholder="Quantity" type="number" value={f.quantity ?? ""} onChange={set("quantity")} data-testid="grocery-qty-input" />
            <Input placeholder="Unit" value={f.unit || ""} onChange={set("unit")} />
            <Input placeholder="Low at" type="number" value={f.low_threshold ?? ""} onChange={set("low_threshold")} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Select value={f.category} onValueChange={(v) => setF((p) => ({ ...p, category: v }))}>
              <SelectTrigger data-testid="grocery-cat-input"><SelectValue placeholder="Category" /></SelectTrigger>
              <SelectContent>{CATS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
            <Input placeholder="€ price (leave blank if unknown)" type="number" value={f.price ?? ""} onChange={set("price")} data-testid="grocery-price-input" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="Store" value={f.store || ""} onChange={set("store")} />
            <Input placeholder="Expiration" type="date" value={f.expiration || ""} onChange={set("expiration")} />
          </div>
          <Input placeholder="Notes" value={f.notes || ""} onChange={set("notes")} />
          <Button onClick={save} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="grocery-save">Save</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function Groceries() {
  const [tab, setTab] = useState("inventory");
  const [items, setItems] = useState(null);
  const [shopping, setShopping] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [newShop, setNewShop] = useState("");

  const load = useCallback(async () => {
    const [g, s] = await Promise.all([api.get("/groceries"), api.get("/shopping")]);
    setItems(g.data); setShopping(s.data);
  }, []);
  useEffect(() => { load(); const h = () => load(); window.addEventListener("lm:refresh", h); return () => window.removeEventListener("lm:refresh", h); }, [load]);

  const adjust = async (g, delta) => {
    const q = Math.max(0, (g.quantity || 0) + delta);
    await api.put(`/groceries/${g.id}`, { quantity: q });
    refreshAll();
  };
  const del = async (id) => { await api.delete(`/groceries/${id}`); refreshAll(); };

  const generate = async () => { await api.post("/shopping/generate"); toast.success("Shopping list generated"); refreshAll(); };
  const addShop = async () => { if (!newShop.trim()) return; await api.post("/shopping", { name: newShop }); setNewShop(""); refreshAll(); };
  const buy = async (it) => { await api.post(`/shopping/${it.id}/buy`, { price: it.best?.price ?? null, store: it.best?.store ?? null }); toast.success(`${it.name} added to inventory`); refreshAll(); };
  const delShop = async (id) => { await api.delete(`/shopping/${id}`); refreshAll(); };

  const arr = items || [];
  const low = arr.filter((g) => (g.quantity || 0) > 0 && g.low_threshold && g.quantity <= g.low_threshold);
  const out = arr.filter((g) => (g.quantity || 0) <= 0);

  return (
    <div className="space-y-6">
      <SectionHeading title="Groceries" sub="Inventory, prices, stock levels and smart shopping"
        action={<Button onClick={() => { setEditItem(null); setDialogOpen(true); }} className="h-9 bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="add-grocery-btn"><Plus className="h-4 w-4 mr-1" />Add item</Button>} />

      <div className="flex gap-1 rounded-lg bg-slate-100 dark:bg-slate-800 p-1 w-fit">
        {[["inventory", "Inventory"], ["shopping", "Shopping list"]].map(([k, l]) => (
          <button key={k} data-testid={`gtab-${k}`} onClick={() => setTab(k)}
            className={cn("rounded-md px-4 py-1.5 text-sm font-medium transition-colors", tab === k ? "bg-white dark:bg-slate-700 shadow-sm" : "text-slate-500")}>{l}</button>
        ))}
      </div>

      {tab === "inventory" && (
        <>
          {(low.length > 0 || out.length > 0) && (
            <div className="grid sm:grid-cols-2 gap-3">
              {out.length > 0 && (
                <Card className="p-4 flex items-center gap-3 border-red-200 dark:border-red-500/30 bg-red-50/60 dark:bg-red-500/10">
                  <AlertTriangle className="h-5 w-5 text-red-500 shrink-0" />
                  <p className="text-sm text-red-800 dark:text-red-300" data-testid="out-of-stock"><b>Out of stock:</b> {out.map((g) => g.name).join(", ")}</p>
                </Card>
              )}
              {low.length > 0 && (
                <Card className="p-4 flex items-center gap-3 border-amber-200 dark:border-amber-500/30 bg-amber-50/60 dark:bg-amber-500/10">
                  <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
                  <p className="text-sm text-amber-800 dark:text-amber-300" data-testid="low-stock"><b>Running low:</b> {low.map((g) => `${g.name} (${g.quantity})`).join(", ")}</p>
                </Card>
              )}
            </div>
          )}

          {items === null ? <div className="skeleton h-64 rounded-2xl" /> : arr.length === 0 ? (
            <Card><EmptyState icon={ShoppingCart} title="Inventory is empty" sub="Add groceries manually or let the assistant log a purchase." /></Card>
          ) : (
            <Card>
              <div className="divide-y divide-border">
                {arr.map((g) => {
                  const isLow = (g.quantity || 0) > 0 && !!g.low_threshold && g.quantity <= g.low_threshold;
                  const isOut = (g.quantity || 0) <= 0;
                  return (
                    <div key={g.id} data-testid={`grocery-${g.id}`} className="flex items-center gap-3 px-5 py-3 group">
                      <div className={cn("h-9 w-9 rounded-xl grid place-items-center shrink-0", isOut ? "bg-red-50 dark:bg-red-500/10" : "bg-emerald-50 dark:bg-emerald-500/10")}>
                        <ShoppingCart className={cn("h-4 w-4", isOut ? "text-red-500" : "text-emerald-600")} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-medium text-sm">{g.name}</p>
                          {isOut && <ConfidenceBadge type="unknown">Out of stock</ConfidenceBadge>}
                          {isLow && <ConfidenceBadge type="estimated">Low</ConfidenceBadge>}
                        </div>
                        <p className="text-xs text-slate-500">
                          {g.category}{g.store ? ` · ${g.store}` : ""} · {g.price != null ? `Price: ${eur(g.price)}` : "Price: Unknown"}
                          {g.notes ? ` · ${g.notes}` : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        <button onClick={() => adjust(g, -1)} className="h-7 w-7 grid place-items-center rounded-lg border border-border hover:bg-slate-100 dark:hover:bg-slate-800" data-testid={`grocery-dec-${g.id}`}><Minus className="h-3.5 w-3.5" /></button>
                        <span className={cn("stat-num text-sm font-semibold w-14 text-center", isLow && "text-amber-500", isOut && "text-red-500")}>{g.quantity} {g.unit}</span>
                        <button onClick={() => adjust(g, 1)} className="h-7 w-7 grid place-items-center rounded-lg border border-border hover:bg-slate-100 dark:hover:bg-slate-800" data-testid={`grocery-inc-${g.id}`}><Plus className="h-3.5 w-3.5" /></button>
                      </div>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => { setEditItem(g); setDialogOpen(true); }} className="text-slate-300 hover:text-emerald-600" data-testid={`grocery-edit-${g.id}`}><Pencil className="h-4 w-4" /></button>
                        <button onClick={() => del(g.id)} className="text-slate-300 hover:text-red-500" data-testid={`grocery-del-${g.id}`}><Trash2 className="h-4 w-4" /></button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          )}
        </>
      )}

      {tab === "shopping" && (
        <>
          <div className="flex gap-2">
            <Input placeholder="Add to list…" value={newShop} onChange={(e) => setNewShop(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addShop()} data-testid="shopping-add-input" />
            <Button onClick={addShop} variant="outline"><Plus className="h-4 w-4" /></Button>
            <Button onClick={generate} className="bg-emerald-600 hover:bg-emerald-700 text-white shrink-0" data-testid="shopping-generate"><Sparkles className="h-4 w-4 mr-1" />Generate</Button>
          </div>

          {shopping?.recommendation && (
            <Card className="p-5 border-emerald-200 dark:border-emerald-500/30 bg-emerald-50/40 dark:bg-emerald-500/10">
              <div className="flex items-center gap-2 mb-2"><Store className="h-4 w-4 text-emerald-600" /><h3 className="font-semibold text-sm">Price intelligence</h3></div>
              <p className="text-sm text-slate-700 dark:text-slate-300" data-testid="shopping-recommendation">{shopping.recommendation}</p>
              {shopping.stores?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {shopping.stores.map((s) => (
                    <span key={s.store} className="text-xs rounded-full border border-border px-2.5 py-1">
                      {s.store}: <span className="stat-num font-semibold">{eur(s.total)}</span> <span className="text-slate-400">({s.covers} items)</span>
                    </span>
                  ))}
                </div>
              )}
            </Card>
          )}

          {!shopping?.items?.length ? (
            <Card><EmptyState icon={ShoppingCart} title="Your shopping list is empty" sub="Add items or tap Generate to build one from your inventory and usual buys." /></Card>
          ) : (
            <Card>
              <div className="divide-y divide-border">
                {shopping.items.map((it) => (
                  <div key={it.id} data-testid={`shop-${it.id}`} className="flex items-center gap-3 px-5 py-3 group">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm">{it.name} <span className="text-slate-400 font-normal">×{it.quantity}</span></p>
                      <p className="text-xs text-slate-500 flex items-center gap-1.5">
                        {it.known ? <>Best: {it.best.store} <ConfidenceBadge type="historical">{eur(it.best.price)}</ConfidenceBadge></> : <ConfidenceBadge type="unknown">Price unknown</ConfidenceBadge>}
                        {it.note ? ` · ${it.note}` : ""}
                      </p>
                    </div>
                    <button onClick={() => buy(it)} className="h-8 px-2.5 rounded-lg border border-emerald-300 text-emerald-700 dark:text-emerald-300 text-xs font-medium hover:bg-emerald-50 dark:hover:bg-emerald-500/10 flex items-center gap-1" data-testid={`shop-buy-${it.id}`}><Check className="h-3.5 w-3.5" />Bought</button>
                    <button onClick={() => delShop(it.id)} className="text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      <GroceryDialog item={editItem} open={dialogOpen} setOpen={setDialogOpen} />
    </div>
  );
}
