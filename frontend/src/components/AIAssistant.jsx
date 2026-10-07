import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, X, Send, Mic, Paperclip, Loader2, Square, Undo2, ScanLine, MessageSquare, History } from "lucide-react";
import { api } from "@/lib/api";
import { refreshAll } from "@/lib/useFetch";
import { Avatar } from "@/components/common";
import { ReceiptReview } from "@/components/ReceiptReview";
import { toast } from "sonner";

const SUGGESTIONS = [
  "What did I spend this month?",
  "How much do people owe me?",
  "I spent €14 at McDonald's on cash",
  "Log 3 eggs, 200g chicken and 300ml milk",
];

export function AIAssistant() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [session] = useState(() => localStorage.getItem("lm_ai_session") || crypto.randomUUID());
  const [image, setImage] = useState(null);
  const [recording, setRecording] = useState(false);
  const fileRef = useRef(null);
  const scrollRef = useRef(null);
  const recRef = useRef(null);
  const loc = useLocation();
  const [tab, setTab] = useState("chat");
  const [actions, setActions] = useState([]);
  const [receiptData, setReceiptData] = useState(null);
  const [receiptOpen, setReceiptOpen] = useState(false);
  const [scanning, setScanning] = useState(false);

  useEffect(() => { setOpen(false); }, [loc.pathname]);

  const loadActions = async () => { try { const { data } = await api.get("/ai/actions"); setActions(data); } catch { /* ignore */ } };
  useEffect(() => { if (open && tab === "activity") loadActions(); }, [open, tab]);
  const undoAction = async (id) => {
    try { await api.post(`/ai/actions/${id}/undo`); toast.success("Change undone"); refreshAll(); loadActions(); }
    catch { toast.error("Could not undo this action"); }
  };
  const scanReceipt = async () => {
    if (!image) return;
    setScanning(true);
    try { const { data } = await api.post("/ai/receipt", { image_base64: image }); 
      if (!data.items?.length && !data.merchant) { toast.error("No receipt detected in that image"); return; }
      setReceiptData(data); setReceiptOpen(true); setImage(null); }
    catch { toast.error("Could not read receipt"); }
    finally { setScanning(false); }
  };

  useEffect(() => { localStorage.setItem("lm_ai_session", session); }, [session]);

  useEffect(() => {
    const h = (e) => {
      setOpen(true);
      if (e.detail?.prompt) setInput(e.detail.prompt);
    };
    window.addEventListener("lm:openAI", h);
    return () => window.removeEventListener("lm:openAI", h);
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [msgs, busy]);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message && !image) return;
    setInput("");
    const userMsg = { role: "user", text: message || "(image)", image };
    setMsgs((m) => [...m, userMsg]);
    setBusy(true);
    const imgToSend = image;
    setImage(null);
    try {
      const { data } = await api.post("/ai/chat", {
        message, session_id: session, image_base64: imgToSend,
      });
      setMsgs((m) => [...m, { role: "assistant", text: data.reply, changed: data.changed }]);
      if (data.changed) { refreshAll(); }
    } catch (e) {
      setMsgs((m) => [...m, { role: "assistant", text: "Sorry, I couldn't process that. Please try again." }]);
      toast.error("AI request failed");
    } finally {
      setBusy(false);
    }
  };

  const pickImage = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => setImage(reader.result);
    reader.readAsDataURL(f);
  };

  const toggleRecord = async () => {
    if (recording) {
      recRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks = [];
      rec.ondataavailable = (e) => chunks.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        const blob = new Blob(chunks, { type: "audio/webm" });
        const fd = new FormData();
        fd.append("file", blob, "audio.webm");
        setBusy(true);
        try {
          const { data } = await api.post("/ai/transcribe", fd);
          if (data.text) { setInput(data.text); send(data.text); }
        } catch { toast.error("Could not transcribe audio"); }
        finally { setBusy(false); }
      };
      recRef.current = rec;
      rec.start();
      setRecording(true);
    } catch {
      toast.error("Microphone access denied");
    }
  };

  return (
    <>
      <button data-testid="ai-fab" onClick={() => setOpen(true)}
        className="fixed z-40 bottom-20 right-4 lg:bottom-6 lg:right-6 h-14 w-14 rounded-full glass-strong border border-slate-300/50 dark:border-slate-700/60 grid place-items-center shadow-2xl pulse-ring">
        <Sparkles className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setOpen(false)} className="fixed inset-0 z-40 bg-slate-950/30 backdrop-blur-[2px]" />
            <motion.div data-testid="ai-panel" initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="fixed z-50 inset-y-0 right-0 w-full sm:w-[440px] glass-strong border-l border-border flex flex-col">
              <div className="h-16 flex items-center gap-3 px-5 border-b border-border">
                <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 grid place-items-center text-white"><Sparkles className="h-4 w-4" /></div>
                <div>
                  <p className="font-bold tracking-tight leading-none">Assistant</p>
                  <p className="text-xs text-slate-500 mt-0.5">Type, speak or snap a receipt</p>
                </div>
                <button data-testid="ai-close" onClick={() => setOpen(false)} className="ml-auto h-9 w-9 grid place-items-center rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="flex gap-1 px-4 pt-3">
                {[["chat", "Chat", MessageSquare], ["activity", "Activity", History]].map(([k, l, Ic]) => (
                  <button key={k} data-testid={`ai-tab-${k}`} onClick={() => setTab(k)}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${tab === k ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100" : "text-slate-500"}`}>
                    <Ic className="h-3.5 w-3.5" />{l}
                  </button>
                ))}
              </div>

              <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                {tab === "activity" ? (
                  <div className="space-y-2" data-testid="activity-feed">
                    {actions.length === 0 ? (
                      <p className="text-sm text-slate-500 pt-6 text-center">No AI activity yet. Ask me to add or change something.</p>
                    ) : actions.map((a) => (
                      <div key={a.id} data-testid={`activity-${a.id}`} className="rounded-xl border border-border bg-card p-3">
                        <div className="flex items-start gap-2">
                          <div className="mt-0.5 h-6 w-6 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 grid place-items-center shrink-0"><Sparkles className="h-3 w-3 text-emerald-600" /></div>
                          <div className="flex-1 min-w-0">
                            <p className="text-[11px] text-slate-400">{new Date(a.created_at).toLocaleString()}</p>
                            <p className="text-sm mt-0.5">{a.label}</p>
                            {a.tools?.length > 0 && <p className="text-[11px] text-slate-400 mt-1">{a.tools.join(", ")}</p>}
                          </div>
                        </div>
                        {a.undoable && !a.undone && (
                          <button onClick={() => undoAction(a.id)} data-testid={`undo-${a.id}`} className="mt-2 text-xs font-medium text-emerald-700 dark:text-emerald-300 inline-flex items-center gap-1 hover:underline"><Undo2 className="h-3 w-3" />Undo</button>
                        )}
                        {a.undone && <span className="mt-2 inline-block text-xs text-slate-400">✓ Undone</span>}
                      </div>
                    ))}
                  </div>
                ) : (<>
                {msgs.length === 0 && (
                  <div className="pt-6">
                    <p className="text-sm text-slate-500 mb-3">Try one of these</p>
                    <div className="grid gap-2">
                      {SUGGESTIONS.map((s) => (
                        <button key={s} data-testid="ai-suggestion" onClick={() => send(s)}
                          className="text-left text-sm rounded-xl border border-border bg-card px-3.5 py-2.5 hover:border-emerald-400 hover:bg-emerald-50/50 dark:hover:bg-emerald-500/10 transition-colors">
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {msgs.map((m, i) => (
                  <div key={i} className={m.role === "user" ? "flex justify-end" : "flex gap-2.5"}>
                    {m.role === "assistant" && <Avatar name="AI" size="h-7 w-7" />}
                    <div className={m.role === "user"
                      ? "max-w-[80%] rounded-2xl rounded-br-md bg-emerald-600 text-white px-3.5 py-2.5 text-sm"
                      : "max-w-[85%] rounded-2xl rounded-bl-md bg-card border border-border px-3.5 py-2.5 text-sm whitespace-pre-wrap"}>
                      {m.image && <img src={m.image} alt="upload" className="rounded-lg mb-2 max-h-40" />}
                      {m.text}
                      {m.changed && <div className="mt-1.5 text-[11px] text-emerald-700 dark:text-emerald-300 font-medium">✓ Your data was updated</div>}
                    </div>
                  </div>
                ))}
                {busy && (
                  <div className="flex gap-2.5">
                    <Avatar name="AI" size="h-7 w-7" />
                    <div className="rounded-2xl rounded-bl-md bg-card border border-border px-3.5 py-2.5 text-sm text-slate-500 flex items-center gap-2">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Working on it…
                    </div>
                  </div>
                )}
                </>)}
              </div>

              <div className="border-t border-border p-3" style={{ display: tab === "chat" ? "block" : "none" }}>
                {image && (
                  <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
                    <img src={image} alt="preview" className="h-10 w-10 rounded-lg object-cover" />
                    Image attached
                    <button onClick={scanReceipt} disabled={scanning} data-testid="ai-scan-receipt" className="rounded-lg bg-emerald-600 text-white px-2.5 py-1 font-medium inline-flex items-center gap-1 hover:bg-emerald-700 disabled:opacity-50">
                      <ScanLine className="h-3.5 w-3.5" />{scanning ? "Reading…" : "Scan receipt"}
                    </button>
                    <button onClick={() => setImage(null)} className="ml-auto text-slate-400 hover:text-slate-600"><X className="h-3.5 w-3.5" /></button>
                  </div>
                )}
                <div className="flex items-end gap-2">
                  <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={pickImage} data-testid="ai-file-input" />
                  <button data-testid="ai-attach" onClick={() => fileRef.current?.click()} className="h-10 w-10 shrink-0 grid place-items-center rounded-xl border border-border hover:bg-slate-100 dark:hover:bg-slate-800">
                    <Paperclip className="h-4 w-4" />
                  </button>
                  <button data-testid="ai-mic" onClick={toggleRecord}
                    className={`h-10 w-10 shrink-0 grid place-items-center rounded-xl border transition-colors ${recording ? "bg-red-500 border-red-500 text-white" : "border-border hover:bg-slate-100 dark:hover:bg-slate-800"}`}>
                    {recording ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                  </button>
                  <textarea data-testid="ai-input" value={input} onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                    rows={1} placeholder="Ask Life Manager…"
                    className="flex-1 resize-none rounded-xl border border-border bg-card px-3 py-2.5 text-sm outline-none focus:border-emerald-400 max-h-28" />
                  <button data-testid="ai-send" onClick={() => send()} disabled={busy}
                    className="h-10 w-10 shrink-0 grid place-items-center rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-50">
                    <Send className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      <ReceiptReview data={receiptData} open={receiptOpen} setOpen={setReceiptOpen} />
    </>
  );
}
