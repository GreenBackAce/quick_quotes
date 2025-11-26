'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import WaveSurfer from 'wavesurfer.js';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import {
    Play,
    Pause,
    SkipBack,
    SkipForward,
    Volume2,
    VolumeX,
    Download,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AudioPlayerProps {
    url: string;
    onTimeUpdate?: (time: number) => void;
    onReady?: () => void;
    className?: string;
}

export function AudioPlayer({
    url,
    onTimeUpdate,
    onReady,
    className,
}: AudioPlayerProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const wavesurfer = useRef<WaveSurfer | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [duration, setDuration] = useState(0);
    const [currentTime, setCurrentTime] = useState(0);
    const [volume, setVolume] = useState(1);
    const [isMuted, setIsMuted] = useState(false);
    const [playbackRate, setPlaybackRate] = useState(1);

    // Initialize WaveSurfer
    useEffect(() => {
        if (!containerRef.current) return;

        wavesurfer.current = WaveSurfer.create({
            container: containerRef.current,
            waveColor: '#e2e8f0',
            progressColor: '#3b82f6',
            cursorColor: '#3b82f6',
            barWidth: 2,
            barGap: 1,
            barRadius: 2,
            height: 80,
            normalize: true,
            minPxPerSec: 50,
        });

        wavesurfer.current.load(url);

        wavesurfer.current.on('ready', () => {
            setDuration(wavesurfer.current?.getDuration() || 0);
            onReady?.();
        });

        wavesurfer.current.on('audioprocess', (time) => {
            setCurrentTime(time);
            onTimeUpdate?.(time);
        });

        wavesurfer.current.on('interaction', (time) => {
            setCurrentTime(time);
            onTimeUpdate?.(time);
        });

        wavesurfer.current.on('play', () => setIsPlaying(true));
        wavesurfer.current.on('pause', () => setIsPlaying(false));
        wavesurfer.current.on('finish', () => setIsPlaying(false));

        return () => {
            try {
                wavesurfer.current?.destroy();
            } catch (e) {
                // Ignore abort errors during cleanup
                console.debug("WaveSurfer destroy error:", e);
            }
        };
    }, [url, onReady, onTimeUpdate]);

    // Listen for seek events from other components
    useEffect(() => {
        const handleSeek = (e: Event) => {
            const customEvent = e as CustomEvent<number>;
            if (wavesurfer.current) {
                wavesurfer.current.setTime(customEvent.detail);
            }
        };

        window.addEventListener('seek-audio', handleSeek);
        return () => window.removeEventListener('seek-audio', handleSeek);
    }, []);

    // Handle controls
    const togglePlay = useCallback(() => {
        wavesurfer.current?.playPause();
    }, []);

    const skipForward = useCallback(() => {
        wavesurfer.current?.skip(5);
    }, []);

    const skipBack = useCallback(() => {
        wavesurfer.current?.skip(-5);
    }, []);

    const handleVolumeChange = useCallback((value: number[]) => {
        const newVolume = value[0];
        setVolume(newVolume);
        wavesurfer.current?.setVolume(newVolume);
        setIsMuted(newVolume === 0);
    }, []);

    const toggleMute = useCallback(() => {
        if (isMuted) {
            wavesurfer.current?.setVolume(volume);
            setIsMuted(false);
        } else {
            wavesurfer.current?.setVolume(0);
            setIsMuted(true);
        }
    }, [isMuted, volume]);

    const handleSpeedChange = useCallback((speed: number) => {
        setPlaybackRate(speed);
        wavesurfer.current?.setPlaybackRate(speed);
    }, []);

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    // Expose seek method via ref or context if needed, 
    // but for now we'll assume parent controls seek via props change 
    // (Wait, props change is tricky with imperative API. 
    // Usually parent passes a ref to call methods, or we expose a seekTo prop)

    // Let's add an effect to handle external seek if we add a prop later.
    // For now, the TranscriptViewer will likely need to control this.
    // I'll export a helper or use a ref in the parent page.

    return (
        <Card className={cn('p-4 space-y-4', className)}>
            <div ref={containerRef} className="w-full" />

            <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={skipBack}
                        className="text-muted-foreground hover:text-foreground"
                    >
                        <SkipBack className="w-5 h-5" />
                    </Button>

                    <Button
                        size="icon"
                        onClick={togglePlay}
                        className="h-10 w-10 rounded-full shadow-md"
                    >
                        {isPlaying ? (
                            <Pause className="w-5 h-5" />
                        ) : (
                            <Play className="w-5 h-5 ml-1" />
                        )}
                    </Button>

                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={skipForward}
                        className="text-muted-foreground hover:text-foreground"
                    >
                        <SkipForward className="w-5 h-5" />
                    </Button>

                    <div className="text-sm font-mono text-muted-foreground ml-2">
                        {formatTime(currentTime)} / {formatTime(duration)}
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        {[0.5, 1, 1.5, 2].map((rate) => (
                            <Button
                                key={rate}
                                variant={playbackRate === rate ? 'secondary' : 'ghost'}
                                size="sm"
                                onClick={() => handleSpeedChange(rate)}
                                className="h-7 px-2 text-xs font-medium"
                            >
                                {rate}x
                            </Button>
                        ))}
                    </div>

                    <div className="flex items-center gap-2 w-32">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={toggleMute}
                            className="h-8 w-8 text-muted-foreground"
                        >
                            {isMuted ? (
                                <VolumeX className="w-4 h-4" />
                            ) : (
                                <Volume2 className="w-4 h-4" />
                            )}
                        </Button>
                        <Slider
                            value={[isMuted ? 0 : volume]}
                            max={1}
                            step={0.01}
                            onValueChange={handleVolumeChange}
                            className="w-20"
                        />
                    </div>
                </div>
            </div>
        </Card>
    );
}
