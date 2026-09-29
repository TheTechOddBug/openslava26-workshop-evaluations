import { useEffect, useState } from "react";

import { useCatalog } from "./hooks/useCatalog";
import { Compare } from "./views/Compare";
import { Datasets } from "./views/Datasets";
import { Ensemble } from "./views/Ensemble";
import { JudgeReliability } from "./views/JudgeReliability";
import { Matrix } from "./views/Matrix";
import { Models } from "./views/Models";
import { Playground } from "./views/Playground";

type Tab = "playground" | "matrix" | "compare" | "ensemble" | "judge" | "datasets" | "models";

const TABS: { id: Tab; label: string }[] = [
  { id: "playground", label: "Playground" },
  { id: "matrix", label: "Matrix" },
  { id: "compare", label: "Compare" },
  { id: "ensemble", label: "Ensemble" },
  { id: "judge", label: "Judge reliability" },
  { id: "datasets", label: "Datasets" },
  { id: "models", label: "Models" },
];

function usePreferredTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  return { theme, setTheme };
}

export function App() {
  const { catalog, error, refresh } = useCatalog();
  const [tab, setTab] = useState<Tab>("playground");
  const { theme, setTheme } = usePreferredTheme();

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar__brand">
          <span className="topbar__title">Evaluation Lab</span>
          <span className="topbar__subtitle">prompts · models · evaluation mechanisms</span>
        </div>
        <div className="topbar__spacer" />
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`tab ${tab === t.id ? "tab--active" : ""}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <button
          className="icon-button"
          title="Toggle light and dark"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? "☾" : "☀"}
        </button>
      </header>

      <main className="content">
        {error && <div className="banner">{error}</div>}
        {!catalog && !error && <p className="muted">Loading catalogue…</p>}
        {catalog && (
          <>
            {tab === "playground" && <Playground catalog={catalog} />}
            {tab === "matrix" && <Matrix catalog={catalog} />}
            {tab === "compare" && <Compare catalog={catalog} />}
            {tab === "ensemble" && <Ensemble catalog={catalog} />}
            {tab === "judge" && <JudgeReliability catalog={catalog} />}
            {tab === "datasets" && <Datasets catalog={catalog} onChange={refresh} />}
            {tab === "models" && <Models onChange={refresh} />}
          </>
        )}
      </main>
    </div>
  );
}
