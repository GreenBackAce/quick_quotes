'use client';

import { useState, useCallback } from 'react';
import { uploadAudio, getProgress } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Upload, FileAudio, CheckCircle2, XCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function AudioUploader() {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [processing, setProcessing] = useState(false);
    const [processingProgress, setProcessingProgress] = useState(0);
    const [processingStatus, setProcessingStatus] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [meetingId, setMeetingId] = useState<string | null>(null);
    const router = useRouter();

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();

        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && droppedFile.type.startsWith('audio/')) {
            setFile(droppedFile);
            setError(null);
        } else {
            setError('Please drop an audio file');
        }
    }, []);

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            setError(null);
        }
    }, []);

    const pollProgress = useCallback(async (id: string) => {
        const interval = setInterval(async () => {
            try {
                const response = await getProgress(id);
                const { progress, status, error: processError } = response.data;

                setProcessingProgress(progress);
                setProcessingStatus(status);

                if (progress === 100) {
                    clearInterval(interval);
                    setTimeout(() => {
                        router.push(`/meetings/${id}`);
                    }, 1000);
                }

                if (processError) {
                    clearInterval(interval);
                    setError(processError);
                    setProcessing(false);
                }
            } catch (err) {
                console.error('Error polling progress:', err);
                clearInterval(interval);
                setError('Failed to get processing status');
                setProcessing(false);
            }
        }, 1000);
    }, [router]);

    const handleUpload = async () => {
        if (!file) return;

        setUploading(true);
        setError(null);

        try {
            const response = await uploadAudio(file, (progressEvent) => {
                const percent = Math.round(
                    (progressEvent.loaded * 100) / progressEvent.total
                );
                setUploadProgress(percent);
            });

            setUploading(false);
            setProcessing(true);
            setMeetingId(response.data.meeting_id);

            // Start polling for progress
            pollProgress(response.data.meeting_id);
        } catch (err: any) {
            setUploading(false);
            setError(err.response?.data?.detail || 'Upload failed');
        }
    };

    const reset = () => {
        setFile(null);
        setUploading(false);
        setUploadProgress(0);
        setProcessing(false);
        setProcessingProgress(0);
        setProcessingStatus('');
        setError(null);
        setMeetingId(null);
    };

    if (processing) {
        return (
            <Card className="p-8">
                <div className="text-center space-y-4">
                    <FileAudio className="w-16 h-16 mx-auto text-primary animate-pulse" />
                    <div>
                        <p className="font-medium text-lg">{processingStatus}</p>
                        <p className="text-sm text-muted-foreground mt-1">{file?.name}</p>
                    </div>
                    <Progress value={processingProgress} className="w-full" />
                    <p className="text-sm text-muted-foreground">
                        {processingProgress}% complete
                    </p>
                </div>
            </Card>
        );
    }

    if (error) {
        return (
            <Card className="p-8 border-destructive">
                <div className="text-center space-y-4">
                    <XCircle className="w-16 h-16 mx-auto text-destructive" />
                    <div>
                        <p className="font-medium text-lg text-destructive">Error</p>
                        <p className="text-sm text-muted-foreground mt-1">{error}</p>
                    </div>
                    <Button onClick={reset}>Try Again</Button>
                </div>
            </Card>
        );
    }

    if (uploading) {
        return (
            <Card className="p-8">
                <div className="text-center space-y-4">
                    <Upload className="w-16 h-16 mx-auto text-primary animate-bounce" />
                    <div>
                        <p className="font-medium text-lg">Uploading...</p>
                        <p className="text-sm text-muted-foreground mt-1">{file?.name}</p>
                    </div>
                    <Progress value={uploadProgress} className="w-full" />
                    <p className="text-sm text-muted-foreground">
                        {uploadProgress}% uploaded
                    </p>
                </div>
            </Card>
        );
    }

    return (
        <Card className="p-8">
            <div
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-12 text-center hover:border-primary/50 transition-colors cursor-pointer"
            >
                {file ? (
                    <div className="space-y-4">
                        <CheckCircle2 className="w-16 h-16 mx-auto text-green-500" />
                        <div>
                            <p className="font-medium">{file.name}</p>
                            <p className="text-sm text-muted-foreground mt-1">
                                {(file.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                        </div>
                        <div className="flex gap-2 justify-center">
                            <Button onClick={handleUpload}>Upload & Process</Button>
                            <Button variant="outline" onClick={reset}>
                                Change File
                            </Button>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <Upload className="w-16 h-16 mx-auto text-muted-foreground" />
                        <div>
                            <p className="font-medium">Drop your audio file here</p>
                            <p className="text-sm text-muted-foreground mt-1">
                                or click to browse
                            </p>
                        </div>
                        <input
                            type="file"
                            accept="audio/*"
                            onChange={handleFileSelect}
                            className="hidden"
                            id="file-upload"
                        />
                        <label htmlFor="file-upload">
                            <Button asChild>
                                <span>Select File</span>
                            </Button>
                        </label>
                        <p className="text-xs text-muted-foreground">
                            Supported formats: WAV, MP3, M4A, FLAC, OGG
                        </p>
                    </div>
                )}
            </div>
        </Card>
    );
}
