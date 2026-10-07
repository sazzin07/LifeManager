import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("sa@lifemanager.app");
  const [password, setPassword] = useState("lifemanager123");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email.trim(), password);
      nav("/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not sign in. Check your details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      <div className="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950 text-white relative overflow-hidden">
        <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full bg-emerald-500/20 blur-3xl" />
        <div className="flex items-center gap-2 relative">
          <div className="h-9 w-9 rounded-xl bg-emerald-500 grid place-items-center"><Sparkles className="h-5 w-5" /></div>
          <span className="font-bold text-lg tracking-tight">Life Manager</span>
        </div>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="relative">
          <h1 className="text-4xl xl:text-5xl font-extrabold tracking-tight leading-tight">
            Your money, food, training and life — <span className="text-emerald-400">in one calm place.</span>
          </h1>
          <p className="mt-5 text-slate-300 max-w-md leading-relaxed">
            Type it, speak it or photograph it. Life Manager turns raw moments into organised, connected insight.
          </p>
        </motion.div>
        <p className="text-xs text-slate-500 relative">Private • Single-user • Built for you</p>
      </div>

      <div className="flex items-center justify-center p-8">
        <motion.form initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          onSubmit={submit} className="w-full max-w-sm" data-testid="login-form">
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="h-9 w-9 rounded-xl bg-emerald-600 grid place-items-center text-white"><Sparkles className="h-5 w-5" /></div>
            <span className="font-bold text-lg">Life Manager</span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Welcome back, Sá</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Sign in to your command center.</p>

          <div className="mt-8 space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Email</label>
              <Input data-testid="login-email" value={email} onChange={(e) => setEmail(e.target.value)} type="email" className="mt-1.5 h-11" />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Password</label>
              <Input data-testid="login-password" value={password} onChange={(e) => setPassword(e.target.value)} type="password" className="mt-1.5 h-11" />
            </div>
          </div>

          <Button data-testid="login-submit" type="submit" disabled={loading} className="w-full h-11 mt-6 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Enter <ArrowRight className="h-4 w-4 ml-1" /></>}
          </Button>
          <p className="text-xs text-slate-400 mt-4 text-center">Demo credentials are pre-filled for you.</p>
        </motion.form>
      </div>
    </div>
  );
}
