import { useNavigate } from "react-router-dom";
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { LayoutDashboard, Wallet, Users, ShoppingCart, Utensils, Dumbbell, HeartPulse, CheckSquare, Calendar, Settings, Plus, Sparkles } from "lucide-react";
import { openAI } from "@/components/AppShell";

const NAV = [
  { to: "/", label: "Home", icon: LayoutDashboard },
  { to: "/money", label: "Money", icon: Wallet },
  { to: "/people", label: "People", icon: Users },
  { to: "/groceries", label: "Groceries", icon: ShoppingCart },
  { to: "/nutrition", label: "Nutrition", icon: Utensils },
  { to: "/fitness", label: "Fitness", icon: Dumbbell },
  { to: "/body", label: "Body", icon: HeartPulse },
  { to: "/tasks", label: "Tasks", icon: CheckSquare },
  { to: "/calendar", label: "Calendar", icon: Calendar },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function CommandBar({ open, setOpen, onQuickAdd }) {
  const nav = useNavigate();
  const go = (fn) => { setOpen(false); setTimeout(fn, 50); };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search…" data-testid="command-input" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Actions">
          <CommandItem onSelect={() => go(() => onQuickAdd())}><Plus className="mr-2 h-4 w-4" />Quick add</CommandItem>
          <CommandItem onSelect={() => go(() => openAI())}><Sparkles className="mr-2 h-4 w-4" />Ask the assistant</CommandItem>
        </CommandGroup>
        <CommandGroup heading="Navigate">
          {NAV.map((n) => (
            <CommandItem key={n.to} onSelect={() => go(() => nav(n.to))}><n.icon className="mr-2 h-4 w-4" />{n.label}</CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
