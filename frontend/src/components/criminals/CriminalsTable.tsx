import type { Criminal } from '@/types/criminal';
import { buildBackendUrl } from '@/api/client';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Eye, Edit2, Trash2 } from 'lucide-react';

interface CriminalsTableProps {
    criminals: Criminal[];
    isLoading: boolean;
    onView: (criminal: Criminal) => void;
    onEdit?: (criminal: Criminal) => void;
    onDelete?: (criminal: Criminal) => void;
}

const getThreatLevelBadge = (level?: string) => {
    const variants: Record<string, 'destructive' | 'warning' | 'info' | 'default'> = {
        critical: 'destructive',
        high: 'destructive',
        medium: 'warning',
        low: 'info',
    };

    return (
        <Badge variant={variants[level || ''] || 'default'}>
            {level ? level.replace('_', ' ') : 'Unknown'}
        </Badge>
    );
};

const getLegalStatusBadge = (status?: string) => {
    const variants: Record<string, 'destructive' | 'warning' | 'success' | 'info' | 'default'> = {
        wanted: 'destructive',
        in_custody: 'warning',
        released: 'success',
        deceased: 'default',
        cleared: 'info',
    };

    const labels: Record<string, string> = {
        wanted: 'Wanted',
        in_custody: 'In Custody',
        released: 'Released',
        deceased: 'Deceased',
        cleared: 'Cleared',
    };

    return (
        <Badge variant={variants[status || ''] || 'default'}>
            {labels[status || ''] || status || 'Unknown'}
        </Badge>
    );
};

export function CriminalsTable({
    criminals,
    isLoading,
    onView,
    onEdit,
    onDelete,
}: CriminalsTableProps) {
    if (isLoading) {
        return (
            <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-8">
                <div className="flex items-center justify-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-800 border-t-blue-600"></div>
                </div>
            </div>
        );
    }

    if (criminals.length === 0) {
        return (
            <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-12 text-center">
                <p className="text-zinc-400">No criminals found.</p>
                <p className="mt-2 text-sm text-zinc-500">
                    Try adjusting your filters or create a new criminal record.
                </p>
            </div>
        );
    }

    return (
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/50">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>NIC</TableHead>
                        <TableHead>Gender</TableHead>
                        <TableHead>Threat Level</TableHead>
                        <TableHead>Legal Status</TableHead>
                        <TableHead>Last Known Address</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {criminals.map((criminal) => (
                        <TableRow key={criminal.id} className="cursor-pointer hover:bg-zinc-900/50">
                            <TableCell className="font-medium">
                                <div className="flex items-center gap-3">
                                    {criminal.primary_face_image_url ? (
                                        <img
                                            src={buildBackendUrl(criminal.primary_face_image_url)}
                                            alt={`${criminal.first_name} ${criminal.last_name}`}
                                            className="h-10 w-10 rounded-full object-cover ring-1 ring-zinc-700"
                                        />
                                    ) : (
                                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800 text-xs font-semibold text-zinc-400 ring-1 ring-zinc-700">
                                            {criminal.first_name.slice(0, 1)}
                                            {criminal.last_name.slice(0, 1)}
                                        </div>
                                    )}
                                    <div>
                                        <div>{criminal.first_name} {criminal.last_name}</div>
                                        <div className="text-xs text-zinc-500">
                                            {criminal.primary_face_image_url ? 'Primary face enrolled' : 'No face enrolled'}
                                        </div>
                                    </div>
                                </div>
                            </TableCell>
                            <TableCell className="text-zinc-400">{criminal.nic || 'N/A'}</TableCell>
                            <TableCell className="text-zinc-400">{criminal.gender || 'N/A'}</TableCell>
                            <TableCell>{getThreatLevelBadge(criminal.threat_level)}</TableCell>
                            <TableCell>{getLegalStatusBadge(criminal.status)}</TableCell>
                            <TableCell className="text-zinc-400">{criminal.last_known_address || 'Unknown'}</TableCell>
                            <TableCell className="text-right">
                                <div className="flex justify-end gap-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onView(criminal);
                                        }}
                                        className="border-zinc-700"
                                    >
                                        <Eye className="h-4 w-4" />
                                    </Button>
                                    {onEdit && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onEdit(criminal);
                                            }}
                                            className="border-zinc-700"
                                        >
                                            <Edit2 className="h-4 w-4" />
                                        </Button>
                                    )}
                                    {onDelete && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onDelete(criminal);
                                            }}
                                            className="border-red-900/50 text-red-400 hover:bg-red-900/20"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    )}
                                </div>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
