import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { RoleGuard } from '@/components/common/RoleGuard';
import { criminalsApi } from '@/api/criminals';
import type { CriminalsListParams } from '@/api/criminals';
import type { Criminal, CriminalFormData } from '@/types/criminal';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { CriminalFilters } from '@/components/criminals/CriminalFilters';
import { CriminalsTable } from '@/components/criminals/CriminalsTable';
import { CriminalDialog } from '@/components/criminals/CriminalDialog';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';

export default function Criminals() {
    const queryClient = useQueryClient();
    const { hasRole } = useAuth();

    // State
    const [page, setPage] = useState(1);
    const [filters, setFilters] = useState<CriminalsListParams>({
        page: 1,
        limit: 10,
        search: '',
        threat_level: '',
        legal_status: '',
    });
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
    const [editingCriminal, setEditingCriminal] = useState<Criminal | undefined>();
    const [deletingCriminal, setDeletingCriminal] = useState<Criminal | undefined>();

    // Queries
    const { data, isLoading, error } = useQuery({
        queryKey: ['criminals', filters],
        queryFn: () => criminalsApi.getAll(filters),
    });

    // Mutations
    const createMutation = useMutation({
        mutationFn: (data: CriminalFormData) =>
            criminalsApi.create({
                ...data,
                aliases: data.aliases ? data.aliases.split(',').map((a) => a.trim()) : [],
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['criminals'] });
            setIsCreateDialogOpen(false);
        },
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: CriminalFormData }) =>
            criminalsApi.update(id, {
                ...data,
                aliases: data.aliases ? data.aliases.split(',').map((a) => a.trim()) : [],
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['criminals'] });
            setEditingCriminal(undefined);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => criminalsApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['criminals'] });
            setDeletingCriminal(undefined);
        },
    });

    // Handlers
    const handleSearchChange = (search: string) => {
        setFilters((prev) => ({ ...prev, search, page: 1 }));
        setPage(1);
    };

    const handleThreatLevelChange = (threat_level: string) => {
        setFilters((prev) => ({ ...prev, threat_level, page: 1 }));
        setPage(1);
    };

    const handleLegalStatusChange = (legal_status: string) => {
        setFilters((prev) => ({ ...prev, legal_status, page: 1 }));
        setPage(1);
    };

    const handleReset = () => {
        setFilters({
            page: 1,
            limit: 10,
            search: '',
            threat_level: '',
            legal_status: '',
        });
        setPage(1);
    };

    const handleCreate = (data: CriminalFormData) => {
        createMutation.mutate(data);
    };

    const handleEdit = (criminal: Criminal) => {
        setEditingCriminal(criminal);
    };

    const handleUpdate = (data: CriminalFormData) => {
        if (editingCriminal) {
            updateMutation.mutate({ id: editingCriminal.id, data });
        }
    };

    const handleDelete = (criminal: Criminal) => {
        setDeletingCriminal(criminal);
    };

    const handleConfirmDelete = () => {
        if (deletingCriminal) {
            deleteMutation.mutate(deletingCriminal.id);
        }
    };

    const handleView = (criminal: Criminal) => {
        // TODO: Implement detail view
        console.log('View criminal:', criminal);
    };

    const handlePageChange = (newPage: number) => {
        setPage(newPage);
        setFilters((prev) => ({ ...prev, page: newPage }));
    };

    return (
        <div className="space-y-6 p-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">Criminal Records</h1>
                    <p className="mt-1 text-sm text-zinc-400">
                        Manage and monitor criminal profiles in the system
                    </p>
                </div>
                <RoleGuard allowedRoles={['admin', 'senior_officer', 'field_officer']}>
                    <Button
                        onClick={() => setIsCreateDialogOpen(true)}
                        className="bg-blue-600 hover:bg-blue-700"
                    >
                        <Plus className="mr-2 h-4 w-4" />
                        Add Criminal
                    </Button>
                </RoleGuard>
            </div>

            {/* Filters */}
            <Card className="border-zinc-800 bg-zinc-950/50 p-4">
                <CriminalFilters
                    onSearchChange={handleSearchChange}
                    onThreatLevelChange={handleThreatLevelChange}
                    onLegalStatusChange={handleLegalStatusChange}
                    onReset={handleReset}
                />
            </Card>

            {/* Error State */}
            {error && (
                <Card className="border-red-900/50 bg-red-950/20 p-4">
                    <p className="text-sm text-red-400">
                        Failed to load criminals. Please try again later.
                    </p>
                </Card>
            )}

            {/* Table */}
            <CriminalsTable
                criminals={data?.items || []}
                isLoading={isLoading}
                onView={handleView}
                onEdit={hasRole(['admin', 'senior_officer', 'field_officer']) ? handleEdit : undefined}
                onDelete={hasRole(['admin', 'senior_officer']) ? handleDelete : undefined}
            />

            {/* Pagination */}
            {data && data.pages > 1 && (
                <div className="flex items-center justify-between">
                    <p className="text-sm text-zinc-400">
                        Showing <span className="font-medium text-zinc-200">{(page - 1) * 10 + 1}</span> to{' '}
                        <span className="font-medium text-zinc-200">
                            {Math.min(page * 10, data.total)}
                        </span>{' '}
                        of <span className="font-medium text-zinc-200">{data.total}</span> results
                    </p>
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePageChange(page - 1)}
                            disabled={page === 1}
                            className="border-zinc-700"
                        >
                            <ChevronLeft className="h-4 w-4 mr-1" />
                            Previous
                        </Button>
                        <div className="flex items-center gap-1">
                            {Array.from({ length: data.pages }, (_, i) => i + 1).map((pageNum) => (
                                <Button
                                    key={pageNum}
                                    variant={pageNum === page ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => handlePageChange(pageNum)}
                                    className={
                                        pageNum === page
                                            ? 'bg-blue-600 hover:bg-blue-700'
                                            : 'border-zinc-700'
                                    }
                                >
                                    {pageNum}
                                </Button>
                            ))}
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePageChange(page + 1)}
                            disabled={page === data.pages}
                            className="border-zinc-700"
                        >
                            Next
                            <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                    </div>
                </div>
            )}

            {/* Create/Edit Dialog */}
            <CriminalDialog
                open={isCreateDialogOpen || !!editingCriminal}
                onOpenChange={(open) => {
                    if (!open) {
                        setIsCreateDialogOpen(false);
                        setEditingCriminal(undefined);
                    }
                }}
                criminal={editingCriminal}
                onSubmit={editingCriminal ? handleUpdate : handleCreate}
                isLoading={createMutation.isPending || updateMutation.isPending}
            />

            {/* Delete Confirmation Dialog */}
            <Dialog
                open={!!deletingCriminal}
                onOpenChange={(open) => !open && setDeletingCriminal(undefined)}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Confirm Deletion</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete the criminal record for{' '}
                            <span className="font-semibold text-white">
                                {deletingCriminal?.full_name}
                            </span>
                            ? This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setDeletingCriminal(undefined)}
                            disabled={deleteMutation.isPending}
                            className="border-zinc-700"
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleConfirmDelete}
                            disabled={deleteMutation.isPending}
                            className="bg-red-600 hover:bg-red-700"
                        >
                            {deleteMutation.isPending ? (
                                <>
                                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-transparent"></div>
                                    Deleting...
                                </>
                            ) : (
                                'Delete'
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
