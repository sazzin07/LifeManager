import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, eur } from "@/lib/api";
import { refreshAll } from "@/lib/useFetch";
import { HandCoins, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";

export function EditExpenseDialog({ txn, open, setOpen }) {
  const [cats, setCats] = useState([]);
  const [people, setPeople] = useState([]);
  const [f, setF] = useState({});
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [refundOpen, setRefundOpen] = useState(false);
  const [refund, setRefund] = useState({ amount: "", method: "Revolut", account: "revolut", person: "" });

  useEffect(() => {
    if (!open || !txn) return;
    api.get("/categories").then((r) => setCats(r.data));
    api.get("/people").then((r) => setPeople(r.data));
    setF({
      description: txn.merchant || txn.description || "",
      amount: txn.gross_amount, personal_amount: txn.personal_amount,
      category: txn.category, payment_method: txn.payment_method || (txn.account === "cash" ? "cash" : "card"),
      date: txn.date, notes: txn.notes || "",
    });
    setRefund((r) => ({ ...r, person: txn.responsible?.[0] || "" }));
  }, [open, txn]);

  if (!txn) return null;
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));

  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/transactions/${txn.id}`, {
        description: f.description, category: f.category, payment_method: f.payment_method,
        date: f.date, notes: f.notes, amount: parseFloat(f.amount),
        personal_amount: f.personal_amount === "" ? null : parseFloat(f.personal_amount),
      });
      toast.success("Expense updated");
      refreshAll();
      setOpen(false);
    } catch { toast.error("Could not update expense"); }
    finally { setSaving(false); }
  };

  const del = async () => {
    try { await api.delete(`/transactions/${txn.id}`); toast.success("Expense deleted"); refreshAll(); setConfirmDelete(false); setOpen(false); }
    catch { toast.error("Could not delete"); }
  };

  const recordRefund = async () => {
    if (!parseFloat(refund.amount) || !refund.person) { toast.error("Enter amount and person"); return; }
    await api.post("/settlements", {
      person: refund.person, amount: parseFloat(refund.amount), method: refund.method,
      account: refund.account, direction: "in", transaction_id: txn.id,
    });
    toast.success("Refund recorded");
    refreshAll();
    setRefundOpen(false);
    setOpen(false);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="edit-expense-dialog">
          <DialogHeader><DialogTitle>Edit expense</DialogTitle>
            <DialogDescription className="sr-only">Edit or delete this expense and manage refunds</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Description</label>
              <Input value={f.description || ""} onChange={set("description")} className="mt-1" data-testid="edit-description" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Total (€)</label>
                <Input type="number" step="0.01" value={f.amount ?? ""} onChange={set("amount")} className="mt-1" data-testid="edit-amount" />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Your personal cost (€)</label>
                <Input type="number" step="0.01" value={f.personal_amount ?? ""} onChange={set("personal_amount")} className="mt-1" data-testid="edit-personal" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Category</label>
                <Select value={f.category} onValueChange={(v) => setF((p) => ({ ...p, category: v }))}>
                  <SelectTrigger className="mt-1" data-testid="edit-category"><SelectValue /></SelectTrigger>
                  <SelectContent>{cats.map((c) => <SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Payment</label>
                <Select value={f.payment_method} onValueChange={(v) => setF((p) => ({ ...p, payment_method: v }))}>
                  <SelectTrigger className="mt-1" data-testid="edit-method"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="cash">Cash</SelectItem><SelectItem value="card">Card (Revolut)</SelectItem></SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Date</label>
              <Input type="date" value={f.date || ""} onChange={set("date")} className="mt-1" data-testid="edit-date" />
            </div>
            <Textarea placeholder="Notes" value={f.notes || ""} onChange={set("notes")} rows={2} data-testid="edit-notes" />

            {txn.reimbursable_amount > 0.005 && (
              <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 p-4 text-sm space-y-1.5">
                <div className="flex justify-between"><span className="text-slate-500">To be refunded</span><span className="stat-num font-semibold">{eur(txn.reimbursable_amount)}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Already refunded</span><span className="stat-num font-semibold text-emerald-600 dark:text-emerald-400">{eur(txn.amount_refunded || 0)}</span></div>
                <div className="flex justify-between border-t border-border pt-1.5"><span className="text-slate-500">Remaining</span><span className="stat-num font-bold text-amber-600 dark:text-amber-400" data-testid="edit-remaining">{eur(txn.remaining_refund ?? txn.reimbursable_amount)}</span></div>
                <div className="text-xs text-slate-500">Owed by: {txn.responsible?.join(", ") || "—"}</div>
                {txn.remaining_refund > 0.005 && (
                  <Button size="sm" variant="outline" className="w-full mt-2" onClick={() => setRefundOpen(true)} data-testid="edit-record-refund">
                    <HandCoins className="h-4 w-4 mr-1" />Record refund
                  </Button>
                )}
              </div>
            )}

            <div className="flex gap-2 pt-1">
              <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50 dark:border-red-500/30" onClick={() => setConfirmDelete(true)} data-testid="edit-delete">
                <Trash2 className="h-4 w-4 mr-1" />Delete
              </Button>
              <Button onClick={save} disabled={saving} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="edit-save">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save changes"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={refundOpen} onOpenChange={setRefundOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Record refund</DialogTitle>
            <DialogDescription className="sr-only">Record a refund against this expense</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Select value={refund.person} onValueChange={(v) => setRefund((r) => ({ ...r, person: v }))}>
              <SelectTrigger data-testid="refund-person"><SelectValue placeholder="Who paid you?" /></SelectTrigger>
              <SelectContent>{people.map((p) => <SelectItem key={p.id} value={p.name}>{p.name}</SelectItem>)}</SelectContent>
            </Select>
            <Input placeholder="Amount" type="number" value={refund.amount} onChange={(e) => setRefund((r) => ({ ...r, amount: e.target.value }))} data-testid="refund-amount" />
            <div className="grid grid-cols-2 gap-2">
              <Select value={refund.method} onValueChange={(v) => setRefund((r) => ({ ...r, method: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="Revolut">Revolut</SelectItem><SelectItem value="MB WAY">MB WAY</SelectItem><SelectItem value="Cash">Cash</SelectItem></SelectContent>
              </Select>
              <Select value={refund.account} onValueChange={(v) => setRefund((r) => ({ ...r, account: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="revolut">Into Revolut</SelectItem><SelectItem value="cash">Into Cash</SelectItem></SelectContent>
              </Select>
            </div>
            <Button onClick={recordRefund} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="refund-submit">Record</Button>
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this expense?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete "{txn.merchant || txn.description}" ({eur(txn.gross_amount)}) and any linked refunds. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="delete-cancel">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={del} className="bg-red-600 hover:bg-red-700" data-testid="delete-confirm">Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
