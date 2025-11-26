import { MeetingsList } from '@/components/MeetingsList';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { Plus } from 'lucide-react';

export default function MeetingsPage() {
    return (
        <div className="max-w-5xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">My Meetings</h1>
                    <p className="text-muted-foreground mt-1">
                        View and manage your transcribed meetings
                    </p>
                </div>
                <Button asChild>
                    <Link href="/">
                        <Plus className="w-4 h-4 mr-2" />
                        New Transcription
                    </Link>
                </Button>
            </div>

            <MeetingsList />
        </div>
    );
}
