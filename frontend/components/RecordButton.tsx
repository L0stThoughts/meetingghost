"use client";

import { useState, useEffect, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RecordButtonProps {
  onComplete?: () => void;
}

export default function RecordButton({ onComplete }: RecordButtonProps) {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (recording) {
      const start = Date.now();
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - start) / 1000));
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setElapsed(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [recording]);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  const handleClick = async () => {
    if (processing) return;

    if (!recording) {
      try {
        await fetch(`${API}/record/start`, { method: "POST" });
        setRecording(true);
      } catch {
        alert("Failed to start recording");
      }
    } else {
      setRecording(false);
      setProcessing(true);
      try {
        const res = await fetch(`${API}/record/stop`, { method: "POST" });
        const data = await res.json();
        if (data.meeting_id) {
          // Poll for completion
          const poll = setInterval(async () => {
            try {
              const statusRes = await fetch(`${API}/meetings/${data.meeting_id}`);
              const statusData = await statusRes.json();
              if (statusData.meeting?.status === "complete" || statusData.meeting?.status === "error") {
                clearInterval(poll);
                setProcessing(false);
                onComplete?.();
              }
            } catch {
              clearInterval(poll);
              setProcessing(false);
            }
          }, 2000);
        }
      } catch {
        setProcessing(false);
        alert("Failed to stop recording");
      }
    }
  };

  return (
    <div className="flex items-center gap-3">
      {recording && (
        <span className="text-sm font-mono text-red-600">{formatTime(elapsed)}</span>
      )}
      {processing && (
        <span className="text-sm text-gray-500 animate-pulse">Processing...</span>
      )}
      <button
        onClick={handleClick}
        disabled={processing}
        className={`relative w-12 h-12 rounded-full flex items-center justify-center transition-all ${
          recording
            ? "bg-red-600 animate-pulse shadow-lg shadow-red-300"
            : processing
            ? "bg-gray-400 cursor-not-allowed"
            : "bg-red-500 hover:bg-red-600 shadow-md hover:shadow-lg"
        }`}
      >
        {recording ? (
          <div className="w-4 h-4 bg-white rounded-sm" />
        ) : (
          <div className="w-4 h-4 bg-white rounded-full" />
        )}
      </button>
    </div>
  );
}
