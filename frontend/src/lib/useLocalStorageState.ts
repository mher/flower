import { useEffect, useState, type Dispatch, type SetStateAction } from "react";

function canUseLocalStorage(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.localStorage !== "undefined" &&
    window.localStorage !== null
  );
}

function readLocalStorage(key: string): string | null {
  if (!canUseLocalStorage()) return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeLocalStorage(key: string, value: string): void {
  if (!canUseLocalStorage()) return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Ignore write failures (quota, private mode, disabled storage, etc.)
  }
}

type UseLocalStorageStateOptions<T> = {
  serialize?: (value: T) => string;
  deserialize?: (raw: string) => T;
  validate?: (value: T) => boolean;
};

const defaultSerialize = <T>(value: T): string => JSON.stringify(value);
const defaultDeserialize = <T>(raw: string): T => JSON.parse(raw) as T;

export function useLocalStorageState<T>(
  key: string,
  defaultValue: T | (() => T),
  options?: UseLocalStorageStateOptions<T>
): [T, Dispatch<SetStateAction<T>>] {
  const getDefault = (): T =>
    typeof defaultValue === "function"
      ? (defaultValue as () => T)()
      : defaultValue;

  const [state, setState] = useState<T>(() => {
    const raw = readLocalStorage(key);
    if (raw === null) return getDefault();

    try {
      const deserialize = options?.deserialize ?? defaultDeserialize<T>;
      const next = deserialize(raw);
      if (options?.validate && !options.validate(next)) return getDefault();
      return next;
    } catch {
      return getDefault();
    }
  });

  useEffect(() => {
    const serialize = options?.serialize ?? defaultSerialize<T>;
    writeLocalStorage(key, serialize(state));
  }, [key, options?.serialize, state]);

  return [state, setState];
}
