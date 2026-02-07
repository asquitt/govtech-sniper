"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { Input } from "@/components/ui/input";

interface MentionUser {
  id: number;
  name: string;
}

interface MentionInputProps {
  value: string;
  onChange: (value: string) => void;
  onMentionsChange: (userIds: number[]) => void;
  /** Available users for @mention autocomplete. */
  users: MentionUser[];
  placeholder?: string;
  className?: string;
}

/**
 * Text input with @mention autocomplete. Triggers a dropdown when `@` is typed.
 */
export function MentionInput({
  value,
  onChange,
  onMentionsChange,
  users,
  placeholder = "Type a comment... Use @ to mention",
  className,
}: MentionInputProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [filter, setFilter] = useState("");
  const [mentionedIds, setMentionedIds] = useState<number[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      onChange(val);

      // Check for @ trigger
      const atIdx = val.lastIndexOf("@");
      if (atIdx >= 0 && (atIdx === 0 || val[atIdx - 1] === " ")) {
        const query = val.slice(atIdx + 1);
        if (!query.includes(" ")) {
          setFilter(query.toLowerCase());
          setShowDropdown(true);
          return;
        }
      }
      setShowDropdown(false);
    },
    [onChange]
  );

  const selectUser = useCallback(
    (user: MentionUser) => {
      const atIdx = value.lastIndexOf("@");
      const before = value.slice(0, atIdx);
      const newValue = `${before}@${user.name} `;
      onChange(newValue);
      const next = [...mentionedIds, user.id];
      setMentionedIds(next);
      onMentionsChange(next);
      setShowDropdown(false);
      inputRef.current?.focus();
    },
    [value, onChange, mentionedIds, onMentionsChange]
  );

  const filtered = users.filter(
    (u) => u.name.toLowerCase().includes(filter) && !mentionedIds.includes(u.id)
  );

  // Close dropdown on outside click
  useEffect(() => {
    const close = () => setShowDropdown(false);
    if (showDropdown) {
      document.addEventListener("click", close, { once: true });
    }
  }, [showDropdown]);

  return (
    <div className="relative">
      <Input
        ref={inputRef}
        value={value}
        onChange={handleInput}
        placeholder={placeholder}
        className={className}
      />
      {showDropdown && filtered.length > 0 && (
        <div className="absolute z-50 mt-1 w-full max-h-36 overflow-y-auto rounded-md border border-border bg-popover shadow-md">
          {filtered.map((user) => (
            <button
              key={user.id}
              type="button"
              className="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent"
              onMouseDown={(e) => {
                e.preventDefault();
                selectUser(user);
              }}
            >
              <span className="w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-bold">
                {user.name.charAt(0).toUpperCase()}
              </span>
              {user.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
