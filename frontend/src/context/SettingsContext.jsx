import { createContext, useContext, useEffect, useState } from "react";

const SettingsCtx = createContext(null);
export const useSettings = () => useContext(SettingsCtx);

const load = (k, d) => {
  try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); }
  catch { return d; }
};

export function SettingsProvider({ children }) {
  const [theme, setTheme] = useState(() => load("lm_theme", "light"));
  const [animations, setAnimations] = useState(() => load("lm_anim", true));

  useEffect(() => {
    const root = document.documentElement;
    const apply = (t) => {
      if (t === "dark") root.classList.add("dark");
      else if (t === "light") root.classList.remove("dark");
      else {
        const m = window.matchMedia("(prefers-color-scheme: dark)").matches;
        root.classList.toggle("dark", m);
      }
    };
    apply(theme);
    localStorage.setItem("lm_theme", JSON.stringify(theme));
  }, [theme]);

  useEffect(() => {
    document.documentElement.classList.toggle("no-anim", !animations);
    localStorage.setItem("lm_anim", JSON.stringify(animations));
  }, [animations]);

  return (
    <SettingsCtx.Provider value={{ theme, setTheme, animations, setAnimations }}>
      {children}
    </SettingsCtx.Provider>
  );
}
