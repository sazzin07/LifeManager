import { useNavigate } from "react-router-dom";
import { Users, ChevronRight, HandCoins } from "lucide-react";
import { eur } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { Card, StatCard, SectionHeading, EmptyState, Avatar, SkeletonCard } from "@/components/common";
import { cn } from "@/lib/utils";

export default function People() {
  const nav = useNavigate();
  const { data: people, loading } = useFetch("/people");
  const totalOwed = (people || []).reduce((s, p) => s + Math.max(p.net, 0), 0);
  const totalIOwe = (people || []).reduce((s, p) => s + Math.max(-p.net, 0), 0);

  return (
    <div className="space-y-6">
      <SectionHeading title="People" sub="Shared expenses, balances and reimbursements" />
      {loading ? <div className="grid md:grid-cols-2 gap-4">{Array.from({ length: 2 }).map((_, i) => <SkeletonCard key={i} />)}</div> : (
        <>
          <div className="grid grid-cols-2 gap-4">
            <StatCard testid="total-owed" label="You are owed" value={eur(totalOwed)} accent="text-emerald-600 dark:text-emerald-400" icon={HandCoins} />
            <StatCard testid="total-i-owe" label="You owe" value={eur(totalIOwe)} accent="text-red-500" icon={HandCoins} />
          </div>
          <Card>
            {(people || []).length === 0 ? (
              <EmptyState icon={Users} title="No people yet" sub="Add people to split expenses and track who owes what." />
            ) : (
              <div className="divide-y divide-border">
                {people.map((p) => (
                  <button key={p.id} data-testid={`person-${p.id}`} onClick={() => nav(`/people/${p.id}`)}
                    className="w-full flex items-center gap-3 px-5 py-4 hover:bg-slate-50 dark:hover:bg-slate-800/40 text-left">
                    <Avatar name={p.name} photo={p.photo} />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium">{p.name}</p>
                      <p className="text-xs text-slate-500">{p.net > 0.005 ? "owes you" : p.net < -0.005 ? "you owe" : "settled up"}</p>
                    </div>
                    <span className={cn("stat-num font-bold", p.net > 0.005 ? "text-emerald-600 dark:text-emerald-400" : p.net < -0.005 ? "text-red-500" : "text-slate-400")}>
                      {p.net > 0 ? "+" : ""}{eur(p.net)}
                    </span>
                    <ChevronRight className="h-4 w-4 text-slate-300" />
                  </button>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
