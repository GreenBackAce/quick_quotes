'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMeetings, deleteMeeting, Meeting } from '@/lib/api';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { MoreHorizontal, Trash2, FileText, Calendar } from 'lucide-react';
import { format } from 'date-fns';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export function MeetingsList() {
    const router = useRouter();
    const queryClient = useQueryClient();

    const { data, isLoading, error } = useQuery({
        queryKey: ['meetings'],
        queryFn: getMeetings,
    });

    const deleteMutation = useMutation({
        mutationFn: deleteMeeting,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['meetings'] });
        },
    });

    if (isLoading) {
        return (
            <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 bg-muted/50 animate-pulse rounded-lg" />
                ))}
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center p-8 text-destructive">
                Failed to load meetings
            </div>
        );
    }

    const meetings = data?.data.meetings || [];

    if (meetings.length === 0) {
        return (
            <div className="text-center p-12 border-2 border-dashed rounded-lg text-muted-foreground">
                <p>No meetings found</p>
                <p className="text-sm mt-1">Upload an audio file to get started</p>
            </div>
        );
    }

    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>Title</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Segments</TableHead>
                        <TableHead className="w-[70px]"></TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {meetings.map((meeting) => (
                        <TableRow key={meeting.id}>
                            <TableCell className="font-medium">
                                <Link
                                    href={`/meetings/${meeting.id}`}
                                    className="hover:underline flex items-center gap-2"
                                >
                                    <FileText className="w-4 h-4 text-muted-foreground" />
                                    {meeting.title}
                                </Link>
                            </TableCell>
                            <TableCell>
                                <div className="flex items-center gap-2 text-muted-foreground">
                                    <Calendar className="w-4 h-4" />
                                    {format(new Date(meeting.created_at), 'MMM d, yyyy')}
                                </div>
                            </TableCell>
                            <TableCell>{meeting.transcript_count}</TableCell>
                            <TableCell>
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button variant="ghost" className="h-8 w-8 p-0">
                                            <span className="sr-only">Open menu</span>
                                            <MoreHorizontal className="h-4 w-4" />
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                        <DropdownMenuItem
                                            className="text-destructive focus:text-destructive"
                                            onClick={() => {
                                                if (confirm('Are you sure you want to delete this meeting?')) {
                                                    deleteMutation.mutate(meeting.id);
                                                }
                                            }}
                                        >
                                            <Trash2 className="mr-2 h-4 w-4" />
                                            Delete
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
