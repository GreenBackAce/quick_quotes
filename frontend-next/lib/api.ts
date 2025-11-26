import axios from 'axios';

// Create axios instance with FastAPI backend URL
const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Types
export interface Meeting {
    id: string;
    title: string;
    created_at: string;
    transcript_count: number;
    has_summary: boolean;
}

export interface TranscriptSegment {
    speaker: string;
    text: string;
    start: number;
    end?: number;
    timestamp?: number;
}

export interface ProgressResponse {
    meeting_id: string;
    progress: number;
    status: string;
    error?: string;
}

// API functions
export const uploadAudio = (
    file: File,
    onUploadProgress?: (progressEvent: any) => void
) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('meeting_title', file.name.replace(/\.[^/.]+$/, ''));

    return api.post<{ meeting_id: string; status: string; message: string }>(
        '/meetings/upload',
        formData,
        {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            onUploadProgress,
        }
    );
};

export const getMeetings = () => {
    return api.get<{ meetings: Meeting[] }>('/meetings');
};

export const getMeeting = (id: string) => {
    return api.get<{
        meeting_id: string;
        transcript: TranscriptSegment[];
        summary?: string;
    }>(`/meetings/${id}/transcript`);
};

export const getProgress = (id: string) => {
    return api.get<ProgressResponse>(`/meetings/${id}/progress`);
};

export const deleteMeeting = (id: string) => {
    return api.delete(`/meetings/${id}`);
};

export const exportMeeting = (id: string) => {
    return api.get<{
        meeting_id: string;
        title: string;
        content: string;
        filename: string;
    }>(`/meetings/${id}/export`);
};
