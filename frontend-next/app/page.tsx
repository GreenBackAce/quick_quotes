'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic,
  UploadCloud,
  FileText,
  MessageSquare,
  BarChart3,
  Play,
  Pause,
  ChevronRight,
  Search,
  MoreVertical,
  CheckCircle2,
  Clock,
  Sparkles,
  Loader2,
  Trash2,
  StopCircle,
  X
} from 'lucide-react';

// --- Types ---

interface Meeting {
  id: string;
  title: string;
  created_at: string;
  status?: string;
  transcript_count?: number;
  has_summary?: boolean;
}

interface TranscriptSegment {
  speaker: string;
  text: string;
  timestamp: number;
  start_time: number;
  relative_time: string;
}

interface Analytics {
  talk_time: Record<string, number>;
  sentiment: {
    overall: string;
    score: number;
    explanation?: string;
  };
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

// --- Components ---

const SidebarLink = ({ icon: Icon, label, active, onClick }: { icon: any, label: string, active: boolean, onClick: () => void }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-3 w-full p-3 rounded-xl transition-all ${active
      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/20'
      : 'text-slate-400 hover:bg-slate-800 hover:text-white'
      }`}
  >
    <Icon size={18} />
    <span className="font-medium text-sm">{label}</span>
  </button>
);

const TranscriptBubble = ({ speaker, relative_time, text }: TranscriptSegment) => {
  const isHost = speaker.toLowerCase().includes('0') || speaker.toLowerCase().includes('a');

  return (
    <div className={`flex gap-4 mb-6`}>
      <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold ${isHost ? 'bg-indigo-500/20 text-indigo-400' : 'bg-emerald-500/20 text-emerald-400'
        }`}>
        {speaker.split(' ').length > 1 ? speaker.split(' ')[1] : speaker.substring(0, 2)}
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-3 mb-1">
          <span className="text-sm font-semibold text-slate-200">{speaker}</span>
          <span className="text-xs text-slate-500">{relative_time}</span>
        </div>
        <p className="text-slate-300 leading-relaxed text-sm">{text}</p>
      </div>
    </div>
  );
};

export default function MeetingDashboard() {
  const [activeTab, setActiveTab] = useState("Transcript"); // Transcript, Summary, Chat, Analytics
  const [isUploading, setIsUploading] = useState(false);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [currentMeeting, setCurrentMeeting] = useState<Meeting | null>(null);
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [summary, setSummary] = useState<string | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Chat State
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Analytics State
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [isAnalyticsLoading, setIsAnalyticsLoading] = useState(false);

  // Recording State
  const [isRecording, setIsRecording] = useState(false);
  const [recordingMeetingId, setRecordingMeetingId] = useState<string | null>(null);
  const [recordingDuration, setRecordingDuration] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const API_BASE = 'http://localhost:8000';

  // --- Effects ---

  useEffect(() => {
    fetchMeetings();
  }, []);

  useEffect(() => {
    if (currentMeeting) {
      fetchMeetingDetails(currentMeeting.id);
      // Reset tab states
      setChatHistory([]);
      setAnalytics(null);
    }
  }, [currentMeeting]);

  // Recording timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);
    } else {
      setRecordingDuration(0);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  // --- API Calls ---

  const fetchMeetings = async () => {
    try {
      const res = await fetch(`${API_BASE}/meetings`);
      const data = await res.json();
      const sorted = (data.meetings || []).sort((a: Meeting, b: Meeting) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setMeetings(sorted);
      if (sorted.length > 0 && !currentMeeting) {
        setCurrentMeeting(sorted[0]);
      }
    } catch (err) {
      console.error("Failed to fetch meetings:", err);
    }
  };

  const fetchMeetingDetails = async (id: string) => {
    setIsLoadingDetails(true);
    setTranscript([]);
    setSummary(null);

    try {
      const res = await fetch(`${API_BASE}/meetings/${id}/transcript`);
      if (!res.ok) throw new Error("Failed to fetch transcript");
      const data = await res.json();
      setTranscript(data.transcript || []);
      setSummary(data.summary);
    } catch (err) {
      console.error("Failed to fetch details:", err);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const deleteMeeting = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent selecting the meeting
    if (!confirm("Are you sure you want to delete this meeting?")) return;

    try {
      const res = await fetch(`${API_BASE}/meetings/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setMeetings(prev => prev.filter(m => m.id !== id));
        if (currentMeeting?.id === id) {
          setCurrentMeeting(null);
          setTranscript([]);
          setSummary(null);
        }
      }
    } catch (err) {
      console.error("Failed to delete meeting:", err);
    }
  };

  const startRecording = async () => {
    try {
      const res = await fetch(`${API_BASE}/meetings/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meeting_title: `Meeting ${new Date().toLocaleString()}` })
      });

      if (res.ok) {
        const data = await res.json();
        setIsRecording(true);
        setRecordingMeetingId(data.meeting_id);
      }
    } catch (err) {
      console.error("Failed to start recording:", err);
      alert("Failed to start recording. Is the backend running?");
    }
  };

  const stopRecording = async () => {
    if (!recordingMeetingId) return;

    try {
      const res = await fetch(`${API_BASE}/meetings/${recordingMeetingId}/stop`, {
        method: 'POST'
      });

      if (res.ok) {
        setIsRecording(false);
        setRecordingMeetingId(null);
        // Refresh meetings and select the new one
        await fetchMeetings();
        // Ideally we'd find the new meeting and select it, but fetchMeetings sorts by date so it should be first
        // We can force select it if we want, but let's just let the user see it in the list
      }
    } catch (err) {
      console.error("Failed to stop recording:", err);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;

    const file = e.target.files[0];
    const formData = new FormData();
    formData.append('file', file);

    setIsUploading(true);
    try {
      const res = await fetch(`${API_BASE}/meetings/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");

      const data = await res.json();
      await fetchMeetings();

      // Select the new meeting
      const meetingsRes = await fetch(`${API_BASE}/meetings`);
      const meetingsData = await meetingsRes.json();
      const sorted = (meetingsData.meetings || []).sort((a: Meeting, b: Meeting) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setMeetings(sorted);
      const uploaded = sorted.find((m: Meeting) => m.id === data.meeting_id);
      if (uploaded) setCurrentMeeting(uploaded);

    } catch (err) {
      console.error("Upload error:", err);
      alert("Failed to upload file");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentMeeting || !chatQuestion.trim()) return;

    const question = chatQuestion;
    setChatQuestion("");
    setChatHistory(prev => [...prev, { role: 'user', content: question }]);
    setIsChatLoading(true);

    try {
      const res = await fetch(`${API_BASE}/meetings/${currentMeeting.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      setChatHistory(prev => [...prev, { role: 'assistant', content: data.answer }]);
    } catch (err) {
      console.error("Chat error:", err);
      setChatHistory(prev => [...prev, { role: 'assistant', content: "Sorry, I couldn't get an answer at this time." }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    if (!currentMeeting) return;
    setIsAnalyticsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/meetings/${currentMeeting.id}/analytics`);
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (err) {
      console.error("Analytics error:", err);
    } finally {
      setIsAnalyticsLoading(false);
    }
  };

  // Fetch analytics when tab is selected
  useEffect(() => {
    if (activeTab === 'Analytics' && currentMeeting && !analytics) {
      fetchAnalytics();
    }
  }, [activeTab, currentMeeting]);

  const handleExport = async () => {
    if (!currentMeeting) return;
    try {
      const res = await fetch(`${API_BASE}/meetings/${currentMeeting.id}/export`);
      const data = await res.json();

      const blob = new Blob([data.content], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Export failed", err);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30 overflow-hidden">

      {/* Sidebar */}
      <aside className="w-72 border-r border-slate-800 bg-slate-900/50 backdrop-blur-xl p-5 flex flex-col">
        <div className="flex items-center gap-2 mb-8 px-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white">
            <Mic size={18} />
          </div>
          <span className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
            QuickQuotes
          </span>
        </div>

        <div className="space-y-1">
          <SidebarLink icon={FileText} label="All Meetings" active={true} onClick={() => { }} />
        </div>

        <div className="mt-8 flex-1 overflow-y-auto custom-scrollbar">
          <h3 className="text-xs font-semibold text-slate-500 uppercase px-3 mb-2">Recent</h3>
          <div className="space-y-1">
            {meetings.map(m => (
              <div
                key={m.id}
                onClick={() => setCurrentMeeting(m)}
                className={`group w-full text-left px-3 py-2 rounded-lg transition-colors cursor-pointer relative ${currentMeeting?.id === m.id ? 'bg-white/10 text-white' : 'hover:bg-white/5 text-slate-300'
                  }`}
              >
                <div className="text-sm font-medium truncate pr-6">{m.title}</div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-xs text-slate-500">{new Date(m.created_at).toLocaleDateString()}</span>
                </div>

                <button
                  onClick={(e) => deleteMeeting(m.id, e)}
                  className="absolute right-2 top-2 p-1 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Delete Meeting"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {meetings.length === 0 && (
              <div className="px-3 py-4 text-xs text-slate-500 text-center italic">
                No meetings found. Upload one to get started!
              </div>
            )}
          </div>
        </div>

        <div className="mt-auto pt-6 border-t border-slate-800">
          {isRecording ? (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex flex-col items-center animate-pulse">
              <div className="text-red-400 font-bold mb-2">Recording...</div>
              <div className="text-2xl font-mono text-white mb-4">{formatTime(recordingDuration)}</div>
              <button
                onClick={stopRecording}
                className="w-full bg-red-600 hover:bg-red-500 text-white py-2 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
              >
                <StopCircle size={18} /> Stop
              </button>
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={startRecording}
                className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white py-3 rounded-xl font-medium flex items-center justify-center gap-2 transition-colors shadow-lg shadow-indigo-900/20"
              >
                <Mic size={18} /> Record
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="flex-1 bg-slate-800 hover:bg-slate-700 text-white py-3 rounded-xl font-medium flex items-center justify-center gap-2 transition-colors"
              >
                {isUploading ? <Loader2 size={18} className="animate-spin" /> : <UploadCloud size={18} />} Upload
              </button>
            </div>
          )}
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            onChange={handleFileUpload}
            accept="audio/*"
          />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative overflow-hidden">

        {/* Top Header */}
        <header className="h-16 border-b border-slate-800 flex justify-between items-center px-6 bg-slate-900/30 backdrop-blur-sm">
          <h2 className="font-semibold text-white truncate max-w-md">
            {currentMeeting ? currentMeeting.title : "Select a meeting"}
          </h2>
          <div className="flex items-center gap-4">
            {currentMeeting && (
              <>
                <button
                  onClick={handleExport}
                  className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-colors"
                >
                  Export Notes
                </button>
              </>
            )}
          </div>
        </header>

        {/* Content Grid */}
        <div className="flex-1 flex overflow-hidden">

          {/* Left: Transcript / Media Player */}
          <section className="flex-1 flex flex-col border-r border-slate-800 relative">

            {isLoadingDetails ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <Loader2 className="animate-spin text-indigo-500" size={32} />
              </div>
            ) : !currentMeeting ? (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-4">
                <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center">
                  <Mic size={32} className="opacity-50" />
                </div>
                <p>Select a meeting to view details or start a new recording</p>
              </div>
            ) : (
              <>
                {/* Audio Waveform Placeholder (Visual Only for now as backend doesn't serve audio) */}
                <div className="h-24 border-b border-slate-800 bg-slate-900/20 p-4 flex items-center justify-center relative">
                  <div className="text-slate-500 text-sm flex items-center gap-2">
                    <Play size={16} /> Audio playback unavailable for archived meetings
                  </div>
                </div>

                {/* Transcript Scroll Area */}
                <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                  <div className="max-w-3xl mx-auto">
                    {transcript.length > 0 ? (
                      transcript.map((t, i) => (
                        <TranscriptBubble key={i} {...t} />
                      ))
                    ) : (
                      <div className="text-center text-slate-500 mt-10">
                        No transcript available yet. It might be processing.
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </section>

          {/* Right: Intelligence Panel */}
          <aside className="w-96 bg-slate-900/20 flex flex-col border-l border-slate-800">
            {/* Tabs */}
            <div className="flex border-b border-slate-800">
              {['Transcript', 'Summary', 'Chat', 'Analytics'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 py-3 text-xs font-medium transition-colors relative ${activeTab === tab ? 'text-white' : 'text-slate-500 hover:text-slate-300'
                    }`}
                >
                  {tab}
                  {activeTab === tab && (
                    <motion.div layoutId="tab-indicator" className="absolute bottom-0 left-0 w-full h-0.5 bg-indigo-500" />
                  )}
                </button>
              ))}
            </div>

            <div className="flex-1 p-6 overflow-y-auto">
              <AnimatePresence mode="wait">
                {activeTab === 'Summary' && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="space-y-6"
                  >
                    {isLoadingDetails ? (
                      <div className="flex justify-center py-10"><Loader2 className="animate-spin text-slate-500" /></div>
                    ) : summary ? (
                      <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                        <h4 className="text-indigo-400 text-xs font-bold uppercase tracking-wider mb-2">AI Summary</h4>
                        <div className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                          {summary}
                        </div>
                      </div>
                    ) : (
                      <div className="text-center text-slate-500 py-10">No summary available.</div>
                    )}
                  </motion.div>
                )}

                {activeTab === 'Chat' && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="h-full flex flex-col"
                  >
                    <div className="flex-1 overflow-y-auto mb-4 space-y-4">
                      {chatHistory.length === 0 ? (
                        <div className="text-center flex flex-col items-center justify-center text-slate-500 h-full">
                          <Sparkles size={32} className="mb-3 opacity-50" />
                          <p className="text-sm">Ask Gemini about this meeting.</p>
                        </div>
                      ) : (
                        chatHistory.map((msg, idx) => (
                          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[85%] p-3 rounded-xl text-sm ${msg.role === 'user'
                                ? 'bg-indigo-600 text-white rounded-br-none'
                                : 'bg-slate-800 text-slate-300 rounded-bl-none'
                              }`}>
                              {msg.content}
                            </div>
                          </div>
                        ))
                      )}
                      {isChatLoading && (
                        <div className="flex justify-start">
                          <div className="bg-slate-800 p-3 rounded-xl rounded-bl-none">
                            <Loader2 size={16} className="animate-spin text-slate-400" />
                          </div>
                        </div>
                      )}
                    </div>

                    <form onSubmit={handleChatSubmit} className="relative mt-auto">
                      <input
                        type="text"
                        value={chatQuestion}
                        onChange={(e) => setChatQuestion(e.target.value)}
                        placeholder="Ask a question..."
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg py-3 pl-4 pr-10 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                        disabled={isChatLoading || !currentMeeting}
                      />
                      <button
                        type="submit"
                        disabled={isChatLoading || !currentMeeting}
                        className="absolute right-2 top-2 p-1 bg-indigo-600 rounded text-white hover:bg-indigo-500 disabled:opacity-50"
                      >
                        <ChevronRight size={16} />
                      </button>
                    </form>
                  </motion.div>
                )}

                {activeTab === 'Analytics' && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="space-y-6"
                  >
                    {isAnalyticsLoading ? (
                      <div className="flex justify-center py-10"><Loader2 className="animate-spin text-slate-500" /></div>
                    ) : analytics ? (
                      <>
                        {/* Talk Time */}
                        <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                          <h4 className="text-indigo-400 text-xs font-bold uppercase tracking-wider mb-4">Talk Time</h4>
                          <div className="space-y-3">
                            {Object.entries(analytics.talk_time).map(([speaker, percentage]) => (
                              <div key={speaker}>
                                <div className="flex justify-between text-xs text-slate-400 mb-1">
                                  <span>{speaker}</span>
                                  <span>{percentage.toFixed(1)}%</span>
                                </div>
                                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-indigo-500 rounded-full"
                                    style={{ width: `${percentage}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Sentiment */}
                        <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                          <h4 className="text-emerald-400 text-xs font-bold uppercase tracking-wider mb-4">Sentiment</h4>
                          <div className="flex items-center justify-between mb-4">
                            <span className="text-slate-300 text-sm">Overall Tone</span>
                            <span className="text-white font-medium capitalize">{analytics.sentiment.overall}</span>
                          </div>

                          <div className="mb-2 flex justify-between text-xs text-slate-500">
                            <span>Negative</span>
                            <span>Positive</span>
                          </div>
                          <div className="h-2 bg-slate-700 rounded-full overflow-hidden mb-4">
                            <div
                              className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-emerald-500"
                              style={{
                                width: '100%',
                                maskImage: `linear-gradient(to right, transparent 0%, black ${((analytics.sentiment.score + 1) / 2) * 100}%, transparent ${((analytics.sentiment.score + 1) / 2) * 100 + 2}%)`,
                                WebkitMaskImage: `linear-gradient(to right, transparent 0%, black ${((analytics.sentiment.score + 1) / 2) * 100}%, transparent ${((analytics.sentiment.score + 1) / 2) * 100 + 2}%)`
                              }}
                            />
                            {/* Simple marker approach instead of complex mask */}
                            <div className="relative h-full w-full -mt-2">
                              <div
                                className="absolute top-0 h-full w-1 bg-white shadow-[0_0_10px_rgba(255,255,255,0.8)]"
                                style={{ left: `${((analytics.sentiment.score + 1) / 2) * 100}%` }}
                              />
                            </div>
                          </div>

                          {analytics.sentiment.explanation && (
                            <p className="text-xs text-slate-400 italic mt-2">
                              "{analytics.sentiment.explanation}"
                            </p>
                          )}
                        </div>
                      </>
                    ) : (
                      <div className="text-center text-slate-500 py-10">No analytics data available.</div>
                    )}
                  </motion.div>
                )}

                {activeTab === 'Transcript' && (
                  <div className="text-center text-slate-500 text-sm mt-10">
                    Select a segment on the left to view details here.
                  </div>
                )}
              </AnimatePresence>
            </div>
          </aside>
        </div>

      </main>
    </div>
  );
}
