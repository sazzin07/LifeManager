import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { ArrowLeft, HandCoins } from "lucide-react";
import { api, eur } from "@/lib/api";
import { useFetch, refreshAll } from "@/lib/useFetch";
import { Card, SectionHeading, Avatar, Label, EmptyState } from "@/components/common";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function PersonDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { data, loading } = useFetch(`/people/${id}`);
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("Revolut");
  const [account, setAccount] = useState("revolut");

  if (loading || !data) return <div className="skeleton h-64 w-full rounded-2xl" />;
  const { person, transactions, settlements } = data;

  const record = async () => {
    if (!parseFloat(amount)) return;
    await api.post("/settlements", { person: person.name, amount: parseFloat(amount), method, account, direction: "in" });
    toast.success("Payment recorded");
    setOpen(false); setAmount(""); refreshAll();
  };

  return (
    <div className="space-y-6">
      <button onClick={() => nav("/people")} className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"><ArrowLeft className="h-4 w-4" />People</button>
      <Card className="p-6 flex items-center gap-4">
        <Avatar name={person.name} photo={person.photo} size="h-14 w-14" />
        <div className="flex-1">
          <h2 className="text-xl font-bold">{person.name}</h2>
          <p className="text-sm text-slate-500">{person.net > 0.005 ? "Owes you" : person.net < -0.005 ? "You owe" : "Settled up"}</p>
        </div>
        <div className="text-right">
          <div className={cn("stat-num text-2xl font-extrabold", person.net > 0.005 ? "text-emerald-600 dark:text-emerald-400" : person.net < -0.005 ? "text-red-500" : "text-slate-400")}>{person.net > 0 ? "+" : ""}{eur(person.net)}</div>
          {person.net > 0.005 && <Button data-testid="record-payment-btn" onClick={() => setOpen(true)} size="sm" className="mt-2 bg-emerald-600 hover:bg-emerald-700 text-white"><HandCoins className="h-4 w-4 mr-1" />Record payment</Button>}
        </div>
      </Card>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card className="p-5">
          <Label>Shared expenses</Label>
          <div className="mt-3 divide-y divide-border">
            {transactions.length === 0 ? <EmptyState title="No shared expenses" sub="Split an expense with this person to see it here." /> :
              transactions.map((t) => (
                <div key={t.id + t.date} className="flex items-center justify-between py-2.5 text-sm">
                  <div><p className="font-medium">{t.merchant}</p><p className="text-xs text-slate-500">{t.date}</p></div>
                  <span className="stat-num font-semibold text-emerald-600 dark:text-emerald-400">{eur(t.amount)}</span>
                </div>
              ))}
          </div>
        </Card>
        <Card className="p-5">
          <Label>Payments received</Label>
          <div className="mt-3 divide-y divide-border">
            {settlements.length === 0 ? <EmptyState title="No payments yet" sub="Recorded reimbursements will appear here." /> :
              settlements.map((s) => (
                <div key={s.id} className="flex items-center justify-between py-2.5 text-sm">
                  <div><p className="font-medium">{s.method}</p><p className="text-xs text-slate-500">{s.date}</p></div>
                  <span className="stat-num font-semibold">{eur(s.amount)}</span>
                </div>
              ))}
          </div>
        </Card>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Record payment from {person.name}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Amount" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} data-testid="settle-amount" />
            <div className="grid grid-cols-2 gap-2">
              <Select value={method} onValueChange={setMethod}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="Revolut">Revolut</SelectItem><SelectItem value="MB WAY">MB WAY</SelectItem><SelectItem value="Cash">Cash</SelectItem></SelectContent></Select>
              <Select value={account} onValueChange={setAccount}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="revolut">Into Revolut</SelectItem><SelectItem value="cash">Into Cash</SelectItem></SelectContent></Select>
            </div>
            <Button onClick={record} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="settle-submit">Record {amount ? eur(parseFloat(amount)) : ""}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
