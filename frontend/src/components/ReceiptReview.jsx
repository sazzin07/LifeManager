import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, eur } from "@/lib/api";
import { refreshAll } from "@/lib/useFetch";
import { Plus, Trash2, ScanLine } from "lucide-react";
import { toast } from "sonner";

const CATS = ["Groceries", "Eating Out", "Transport", "Shopping", "Entertainment", "Health", "Bills", "Other"];

export function ReceiptReview({ data, open, setOpen }) {
  const [merchant, setMerchant] = useState("");
  const [date, setDate] = useState("");
  const [category, setCategory] = useState("Groceries");
  const [account, setAccount] = useState("card");
  const [items, setItems] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!data) return;
    setMerchant(data.merchant || "");
    setDate(data.date || new Date().toISOString().slice(0, 10));
    setItems((data.items || []).map((i) => ({ name: i.name || "", price: i.price ?? "" })));
  }, [data]);

  const total = items.reduce((s, i) => s + (parseFloat(i.price) || 0), 0);

  const save = async () => {
    setSaving(true);
    try {
      await api.post("/transactions/expense", {
        amount: total || data?.total || 0, merchant, description: merchant, category,
        account: account === "cash" ? "cash" : "revolut", date,
        participants: ["Me"], split_mode: "items",
        items: items.filter((i) => i.name).map((i) => ({ name: i.name, price: parseFloat(i.price) || 0, assigned: ["Me"] })),
        add_to_inventory: category === "Groceries",
      });
      toast.success("Expense saved from receipt");
      refreshAll();
      setOpen(false);
    } catch { toast.error("Could not save"); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="receipt-review">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><ScanLine className="h-5 w-5 text-emerald-600" />Review receipt</DialogTitle>
          <DialogDescription>Check the items and prices below before saving. Nothing is saved until you confirm.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="Merchant" value={merchant} onChange={(e) => setMerchant(e.target.value)} data-testid="receipt-merchant" />
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} data-testid="receipt-date" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{CATS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
            <Select value={account} onValueChange={setAccount}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="cash">Cash</SelectItem><SelectItem value="card">Card (Revolut)</SelectItem></SelectContent>
            </Select>
          </div>
          <div className="rounded-xl border border-border p-3 space-y-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Items found: {items.length}</p>
            {items.map((it, idx) => (
              <div key={idx} className="flex gap-2">
                <Input placeholder="Item" value={it.name} onChange={(e) => setItems((a) => a.map((x, i) => i === idx ? { ...x, name: e.target.value } : x))} className="h-9" data-testid={`receipt-item-${idx}`} />
                <Input placeholder="€" type="number" step="0.01" value={it.price} onChange={(e) => setItems((a) => a.map((x, i) => i === idx ? { ...x, price: e.target.value } : x))} className="h-9 w-24" />
                <button onClick={() => setItems((a) => a.filter((_, i) => i !== idx))} className="h-9 w-9 grid place-items-center text-slate-400 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
            <Button variant="outline" size="sm" className="w-full" onClick={() => setItems((a) => [...a, { name: "", price: "" }])}><Plus className="h-4 w-4 mr-1" />Add item</Button>
          </div>
          <div className="flex items-center justify-between rounded-xl bg-slate-50 dark:bg-slate-800/50 p-3 text-sm">
            <span className="text-slate-500">Total</span><span className="stat-num font-bold">{eur(total)}</span>
          </div>
          <Button onClick={save} disabled={saving} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="receipt-save">
            {saving ? "Saving…" : "Confirm & save expense"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
