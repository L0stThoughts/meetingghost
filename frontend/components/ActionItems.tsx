"use client";

interface ActionItem {
  description: string;
  assignee: string | null;
  due_date: string | null;
  priority: "high" | "medium" | "low";
}

interface ActionItemsProps {
  items: ActionItem[];
}

const PRIORITY_STYLES: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-green-100 text-green-700",
};

export default function ActionItems({ items }: ActionItemsProps) {
  if (!items.length) {
    return <p className="text-gray-400 text-sm">No action items extracted.</p>;
  }

  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-gray-900">Action Items ({items.length})</h3>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="bg-white border border-gray-200 rounded-lg p-3">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm text-gray-800 flex-1">{item.description}</p>
              <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${PRIORITY_STYLES[item.priority] || PRIORITY_STYLES.medium}`}>
                {item.priority}
              </span>
            </div>
            <div className="flex gap-4 mt-2 text-xs text-gray-500">
              {item.assignee && <span>👤 {item.assignee}</span>}
              {item.due_date && <span>📅 {item.due_date}</span>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
