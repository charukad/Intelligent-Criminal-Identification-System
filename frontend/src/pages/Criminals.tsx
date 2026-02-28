import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, ChevronLeft, ChevronRight, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import { useAuth } from '@/contexts/AuthContext';
import { RoleGuard } from '@/components/common/RoleGuard';
import { criminalsApi } from '@/api/criminals';
import { buildBackendUrl } from '@/api/client';
import type { CriminalsListParams } from '@/api/criminals';
import type { Criminal, CriminalFace, CriminalFormData } from '@/types/criminal';
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
        q: '',
        threat_level: '',
        status: '',
    });
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
    const [viewingCriminal, setViewingCriminal] = useState<Criminal | undefined>();
    const [editingCriminal, setEditingCriminal] = useState<Criminal | undefined>();
    const [deletingCriminal, setDeletingCriminal] = useState<Criminal | undefined>();
    const [actionNotice, setActionNotice] = useState<{ tone: 'success' | 'warning' | 'error'; message: string } | null>(null);
    const [existingFaceFile, setExistingFaceFile] = useState<File | null>(null);
    const [existingFacePrimary, setExistingFacePrimary] = useState(true);
    const [deletingFace, setDeletingFace] = useState<CriminalFace | null>(null);

    // Queries
    const { data, isLoading, error } = useQuery({
        queryKey: ['criminals', filters],
        queryFn: () => criminalsApi.getAll(filters),
    });

    const {
        data: viewingFaces = [],
        isLoading: isLoadingFaces,
    } = useQuery({
        queryKey: ['criminalFaces', viewingCriminal?.id],
        queryFn: () => criminalsApi.listFaces(viewingCriminal!.id),
        enabled: Boolean(viewingCriminal?.id),
    });

    // Mutations
    const createMutation = useMutation({
        mutationFn: (data: CriminalFormData) =>
            criminalsApi.create({
                first_name: data.first_name,
                last_name: data.last_name,
                aliases: data.aliases,
                nic: data.nic,
                dob: data.dob,
                gender: data.gender,
                blood_type: data.blood_type,
                threat_level: data.threat_level,
                status: data.status,
                last_known_address: data.last_known_address,
                physical_description: data.physical_description,
            }),
    });

    const uploadFaceMutation = useMutation({
        mutationFn: ({ criminalId, file, isPrimary }: { criminalId: string; file: File; isPrimary: boolean }) =>
            criminalsApi.uploadFace(criminalId, file, isPrimary),
    });

    const uploadFacesMutation = useMutation({
        mutationFn: ({ criminalId, files, primaryIndex }: { criminalId: string; files: File[]; primaryIndex: number }) =>
            criminalsApi.uploadFaces(criminalId, files, primaryIndex),
    });

    const deleteFaceMutation = useMutation({
        mutationFn: ({ criminalId, faceId }: { criminalId: string; faceId: string }) =>
            criminalsApi.deleteFace(criminalId, faceId),
    });

    const setPrimaryFaceMutation = useMutation({
        mutationFn: ({ criminalId, faceId }: { criminalId: string; faceId: string }) =>
            criminalsApi.setPrimaryFace(criminalId, faceId),
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: CriminalFormData }) =>
            criminalsApi.update(id, {
                first_name: data.first_name,
                last_name: data.last_name,
                aliases: data.aliases,
                nic: data.nic,
                dob: data.dob,
                gender: data.gender,
                blood_type: data.blood_type,
                threat_level: data.threat_level,
                status: data.status,
                last_known_address: data.last_known_address,
                physical_description: data.physical_description,
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
        setFilters((prev) => ({ ...prev, q: search, page: 1 }));
        setPage(1);
    };

    const handleThreatLevelChange = (threat_level: string) => {
        setFilters((prev) => ({ ...prev, threat_level, page: 1 }));
        setPage(1);
    };

    const handleLegalStatusChange = (status: string) => {
        setFilters((prev) => ({ ...prev, status, page: 1 }));
        setPage(1);
    };

    const handleReset = () => {
        setFilters({
            page: 1,
            limit: 10,
            q: '',
            threat_level: '',
            status: '',
        });
        setPage(1);
    };

    const handleCreate = (data: CriminalFormData) => {
        setActionNotice(null);
        createMutation.mutate(data, {
            onSuccess: async (createdCriminal) => {
                queryClient.invalidateQueries({ queryKey: ['criminals'] });

                if (data.faceFiles && data.faceFiles.length > 0) {
                    try {
                        const enrollmentResult = await uploadFacesMutation.mutateAsync({
                            criminalId: createdCriminal.id,
                            files: data.faceFiles,
                            primaryIndex: data.primaryFaceIndex ?? 0,
                        });

                        if (enrollmentResult.failed.length > 0) {
                            const failedNames = enrollmentResult.failed.map((failure) => failure.fileName).join(', ');
                            setActionNotice({
                                tone: enrollmentResult.uploaded.length > 0 ? 'warning' : 'error',
                                message:
                                    enrollmentResult.uploaded.length > 0
                                        ? `Criminal profile created. ${enrollmentResult.uploaded.length} face image(s) enrolled, but these failed: ${failedNames}.`
                                        : `Criminal profile created, but face enrollment failed for: ${failedNames}.`,
                            });
                        } else {
                            setActionNotice({
                                tone: 'success',
                                message: `Criminal profile and ${enrollmentResult.uploaded.length} face image(s) were enrolled successfully.`,
                            });
                        }
                    } catch (uploadError: any) {
                        setActionNotice({
                            tone: 'warning',
                            message:
                                uploadError?.response?.data?.detail ||
                                'Criminal profile created, but face enrollment failed. You can upload the mugshot later.',
                        });
                    }
                } else {
                    setActionNotice({
                        tone: 'success',
                        message: 'Criminal profile created successfully.',
                    });
                }

                setIsCreateDialogOpen(false);
            },
            onError: (createError: any) => {
                setActionNotice({
                    tone: 'error',
                    message:
                        createError?.response?.data?.detail ||
                        'Failed to create criminal profile. Please try again.',
                });
            },
        });
    };

    const handleEdit = (criminal: Criminal) => {
        setEditingCriminal(criminal);
    };

    const handleUpdate = (data: CriminalFormData) => {
        if (editingCriminal) {
            setActionNotice(null);
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
        setViewingCriminal(criminal);
    };

    const handleExistingFaceUpload = async () => {
        if (!viewingCriminal || !existingFaceFile) {
            return;
        }

        setActionNotice(null);
        try {
            await uploadFaceMutation.mutateAsync({
                criminalId: viewingCriminal.id,
                file: existingFaceFile,
                isPrimary: existingFacePrimary,
            });
            await queryClient.invalidateQueries({ queryKey: ['criminalFaces', viewingCriminal.id] });
            setExistingFaceFile(null);
            setExistingFacePrimary(true);
            setActionNotice({
                tone: 'success',
                message: 'Face image uploaded for the selected criminal.',
            });
        } catch (uploadError: any) {
            setActionNotice({
                tone: 'error',
                message:
                    uploadError?.response?.data?.detail ||
                    'Failed to upload the face image. Please try again.',
            });
        }
    };

    const handleConfirmDeleteFace = async () => {
        if (!viewingCriminal || !deletingFace) {
            return;
        }

        setActionNotice(null);
        try {
            await deleteFaceMutation.mutateAsync({
                criminalId: viewingCriminal.id,
                faceId: deletingFace.id,
            });
            await queryClient.invalidateQueries({ queryKey: ['criminalFaces', viewingCriminal.id] });
            setDeletingFace(null);
            setActionNotice({
                tone: 'success',
                message: 'Face record deleted successfully.',
            });
        } catch (deleteError: any) {
            setActionNotice({
                tone: 'error',
                message:
                    deleteError?.response?.data?.detail ||
                    'Failed to delete the selected face record.',
            });
        }
    };

    const handleSetPrimaryFace = async (face: CriminalFace) => {
        if (!viewingCriminal || face.is_primary) {
            return;
        }

        setActionNotice(null);
        try {
            await setPrimaryFaceMutation.mutateAsync({
                criminalId: viewingCriminal.id,
                faceId: face.id,
            });
            await queryClient.invalidateQueries({ queryKey: ['criminalFaces', viewingCriminal.id] });
            setActionNotice({
                tone: 'success',
                message: 'Primary face updated successfully.',
            });
        } catch (setPrimaryError: any) {
            setActionNotice({
                tone: 'error',
                message:
                    setPrimaryError?.response?.data?.detail ||
                    'Failed to update the primary face record.',
            });
        }
    };

    const handlePageChange = (newPage: number) => {
        setPage(newPage);
        setFilters((prev) => ({ ...prev, page: newPage }));
    };

    useEffect(() => {
        if (!viewingCriminal) {
            setExistingFaceFile(null);
            setExistingFacePrimary(true);
            setDeletingFace(null);
        }
    }, [viewingCriminal]);

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
                        className="bg-primary text-primary-foreground hover:bg-primary/90"
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

            {actionNotice && (
                <Card
                    className={
                        actionNotice.tone === 'success'
                            ? 'border-emerald-900/50 bg-emerald-950/20 p-4'
                            : actionNotice.tone === 'warning'
                                ? 'border-amber-900/50 bg-amber-950/20 p-4'
                                : 'border-red-900/50 bg-red-950/20 p-4'
                    }
                >
                    <p
                        className={
                            actionNotice.tone === 'success'
                                ? 'text-sm text-emerald-300'
                                : actionNotice.tone === 'warning'
                                    ? 'text-sm text-amber-300'
                                    : 'text-sm text-red-400'
                        }
                    >
                        {actionNotice.message}
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
                                            ? 'bg-primary text-primary-foreground hover:bg-primary/90'
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
                isLoading={
                    createMutation.isPending ||
                    uploadFaceMutation.isPending ||
                    uploadFacesMutation.isPending ||
                    updateMutation.isPending
                }
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
                                {deletingCriminal ? `${deletingCriminal.first_name} ${deletingCriminal.last_name}` : ''}
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

            {/* View Details Dialog */}
            <Dialog
                open={!!viewingCriminal}
                onOpenChange={(open) => !open && setViewingCriminal(undefined)}
            >
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>Criminal Profile Details</DialogTitle>
                    </DialogHeader>
                    {viewingCriminal && (
                        <div className="space-y-6 mt-4">
                            <div className="grid grid-cols-2 gap-4 text-sm text-zinc-300">
                                <div>
                                    <p className="text-zinc-500">Name</p>
                                    <p className="font-semibold text-white">
                                        {viewingCriminal.first_name} {viewingCriminal.last_name}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-zinc-500">NIC Mapping</p>
                                    <p className="font-semibold text-white">{viewingCriminal.nic || 'N/A'}</p>
                                </div>
                                <div>
                                    <p className="text-zinc-500">Aliases</p>
                                    <p>{viewingCriminal.aliases || 'None'}</p>
                                </div>
                                <div>
                                    <p className="text-zinc-500">Gender</p>
                                    <p>{viewingCriminal.gender || 'Unknown'}</p>
                                </div>
                                <div>
                                    <p className="text-zinc-500">Threat Level</p>
                                    <p>{viewingCriminal.threat_level}</p>
                                </div>
                                <div>
                                    <p className="text-zinc-500">Status</p>
                                    <p>{viewingCriminal.status}</p>
                                </div>
                                <div>
                                    <p className="text-zinc-500">Last Known Address</p>
                                    <p>{viewingCriminal.last_known_address || 'Unknown'}</p>
                                </div>
                                <div className="col-span-2">
                                    <p className="text-zinc-500">Physical Description</p>
                                    <p>{viewingCriminal.physical_description || 'None documented'}</p>
                                </div>
                            </div>

                            <div className="space-y-4 border-t border-zinc-800 pt-4">
                                <div>
                                    <p className="text-sm font-semibold text-white">Enrolled Face Images</p>
                                    <p className="text-xs text-zinc-500">
                                        Stored mugshots and their embedding metadata used by the recognition pipeline.
                                    </p>
                                </div>

                                {isLoadingFaces ? (
                                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-6 text-sm text-zinc-500">
                                        Loading enrolled faces...
                                    </div>
                                ) : viewingFaces.length === 0 ? (
                                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-6 text-sm text-zinc-500">
                                        No face images have been enrolled for this criminal yet.
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {viewingFaces.map((face: CriminalFace, index: number) => (
                                            <div key={face.id} className="relative pl-8">
                                                {index !== viewingFaces.length - 1 && (
                                                    <div className="absolute left-[11px] top-8 h-[calc(100%-1rem)] w-px bg-zinc-800" />
                                                )}
                                                <div className="absolute left-0 top-2 h-6 w-6 rounded-full border border-zinc-700 bg-zinc-950 flex items-center justify-center">
                                                    <div className={`h-2.5 w-2.5 rounded-full ${face.is_primary ? 'bg-emerald-400' : 'bg-zinc-500'}`} />
                                                </div>
                                                <div className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950/60">
                                                    <div className="grid gap-0 md:grid-cols-[220px_1fr]">
                                                        <img
                                                            src={buildBackendUrl(face.image_url)}
                                                            alt="Enrolled criminal face"
                                                            className="h-56 w-full object-cover md:h-full"
                                                        />
                                                        <div className="space-y-4 p-4 text-sm text-zinc-300">
                                                            <div className="flex flex-wrap items-start justify-between gap-3">
                                                                <div>
                                                                    <p className="font-medium text-white">
                                                                        {face.is_primary ? 'Current Primary Face' : 'Historical Face Record'}
                                                                    </p>
                                                                    <p className="mt-1 text-xs text-zinc-500">
                                                                        Enrolled on {format(new Date(face.created_at), 'PPP p')}
                                                                    </p>
                                                                </div>
                                                                <div className="flex flex-wrap items-center gap-2">
                                                                    <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-400">
                                                                        {face.embedding_version}
                                                                    </span>
                                                                    <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-400">
                                                                        {face.is_primary ? 'Active' : 'Archived'}
                                                                    </span>
                                                                </div>
                                                            </div>

                                                            <div className="grid gap-3 text-xs text-zinc-500 sm:grid-cols-2">
                                                                <p>
                                                                    Bounding box: x={face.box[0]}, y={face.box[1]}, w={face.box[2]}, h={face.box[3]}
                                                                </p>
                                                                <p>
                                                                    Face ID: <span className="font-mono text-zinc-400">{face.id}</span>
                                                                </p>
                                                            </div>

                                                            {hasRole(['admin', 'senior_officer', 'field_officer']) && (
                                                                <div className="flex flex-wrap justify-end gap-2 pt-2">
                                                                    {!face.is_primary && (
                                                                        <Button
                                                                            type="button"
                                                                            variant="outline"
                                                                            size="sm"
                                                                            className="border-zinc-700 text-zinc-200"
                                                                            onClick={() => handleSetPrimaryFace(face)}
                                                                            disabled={setPrimaryFaceMutation.isPending}
                                                                        >
                                                                            Set Primary
                                                                        </Button>
                                                                    )}
                                                                    <Button
                                                                        type="button"
                                                                        variant="outline"
                                                                        size="sm"
                                                                        className="border-red-900/50 text-red-400 hover:bg-red-950/30"
                                                                        onClick={() => setDeletingFace(face)}
                                                                    >
                                                                        <Trash2 className="mr-2 h-4 w-4" />
                                                                        Delete
                                                                    </Button>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {hasRole(['admin', 'senior_officer', 'field_officer']) && (
                                <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-950/50 p-4">
                                    <div>
                                        <p className="text-sm font-semibold text-white">Add Or Replace Face Image</p>
                                        <p className="text-xs text-zinc-500">
                                            Upload another mugshot for this criminal. Mark it as primary to replace the active face image used in the UI.
                                        </p>
                                    </div>
                                    <input
                                        type="file"
                                        accept="image/jpeg,image/png,image/webp"
                                        className="block w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-300 file:mr-4 file:border-0 file:bg-transparent file:text-sm"
                                        onChange={(event) => setExistingFaceFile(event.target.files?.[0] ?? null)}
                                    />
                                    <label className="flex items-center gap-3 text-sm text-zinc-300">
                                        <input
                                            type="checkbox"
                                            className="h-4 w-4 rounded border-zinc-600 bg-zinc-900 text-primary"
                                            checked={existingFacePrimary}
                                            onChange={(event) => setExistingFacePrimary(event.target.checked)}
                                        />
                                        Mark this upload as the new primary face image
                                    </label>
                                    <div className="flex justify-end">
                                        <Button
                                            type="button"
                                            onClick={handleExistingFaceUpload}
                                            disabled={!existingFaceFile || uploadFaceMutation.isPending || setPrimaryFaceMutation.isPending}
                                            className="bg-primary text-primary-foreground hover:bg-primary/90"
                                        >
                                            {uploadFaceMutation.isPending ? 'Uploading...' : 'Upload Face Image'}
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            <Dialog open={!!deletingFace} onOpenChange={(open) => !open && setDeletingFace(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Delete Face Record</DialogTitle>
                        <DialogDescription>
                            Delete this enrolled face image and embedding record? If it is the primary face, another stored face will be promoted automatically.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setDeletingFace(null)}
                            disabled={deleteFaceMutation.isPending}
                            className="border-zinc-700"
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleConfirmDeleteFace}
                            disabled={deleteFaceMutation.isPending || setPrimaryFaceMutation.isPending}
                        >
                            {deleteFaceMutation.isPending ? 'Deleting...' : 'Delete Face'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
