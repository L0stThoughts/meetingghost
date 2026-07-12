"use client";

import { useEffect, useState } from "react";
import RecordButton from "../components/RecordButton";
import SearchBar from "../components/SearchBar";
import MeetingCard from "../components/MeetingCard";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Meeting {
  id: number;
  title: string | null;
  created_at: string | null;
  duration_seconds: number | null;
  one_liner: string | null;
  action_items: string | null;
  status: string | null;
}

export default function Page() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMeetings = async () => {
    try {
      const res = await fetch(`${API}/meetings`);
      const data = await res.json();
      setMeetings(data);
    } catch {
      console.error("Failed to fetch meetings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMeetings();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">👻 MeetingGhost</h1>
          <RecordButton onComplete={fetchMeetings} />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6">
        <SearchBar />

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading...</div>
        ) : meetings.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-6xl mb-4">👻</div>
            <h2 className="text-xl font-semibold text-gray-700 mb-2">No meetings yet</h2>
            <p className="text-gray-500">
              Click the record button or upload an audio file to get started.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
            {meetings.map((m) => (
              <MeetingCard key={m.id} meeting={m} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
