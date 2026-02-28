import React from "react";
import { formatDistanceToNow } from "date-fns";
import { Clock, ExternalLink } from "lucide-react";

export interface HistoryItem {
    id: number;
    source_url: string | null;
    summary_preview: string;
    label: "REAL" | "FAKE";
    score: number;
    analyzed_at: string;
}

interface HistoryTableProps {
    items: HistoryItem[];
    onSelect: (item: HistoryItem) => void;
}

export function HistoryTable({ items, onSelect }: HistoryTableProps) {
    if (!items || !Array.isArray(items) || items.length === 0) {
        return (
            <div className="flex flex-col flex-1 items-center justify-center p-8 text-center text-slate-400">
                <Clock className="w-12 h-12 mb-4 opacity-20" />
                <p>No recent searches.</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col space-y-4 pt-2">
            {items.map((item) => {
                const fakePercent = Math.round(item.score * 100);
                const isFake = item.label === "FAKE";

                const badgeBg = isFake ? "bg-red-50" : "bg-emerald-50";
                const badgeText = isFake ? "text-red-700" : "text-emerald-700";
                const badgeBorder = isFake ? "border-red-200" : "border-emerald-200";

                // Truncate text for preview
                const previewText = item.summary_preview?.length > 80 ? item.summary_preview.slice(0, 80) + "..." : item.summary_preview;

                return (
                    <div
                        key={item.id}
                        onClick={() => onSelect(item)}
                        className="group flex flex-col p-4 bg-white border rounded-xl shadow-sm hover:shadow hover:border-slate-300 transition-all cursor-pointer relative"
                    >
                        <div className="flex justify-between items-start mb-2">
                            <div
                                className={`text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${badgeBg} ${badgeText} ${badgeBorder}`}
                            >
                                {item.label} ({fakePercent}% FAKE)
                            </div>
                            <span className="text-xs text-slate-400 whitespace-nowrap ml-2">
                                {formatDistanceToNow(new Date(item.analyzed_at), { addSuffix: true })}
                            </span>
                        </div>

                        <p className="text-sm text-slate-600 line-clamp-2 leading-relaxed">
                            {previewText}
                        </p>

                        {item.source_url && (
                            <div className="mt-3 flex items-center gap-1.5 text-xs text-blue-500 hover:text-blue-700">
                                <ExternalLink size={14} />
                                <span className="truncate max-w-[200px]">{item.source_url}</span>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
