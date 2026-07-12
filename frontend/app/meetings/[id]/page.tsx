"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import TranscriptView from "@/components/TranscriptView";
import ActionItems from "@/components/ActionItems";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Segment {
  speaker: string | null;
  start_time: number | null;
  end_time: number | null;
  text: string;
}

interface ActionItem {
  description: string;
  assignee: string | null;
  due_date: string | null;
  priority: "high" | "medium" | "low";
}

interface MeetingDetail {
  meeting: {
    id: number;
    title: string | null;
    created_at: string | null;
    duration_seconds: number | null;
    one_liner: string | null;
    key_points: string | null;
    decisions: string | null;
    action_items: string | null;
    status: string | null;
  };
  transcripts: Segment[];
}

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [data, setData] = useState<MeetingDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMeeting = async () => {
      try {
        const res = await fetch(`${API}/meetings/${params.id}`);
        if (!res.ok) throw new Error("Not found");
        const json = await res.json();
        setData(json);
      } catch {
        console.error("Failed to load meeting");
      } finally {
        setLoading(false);
      }
    };
    fetchMeeting();
  }, [params.id]);

  if (loading) return <div className="p-6 text-gray-400">Loading...</div>;
  if (!data) return <div className="p-6 text-red-500">Meeting not found.</div>;

  const { meeting, transcripts } = data;

  const keyPoints: string[] = (() => {
    try { return meeting.key_points ? JSON.parse(meeting.key_points) : []; } catch { return []; }
  })();
  const decisions: string[] = (() => {
    try { return meeting.decisions ? JSON.parse(meeting.decisions) : []; } catch { return []; }
  })();
  const actionItems: ActionItem[] = (() => {
    try { return meeting.action_items ? JSON.parse(meeting.action_items) : []; } catch { return []; }
  })();

  const formatDuration = (s: number | null) => {
    if (!s) return "";
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}m ${sec}s`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto">
          <button
            onClick={() => router.push("/")}
            className="text-sm text-blue-600 hover:text-blue-800 mb-2 flex items-center gap-1"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-2xl font-bold text-gray-900">
            {meeting.title || `Meeting #${meeting.id}`}
          </h1>
          <div className="flex gap-4 mt-1 text-sm text-gray-500">
            {meeting.created_at && <span>{new Date(meeting.created_at).toLocaleString()}</span>}
            {meeting.duration_seconds && <span>{formatDuration(meeting.duration_seconds)}</span>}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6">
        {/* Summary section */}
        {meeting.one_liner && (
          <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
            <p className="text-gray-800 font-medium">{meeting.one_liner}</p>
          </div>
        )}

        {(keyPoints.length > 0 || decisions.length > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {keyPoints.length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-900 mb-2">Key Points</h3>
                <ul className="space-y-1">
                  {keyPoints.map((p, i) => (
                    <li key={i} className="text-sm text-gray-700 flex gap-2">
                      <span className="text-blue-500">•</span> {p}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {decisions.length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-900 mb-2">Decisions</h3>
                <ul className="space-y-1">
                  {decisions.map((d, i) => (
                    <li key={i} className="text-sm text-gray-700 flex gap-2">
                      <span className="text-green-500">✓</span> {d}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Main content: transcript + action items */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="font-semibold text-gray-900 mb-4">Transcript</h3>
            <TranscriptView segments={transcripts} />
          </div>
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
            <ActionItems items={actionItems} />
          </div>
        </div>
      </main>
    </div>
  );
}
