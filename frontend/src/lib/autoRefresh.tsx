import type { FC, PropsWithChildren } from "react";
import { createContext, useContext, useMemo, useState } from "react";

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

type AutoRefreshContextValue = {
  option: AutoRefreshOption;
  setOption: (next: AutoRefreshOption) => void;
};

const AutoRefreshContext = createContext<AutoRefreshContextValue | null>(null);

export const AutoRefreshProvider: FC<PropsWithChildren> = ({ children }) => {
  const [option, setOption] = useState<AutoRefreshOption>(
    AUTO_REFRESH_OPTIONS[0]
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
