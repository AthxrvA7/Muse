import { Loader2, Plus, Search } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";

import { Input } from "@/components/ui/input";

interface Props<T> {
  placeholder: string;
  search: (query: string) => Promise<T[]>;
  render: (item: T) => ReactNode;
  itemKey: (item: T) => string;
  onPick: (item: T) => void;
  label: string;
}

/** Debounced search against the Spotify catalogue (through the Muse API). */
export function SearchBox<T>({ placeholder, search, render, itemKey, onPick, label }: Props<T>) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) return;
    const timer = setTimeout(() => {
      setLoading(true);
      setError(null);
      search(q)
        .then(setResults)
        .catch((e: Error) => setError(e.message))
        .finally(() => setLoading(false));
    }, 350);
    return () => clearTimeout(timer);
  }, [query, search]);

  const showResults = query.trim().length >= 2;

  return (
    <div className="space-y-2">
      <div className="relative">
        <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-ink-soft" />
        <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={placeholder} aria-label={label} className="pl-10" />
        {loading && <Loader2 className="absolute right-4 top-1/2 size-4 -translate-y-1/2 animate-spin text-plum" />}
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
      {showResults && results.length > 0 && (
        <ul className="grid gap-1.5 sm:grid-cols-2">
          {results.map((item) => (
            <li key={itemKey(item)}>
              <button
                type="button"
                onClick={() => {
                  onPick(item);
                  setQuery("");
                  setResults([]);
                }}
                className="flex w-full items-center gap-3 rounded-2xl border border-line bg-surface p-2 text-left transition hover:border-lavender hover:bg-lavender-faint"
              >
                {render(item)}
                <Plus className="ml-auto size-4 shrink-0 text-plum" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
