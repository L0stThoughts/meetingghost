"use client";

const SPEAKER_COLORS: Record<string, string> = {
  "Speaker 1": "bg-blue-100 text-blue-800 border-blue-300",
  "Speaker 2": "bg-green-100 text-green-800 border-green-300",
  "Speaker 3": "bg-purple-100 text-purple-800 border-purple-300",
  "Speaker 4": "bg-orange-100 text-orange-800 border-orange-300",
  "Speaker 5": "bg-pink-100 text-pink-800 border-pink-300",
};

function getSpeakerColor(speaker: string): string {
  return SPEAKER_COLORS[speaker] || "bg-gray-100 text-gray-800 border-gray-300";
}

function formatTimestamp(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

interface Segment {
  speaker: string | null;
  start_time: number | null;
  end_time: number | null;
  text: string;
}

interface TranscriptViewProps {
  segments: Segment[];
}

export default function TranscriptView({ segments }: TranscriptViewProps) {
  if (!segments.length) {
    return <p className="text-gray-400 text-sm">No transcript available.</p>;
  }

  return (
    <div className="space-y-3">
      {segments.map((seg, i) => {
        const speaker = seg.speaker || "Speaker";
        const color = getSpeakerColor(speaker);
        return (
          <div key={i} className="flex gap-3">
            <div className="flex-shrink-0 w-14 text-xs text-gray-400 pt-1 font-mono text-right">
              {formatTimestamp(seg.start_time)}
            </div>
            <div className="flex-1">
              <span className={`inline-block text-xs px-2 py-0.5 rounded-full border mb-1 ${color}`}>
                {speaker}
              </span>
              <p className="text-sm text-gray-800 leading-relaxed">{seg.text}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
