'use client';

import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TranscriptSegment } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useEffect, useRef } from 'react';

interface TranscriptViewerProps {
    transcript: TranscriptSegment[];
    currentTime?: number;
    onSeek?: (time: number) => void;
    className?: string;
}

const SPEAKER_COLORS: Record<string, string> = {
    SPEAKER_00: 'bg-blue-100 text-blue-800 border-blue-200',
    SPEAKER_01: 'bg-green-100 text-green-800 border-green-200',
    SPEAKER_02: 'bg-purple-100 text-purple-800 border-purple-200',
    SPEAKER_03: 'bg-orange-100 text-orange-800 border-orange-200',
    Unknown: 'bg-gray-100 text-gray-800 border-gray-200',
};

function formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export function TranscriptViewer({
    transcript,
    currentTime = 0,
    onSeek,
    className,
}: TranscriptViewerProps) {
    const activeSegmentRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to active segment
    useEffect(() => {
        if (activeSegmentRef.current) {
            activeSegmentRef.current.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
            });
        }
    }, [currentTime]);

    return (
        <Card className={cn('flex flex-col h-[600px]', className)}>
            <div className="p-4 border-b bg-muted/50">
                <h3 className="font-semibold">Transcript</h3>
            </div>
            <ScrollArea className="flex-1 p-4">
                <div className="space-y-6">
                    {transcript.map((segment, index) => {
                        const isActive =
                            currentTime >= segment.start &&
                            (segment.end ? currentTime < segment.end : true);

                        return (
                            <div
                                key={index}
                                ref={isActive ? activeSegmentRef : null}
                                className={cn(
                                    'group flex gap-4 p-3 rounded-lg transition-colors cursor-pointer hover:bg-muted/50',
                                    isActive && 'bg-primary/5 ring-1 ring-primary/20'
                                )}
                                onClick={() => onSeek?.(segment.start)}
                            >
                                <div className="flex-shrink-0 w-16 text-xs text-muted-foreground pt-1 font-mono">
                                    {formatTime(segment.start)}
                                </div>
                                <div className="flex-1 space-y-1">
                                    <div className="flex items-center gap-2">
                                        <Badge
                                            variant="outline"
                                            className={cn(
                                                'text-xs font-medium border',
                                                SPEAKER_COLORS[segment.speaker] || SPEAKER_COLORS.Unknown
                                            )}
                                        >
                                            {segment.speaker.replace('_', ' ')}
                                        </Badge>
                                    </div>
                                    <p className="text-sm leading-relaxed text-foreground/90">
                                        {segment.text}
                                    </p>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </ScrollArea>
        </Card>
    );
}
