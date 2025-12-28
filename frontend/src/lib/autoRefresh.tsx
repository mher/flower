import type { FC, PropsWithChildren } from "react";
import { createContext, useCallback, useContext, useMemo } from "react";
import { useLocalStorageState } from "./useLocalStorageState";

export type AutoRefreshOption = {
  label: "Off" | "5s" | "15s" | "30s" | "1m" | "5m";
  intervalMs: number;
};

export const AUTO_REFRESH_OPTIONS: readonly AutoRefreshOption[] = [
  { label: "Off", intervalMs: 0 },
  { label: "5s", intervalMs: 5_000 },
  { label: "15s", intervalMs: 15_000 },
  { label: "30s", intervalMs: 30_000 },
  { label: "1m", intervalMs: 60_000 },
  { label: "5m", intervalMs: 300_000 },
] as const;

const AUTO_REFRESH_STORAGE_KEY = "flower:autoRefreshLabel";

type AutoRefreshContextValue = {
  option: AutoRefreshOption;
  setOption: (next: AutoRefreshOption) => void;
};

const AutoRefreshContext = createContext<AutoRefreshContextValue | null>(null);

export const AutoRefreshProvider: FC<PropsWithChildren> = ({ children }) => {
  const [label, setLabel] = useLocalStorageState<AutoRefreshOption["label"]>(
    AUTO_REFRESH_STORAGE_KEY,
    AUTO_REFRESH_OPTIONS[0].label,
    {
      validate: (v) => AUTO_REFRESH_OPTIONS.some((opt) => opt.label === v),
    }
  );

  const option = useMemo<AutoRefreshOption>(
    () =>
      AUTO_REFRESH_OPTIONS.find((opt) => opt.label === label) ??
      AUTO_REFRESH_OPTIONS[0],
    [label]
  );

  const setOption = useCallback(
    (next: AutoRefreshOption) => {
      setLabel(next.label);
    },
    [setLabel]
  );

  const value = useMemo<AutoRefreshContextValue>(
    () => ({ option, setOption }),
    [option]
  );

  return (
    <AutoRefreshContext.Provider value={value}>
      {children}
    </AutoRefreshContext.Provider>
  );
};

export function useAutoRefresh(): AutoRefreshContextValue {
  const value = useContext(AutoRefreshContext);
  if (!value) {
    throw new Error("useAutoRefresh must be used within AutoRefreshProvider");
  }
  return value;
}
