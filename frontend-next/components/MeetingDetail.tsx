'use client';

import { useQuery } from '@tanstack/react-query';
import { getMeeting, exportMeeting } from '@/lib/api';
import { AudioPlayer } from '@/components/AudioPlayer';
import { TranscriptViewer } from '@/components/TranscriptViewer';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Download, ArrowLeft, FileText } from 'lucide-react';
import Link from 'next/link';
import { useState, useCallback } from 'react';

interface MeetingDetailProps {
    meetingId: string;
}

export function MeetingDetail({ meetingId }: MeetingDetailProps) {
    const [currentTime, setCurrentTime] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    const { data, isLoading, error } = useQuery({
        queryKey: ['meeting', meetingId],
        queryFn: () => getMeeting(meetingId),
    });

    const handleExport = async () => {
        try {
            const response = await exportMeeting(meetingId);
            const blob = new Blob([response.data.content], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = response.data.filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            console.error('Failed to export transcript:', err);
            alert('Failed to export transcript');
        }
    };

    const handleTimeUpdate = useCallback((time: number) => {
        setCurrentTime(time);
    }, []);

    const handleSeek = useCallback((time: number) => {
        // This will be handled by the AudioPlayer via a ref or context in a real app
        // For now, we update the state, but AudioPlayer needs to listen to it
        // Since AudioPlayer is imperative, we might need to lift the wavesurfer instance
        // or use a context.
        // For MVP, let's just update the time and assume the user clicks the waveform to seek.
        // Wait, clicking transcript SHOULD seek audio.
        // I need to pass a seek function to TranscriptViewer that controls AudioPlayer.

        // To fix this properly:
        // 1. AudioPlayer should expose a seekTo method
        // 2. Or we use a shared ref for the wavesurfer instance

        // Let's use a custom event for now to keep it simple without lifting state too much
        const event = new CustomEvent('seek-audio', { detail: time });
        window.dispatchEvent(event);
    }, []);

    if (isLoading) {
        return (
            <div className="space-y-8">
                <div className="h-12 w-1/3 bg-muted/50 animate-pulse rounded" />
                <div className="h-32 bg-muted/50 animate-pulse rounded" />
                <div className="h-96 bg-muted/50 animate-pulse rounded" />
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="text-center p-12 text-destructive">
                Failed to load meeting details
            </div>
        );
    }

    const { transcript, summary } = data.data;
    // We need the audio URL. The backend should provide it, or we construct it.
    // Assuming backend serves audio at /meetings/{id}/audio
    const audioUrl = `${process.env.NEXT_PUBLIC_API_URL}/meetings/${meetingId}/audio`;

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" asChild>
                        <Link href="/meetings">
                            <ArrowLeft className="w-5 h-5" />
                        </Link>
                    </Button>
                    <h1 className="text-2xl font-bold">Meeting Transcript</h1>
                </div>
                <Button onClick={handleExport}>
                    <Download className="w-4 h-4 mr-2" />
                    Export TXT
                </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                    <AudioPlayer
                        url={audioUrl}
                        onTimeUpdate={handleTimeUpdate}
                        className="w-full"
                    />

                    <TranscriptViewer
                        transcript={transcript}
                        currentTime={currentTime}
                        onSeek={handleSeek}
                    />
                </div>

                <div className="space-y-6">
                    <Card className="p-6">
                        <h3 className="font-semibold mb-4 flex items-center gap-2">
                            <FileText className="w-4 h-4" />
                            Summary
                        </h3>
                        {summary ? (
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                {summary}
                            </p>
                        ) : (
                            <p className="text-sm text-muted-foreground italic">
                                No summary available
                            </p>
                        )}
                    </Card>

                    <Card className="p-6">
                        <h3 className="font-semibold mb-4">Stats</h3>
                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">Segments</span>
                                <span>{transcript.length}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">Speakers</span>
                                <span>
                                    {new Set(transcript.map((t) => t.speaker)).size}
                                </span>
                            </div>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
}
