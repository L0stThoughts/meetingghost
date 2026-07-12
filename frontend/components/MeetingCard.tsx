"use client";

import { useRouter } from "next/navigation";

interface MeetingProps {
  meeting: {
    id: number;
    title: string | null;
    created_at: string | null;
    duration_seconds: number | null;
    one_liner: string | null;
    action_items: string | null;
    status: string | null;
  };
}

export default function MeetingCard({ meeting }: MeetingProps) {
  const router = useRouter();

  const formatDuration = (s: number | null) => {
    if (!s) return "--:--";
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}m ${sec}s`;
  };

  const actionCount = (() => {
    if (!meeting.action_items) return 0;
    try {
      return JSON.parse(meeting.action_items).length;
    } catch {
      return 0;
    }
  })();

  const dateStr = meeting.created_at
    ? new Date(meeting.created_at).toLocaleDateString()
    : "";

  return (
    <div
      onClick={() => router.push(`/meetings/${meeting.id}`)}
      className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-gray-900 truncate">
          {meeting.title || `Meeting #${meeting.id}`}
        </h3>
        {meeting.status === "processing" && (
          <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
            Processing
          </span>
        )}
      </div>

      <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
        <span>{dateStr}</span>
        <span>{formatDuration(meeting.duration_seconds)}</span>
      </div>

      {meeting.one_liner && (
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">{meeting.one_liner}</p>
      )}

      {actionCount > 0 && (
        <span className="inline-flex items-center text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
          {actionCount} action item{actionCount !== 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
}
