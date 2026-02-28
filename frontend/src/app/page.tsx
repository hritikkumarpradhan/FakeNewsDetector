"use client";

import React, { useState, useEffect } from "react";
import { CredibilityGauge } from "@/components/CredibilityGauge";
import { SummaryCard } from "@/components/SummaryCard";
import { HistoryTable, HistoryItem } from "@/components/HistoryTable";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";
import { Globe, FileText, Loader2, ShieldCheck, Activity } from "lucide-react";

// The FastAPI backend base URL
const API_BASE = "http://localhost:8000/api";

export default function Home() {
  const [inputType, setInputType] = useState<"url" | "text">("url");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  // Fetch history on load
  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/history?limit=20`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.items || []);
      }
    } catch (e) {
      console.error("Failed to fetch history:", e);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleAnalyze = async () => {
    if (inputType === "url" && !url.trim()) {
      toast.error("Please enter a valid URL.");
      return;
    }
    if (inputType === "text" && text.trim().length < 50) {
      toast.error("Please enter at least 50 characters of text to analyze.");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const payload = inputType === "url" ? { url: url.trim() } : { text: text.trim() };
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Analysis failed.");
      }

      setResult(data);
      toast.success("Analysis complete!");
      fetchHistory(); // Refresh history
    } catch (err: any) {
      toast.error(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const loadHistoryItem = (item: HistoryItem) => {
    setResult({
      label: item.label,
      score: item.score,
      confidence: 1.0, // approx
      model_used: "Historical",
      summary_bullets: [], // If DB had them we would show them, for now we skip or re-summarize
      summary_raw: "",
      text: item.summary_preview,
      url: item.source_url,
      method: "db",
      success: true,
    });
    // Let user know they are viewing a past item
    // toast.info("Viewing historical analysis.");
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row">
      {/* Sidebar: History */}
      <aside className="w-full md:w-80 lg:w-96 bg-white border-r flex flex-col h-screen sticky top-0 md:flex-shrink-0 shadow-sm z-10">
        <div className="p-6 border-b flex items-center gap-3">
          <div className="p-2 bg-blue-600 rounded-lg text-white">
            <ShieldCheck size={24} />
          </div>
          <div>
            <h1 className="font-bold text-xl tracking-tight text-slate-900">TruthLens</h1>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-widest">Fake News Detector</p>
          </div>
        </div>
        <div className="flex-1 overflow-hidden flex flex-col p-4 bg-slate-50/50">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2 px-2 flex items-center gap-2">
            <Activity size={16} />
            Recent Analyses
          </h2>
          <ScrollArea className="flex-1">
            <HistoryTable items={history} onSelect={loadHistoryItem} />
          </ScrollArea>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-6 lg:p-12 overflow-y-auto">
        <div className="max-w-4xl mx-auto space-y-8">

          {/* Header */}
          <header className="mb-10">
            <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Verify the News</h2>
            <p className="text-slate-500 mt-2 text-lg">
              Paste a news article URL or raw text to analyze its credibility and generate an AI summary.
            </p>
          </header>

          {/* Input Section */}
          <Card className="shadow-md border-0 ring-1 ring-slate-200">
            <CardHeader className="bg-white rounded-t-xl border-b pb-4">
              <div className="flex gap-2">
                <Button
                  variant={inputType === "url" ? "default" : "ghost"}
                  onClick={() => setInputType("url")}
                  className="rounded-full px-6"
                >
                  <Globe className="w-4 h-4 mr-2" />
                  Article URL
                </Button>
                <Button
                  variant={inputType === "text" ? "default" : "ghost"}
                  onClick={() => setInputType("text")}
                  className="rounded-full px-6"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Raw Text
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              {inputType === "url" ? (
                <div className="space-y-4">
                  <Input
                    placeholder="https://example.com/news-article"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="text-lg py-6 focus-visible:ring-blue-500"
                    onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
                  />
                  <p className="text-sm text-slate-500 ml-1">
                    Supported sites work best (CNN, BBC, NYT, etc.)
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <Textarea
                    placeholder="Paste the full article text here..."
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    className="min-h-[150px] text-base resize-y focus-visible:ring-blue-500"
                  />
                  <p className="text-sm text-slate-500 ml-1">
                    Minimum 50 characters required.
                  </p>
                </div>
              )}

              <div className="mt-6 flex justify-end">
                <Button
                  size="lg"
                  onClick={handleAnalyze}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 px-8 text-md font-semibold rounded-full shadow-lg shadow-blue-600/20"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Analyzing Models...
                    </>
                  ) : (
                    "Analyze Credibility"
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Results Section */}
          {result && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">

              {/* Gauge Column */}
              <div className="col-span-1">
                <Card className="h-full shadow-md border-0 ring-1 ring-slate-200">
                  <CredibilityGauge score={result.score} className="h-full" />
                </Card>
              </div>

              {/* Summary Column */}
              <div className="col-span-1 lg:col-span-2">
                {result.summary_bullets && result.summary_bullets.length > 0 ? (
                  <SummaryCard
                    bullets={result.summary_bullets}
                    rawSummary={result.summary_raw}
                    modelUsed={result.model_used}
                  />
                ) : (
                  <Card className="w-full h-full shadow-sm">
                    <CardHeader className="bg-slate-50 border-b pb-4 rounded-t-xl">
                      <CardTitle className="text-xl">Analysis Complete</CardTitle>
                      <CardDescription>Article analyzed successfully.</CardDescription>
                    </CardHeader>
                    <CardContent className="pt-6">
                      <Alert className="bg-blue-50 text-blue-800 border-blue-200">
                        <AlertDescription className="text-sm leading-relaxed">
                          {result.text.length > 300 ? result.text.slice(0, 300) + "..." : result.text}
                        </AlertDescription>
                      </Alert>
                      {(!result.summary_bullets || result.summary_bullets.length === 0) && (
                        <div className="mt-6 text-sm text-slate-500 italic">
                          Summary features are not available for this historic record or the text was too short.
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
