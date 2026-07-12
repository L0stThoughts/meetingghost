"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SearchResultItem {
  meeting_id: number;
  snippet: string;
  score: number;
  speaker: string | null;
  timestamp: number | null;
}

type SearchMode = "fts" | "semantic" | "hybrid";

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [showResults, setShowResults] = useState(false);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const router = useRouter();

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      setShowResults(false);
      return;
    }
    try {
      const res = await fetch(`${API}/search?q=${encodeURIComponent(q)}&mode=${mode}`);
      const data = await res.json();
      setResults(data);
      setShowResults(true);
    } catch {
      setResults([]);
    }
  }, [mode]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(query), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, doSearch]);

  const modes: SearchMode[] = ["fts", "semantic", "hybrid"];

  return (
    <div className="relative">
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setShowResults(true)}
          placeholder="Search meetings..."
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex rounded-lg border border-gray-300 overflow-hidden">
          {modes.map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-2 text-xs font-medium transition-colors ${
                mode === m ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              {m.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {showResults && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto">
          {results.map((r, i) => (
            <button
              key={i}
              onClick={() => {
                router.push(`/meetings/${r.meeting_id}`);
                setShowResults(false);
              }}
              className="w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-0"
            >
              <div className="flex items-center gap-2 mb-1">
                {r.speaker && (
                  <span className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
                    {r.speaker}
                  </span>
                )}
                <span className="text-xs text-gray-400">Meeting #{r.meeting_id}</span>
                <span className="text-xs text-gray-400 ml-auto">
                  {r.score.toFixed(3)}
                </span>
              </div>
              <p className="text-sm text-gray-700 line-clamp-2">{r.snippet}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
