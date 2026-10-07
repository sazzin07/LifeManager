import { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, eur } from "@/lib/api";
import { refreshAll } from "@/lib/useFetch";
import { Avatar } from "@/components/common";
import { Plus, Trash2, Users, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export function ExpenseDialog({ open, setOpen }) {
  const [cats, setCats] = useState([]);
  const [people, setPeople] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [saving, setSaving] = useState(false);

  const [amount, setAmount] = useState("");
  const [merchant, setMerchant] = useState("");
  const [category, setCategory] = useState("Groceries");
  const [account, setAccount] = useState("cash");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [participants, setParticipants] = useState(["Me"]);
  const [splitMode, setSplitMode] = useState("equal");
  const [items, setItems] = useState([]);

  useEffect(() => {
    if (!open) return;
    api.get("/categories").then((r) => setCats(r.data));
    api.get("/people").then((r) => setPeople(r.data));
    api.get("/accounts").then((r) => setAccounts(r.data));
  }, [open]);

  const toggleParticipant = (name) => {
    setParticipants((p) => (p.includes(name) ? p.filter((x) => x !== name) : [...p, name]));
  };

  const itemsTotal = useMemo(() => items.reduce((s, i) => s + (parseFloat(i.price) || 0), 0), [items]);

  const myShare = useMemo(() => {
    if (splitMode === "items") {
      let mine = 0;
      items.forEach((it) => {
        const a = it.assigned?.length ? it.assigned : ["Me"];
        if (a.includes("Me")) mine += (parseFloat(it.price) || 0) / a.length;
      });
      return mine;
    }
    const gross = parseFloat(amount) || 0;
    return participants.length ? gross / participants.length : gross;
  }, [splitMode, items, amount, participants]);

  const gross = splitMode === "items" ? itemsTotal : parseFloat(amount) || 0;

  const reset = () => {
    setAmount(""); setMerchant(""); setNotes(""); setParticipants(["Me"]);
    setSplitMode("equal"); setItems([]); setCategory("Groceries"); setAccount("cash");
  };

  const save = async () => {
    if (gross <= 0) { toast.error("Enter an amount"); return; }
    setSaving(true);
    try {
      await api.post("/transactions/expense", {
        amount: gross, merchant, description: merchant, category, account, date, notes,
        participants, split_mode: splitMode,
        items: splitMode === "items" ? items.map((i) => ({ name: i.name, price: parseFloat(i.price) || 0, assigned: i.assigned?.length ? i.assigned : ["Me"] })) : [],
        add_to_inventory: category === "Groceries" && splitMode === "items",
      });
      toast.success("Expense added");
      refreshAll();
      reset();
      setOpen(false);
    } catch { toast.error("Could not save expense"); }
    finally { setSaving(false); }
  };

  const allNames = ["Me", ...people.map((p) => p.name)];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="expense-dialog">
        <DialogHeader><DialogTitle>Add expense</DialogTitle>
          <DialogDescription className="sr-only">Create a new expense with optional sharing and item-level splitting</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Amount</label>
              <Input data-testid="expense-amount" type="number" step="0.01" value={splitMode === "items" ? itemsTotal.toFixed(2) : amount}
                onChange={(e) => setAmount(e.target.value)} disabled={splitMode === "items"} placeholder="0.00" className="mt-1" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Date</label>
              <Input data-testid="expense-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} className="mt-1" />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Merchant</label>
            <Input data-testid="expense-merchant" value={merchant} onChange={(e) => setMerchant(e.target.value)} placeholder="e.g. Lidl" className="mt-1" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Category</label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger data-testid="expense-category" className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>{cats.map((c) => <SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Paid with</label>
              <Select value={account} onValueChange={setAccount}>
                <SelectTrigger data-testid="expense-account" className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="cash">Cash</SelectItem>
                  <SelectItem value="revolut">Card (Revolut)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1.5"><Users className="h-3.5 w-3.5" /> Who participated?</label>
            <div className="mt-2 flex flex-wrap gap-2">
              {allNames.map((name) => (
                <button key={name} type="button" data-testid={`participant-${name.toLowerCase()}`} onClick={() => name !== "Me" && toggleParticipant(name)}
                  className={cn("flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm transition-colors",
                    participants.includes(name) ? "border-emerald-400 bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" : "border-border text-slate-500")}>
                  <Avatar name={name} size="h-5 w-5" />{name}
                </button>
              ))}
            </div>
          </div>

          {participants.length > 1 && (
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Split</label>
              <div className="mt-2 flex gap-2">
                {["equal", "items"].map((m) => (
                  <button key={m} type="button" data-testid={`split-${m}`} onClick={() => setSplitMode(m)}
                    className={cn("rounded-lg border px-3 py-1.5 text-sm capitalize", splitMode === m ? "border-emerald-400 bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" : "border-border text-slate-500")}>
                    {m === "items" ? "By item" : "Equal"}
                  </button>
                ))}
              </div>
            </div>
          )}

          {splitMode === "items" && participants.length > 1 && (
            <div className="rounded-xl border border-border p-3 space-y-3">
              {items.map((it, idx) => (
                <div key={idx} className="space-y-2 pb-2 border-b border-border last:border-0 last:pb-0">
                  <div className="flex gap-2">
                    <Input placeholder="Item" value={it.name} onChange={(e) => setItems((a) => a.map((x, i) => i === idx ? { ...x, name: e.target.value } : x))} className="h-9" />
                    <Input placeholder="€" type="number" step="0.01" value={it.price} onChange={(e) => setItems((a) => a.map((x, i) => i === idx ? { ...x, price: e.target.value } : x))} className="h-9 w-24" />
                    <button onClick={() => setItems((a) => a.filter((_, i) => i !== idx))} className="h-9 w-9 grid place-items-center rounded-lg text-slate-400 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {participants.map((name) => {
                      const on = (it.assigned || []).includes(name);
                      return (
                        <button key={name} type="button" onClick={() => setItems((a) => a.map((x, i) => i === idx ? { ...x, assigned: on ? (x.assigned || []).filter((n) => n !== name) : [...(x.assigned || []), name] } : x))}
                          className={cn("rounded-md px-2 py-0.5 text-xs border", on ? "border-emerald-400 bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" : "border-border text-slate-400")}>{name}</button>
                      );
                    })}
                  </div>
                </div>
              ))}
              <Button variant="outline" size="sm" onClick={() => setItems((a) => [...a, { name: "", price: "", assigned: ["Me"] }])} className="w-full" data-testid="add-item-btn">
                <Plus className="h-4 w-4 mr-1" /> Add item
              </Button>
            </div>
          )}

          <Textarea placeholder="Notes (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} data-testid="expense-notes" />

          <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 p-4 flex items-center justify-between text-sm">
            <div>
              <div className="text-slate-500">Total {eur(gross)}</div>
              <div className="font-semibold text-slate-900 dark:text-slate-100 mt-0.5">Your share {eur(myShare)}</div>
            </div>
            {gross - myShare > 0.005 && <div className="text-right text-emerald-600 dark:text-emerald-400 font-semibold">+{eur(gross - myShare)}<div className="text-xs text-slate-500 font-normal">to receive</div></div>}
          </div>

          <Button data-testid="expense-save" onClick={save} disabled={saving} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white h-11">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save expense"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
