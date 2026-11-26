import { X } from "lucide-react";
import { useState } from "react";

import { Input } from "@/components/ui/input";

/** Free-text tags: type and press Enter or comma; click a tag to remove it. */
export function TagInput({ values, onChange, placeholder, max, label }: { values: string[]; onChange: (v: string[]) => void; placeholder: string; max: number; label: string }) {
  const [text, setText] = useState("");
  function add() {
    const value = text.trim().replace(/\s+/g, " ");
    if (value && values.length < max && !values.some((v) => v.toLowerCase() === value.toLowerCase())) onChange([...values, value]);
    setText("");
  }
  return (
    <div className="space-y-2">
      <Input
        value={text}
        placeholder={values.length >= max ? `Up to ${max}` : placeholder}
        disabled={values.length >= max}
        aria-label={label}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            add();
          }
        }}
        onBlur={add}
      />
      {values.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {values.map((v) => (
            <button key={v} type="button" onClick={() => onChange(values.filter((x) => x !== v))} className="inline-flex min-h-8 items-center gap-1 rounded-full bg-lavender-soft px-3 py-1.5 text-xs font-medium text-plum hover:bg-lavender/60" aria-label={`Remove ${v}`}>
              {v} <X className="size-3" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
