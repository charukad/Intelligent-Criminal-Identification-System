import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, ChevronLeft, ChevronRight, ShieldAlert, ShieldCheck, Trash2, Ban, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { RoleGuard } from '@/components/common/RoleGuard';
import { criminalsApi } from '@/api/criminals';
import { buildBackendUrl } from '@/api/client';
import type { CriminalsListParams } from '@/api/criminals';
import type { Criminal, CriminalFace, CriminalFormData } from '@/types/criminal';
import type { DuplicateReviewSummary } from '@/types/review';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { CriminalFilters } from '@/components/criminals/CriminalFilters';
import { CriminalsTable } from '@/components/criminals/CriminalsTable';
import { CriminalDialog } from '@/components/criminals/CriminalDialog';
import { FaceOutlierWarning } from '@/components/criminals/FaceOutlierWarning';
import { FaceTemplateSummary } from '@/components/criminals/FaceTemplateSummary';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';

function humanizeQualityLabel(value: string) {
    return value.replace(/_/g, ' ');
}

function getFaceQualityBadge(face: CriminalFace) {
    if (face.quality.status === 'accepted') {
        return { label: 'Ready For Matching', variant: 'success' as const };
    }
    if (face.quality.status === 'accepted_with_warnings') {
        return { label: 'Use With Warnings', variant: 'warning' as const };
    }
    return { label: 'Rejected Quality', variant: 'destructive' as const };
}

function getStoredFaceWarnings(face: CriminalFace) {
    const warnings = [...face.quality.warnings];

    if (face.quality.pose_score > 0 && face.quality.pose_score < 65 && !warnings.includes('face_pose_off_center')) {
        warnings.unshift('face_pose_off_center');
    }

    if (
        face.quality.occlusion_score > 0 &&
        face.quality.occlusion_score < 65 &&
        !warnings.includes('possible_face_occlusion')
    ) {
        warnings.push('possible_face_occlusion');
    }

    return Array.from(new Set(warnings));
}

function getMetricTone(score: number) {
    if (score <= 0) {
        return 'text-zinc-500';
    }
    if (score >= 85) {
        return 'text-emerald-300';
    }
    if (score >= 65) {
        return 'text-amber-300';
    }
    return 'text-red-300';
}

function formatMetricValue(value: number, suffix = '') {
    if (value <= 0) {
        return 'Unavailable';
    }
    return `${value.toFixed(1)}${suffix}`;
}

function humanizeEnum(value?: string | null, fallback = 'Not provided') {
    if (!value) {
        return fallback;
    }

    return value
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (character) => character.toUpperCase());
}

function getThreatBadgeVariant(threatLevel?: Criminal['threat_level']) {
    switch (threatLevel) {
        case 'critical':
            return 'destructive' as const;
        case 'high':
            return 'warning' as const;
        case 'medium':
            return 'info' as const;
        case 'low':
            return 'success' as const;
        default:
            return 'outline' as const;
    }
}

function getStatusBadgeVariant(status?: Criminal['status']) {
    switch (status) {
        case 'wanted':
            return 'destructive' as const;
        case 'in_custody':
            return 'warning' as const;
        case 'released':
            return 'info' as const;
        case 'cleared':
            return 'success' as const;
        case 'deceased':
            return 'outline' as const;
        default:
            return 'outline' as const;
    }
}

function buildDuplicateReviewMessage(summary: DuplicateReviewSummary, fileName?: string) {
    const prefix = fileName ? `${fileName}: ` : '';
    return (
        `${prefix}${summary.risk_level === 'probable_duplicate' ? 'Probable duplicate' : 'Needs review'} ` +
        `with ${summary.conflicting_criminal.name} at distance ${summary.distance.toFixed(6)}. ` +
        `Review case ${summary.review_case_id}.`
    );
}

function buildEnrollmentNotice(
    uploaded: CriminalFace[],
    failed: { fileName: string; detail: string; duplicateReview?: DuplicateReviewSummary }[],
) {
    const acceptedWithReview = uploaded
        .filter((face) => face.duplicate_review)
        .map((face) => buildDuplicateReviewMessage(face.duplicate_review!, face.image_url.split('/').pop()));
    const blockedDuplicates = failed
        .filter((failure) => failure.duplicateReview)
        .map((failure) => buildDuplicateReviewMessage(failure.duplicateReview!, failure.fileName));
    const genericFailures = failed
        .filter((failure) => !failure.duplicateReview)
        .map((failure) => `${failure.fileName}: ${failure.detail}`);

    const detailParts = [...acceptedWithReview, ...blockedDuplicates, ...genericFailures];
    const reviewCaseIds = [
        ...uploaded
            .map((face) => face.duplicate_review?.review_case_id)
            .filter((value): value is string => Boolean(value)),
        ...failed
            .map((failure) => failure.duplicateReview?.review_case_id)
            .filter((value): value is string => Boolean(value)),
    ];

    if (detailParts.length === 0) {
        return {
            tone: 'success' as const,
            message: `Criminal profile and ${uploaded.length} face image(s) were enrolled successfully.`,
            reviewCaseIds: [] as string[],
        };
    }

    return {
        tone: uploaded.length > 0 ? ('warning' as const) : ('error' as const),
        message:
            (uploaded.length > 0
                ? `Criminal profile created. ${uploaded.length} face image(s) enrolled with review warnings or partial failures. `
                : 'Criminal profile created, but face enrollment raised duplicate or upload issues. ') +
            detailParts.join(' '),
        reviewCaseIds: Array.from(new Set(reviewCaseIds)),
    };
}

function getUploadErrorDetails(error: any) {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string') {
        return { message: detail, reviewCaseIds: [] as string[] };
    }
    if (detail?.review_case_id && detail?.conflicting_criminal?.name) {
        const summary: DuplicateReviewSummary = {
            review_case_id: String(detail.review_case_id),
            risk_level: detail.risk_level,
            distance: Number(detail.distance ?? 0),
            conflicting_criminal: {
                id: String(detail.conflicting_criminal.id),
                name: detail.conflicting_criminal.name,
                primary_face_image_url: detail.conflicting_criminal.primary_face_image_url ?? null,
            },
            status: 'open',
        };
        return {
            message: buildDuplicateReviewMessage(summary),
            reviewCaseIds: [summary.review_case_id],
        };
    }
    if (detail?.message) {
        return { message: detail.message, reviewCaseIds: [] as string[] };
    }
    return { message: 'Failed to upload the face image. Please try again.', reviewCaseIds: [] as string[] };
}

export default function Criminals() {
    const queryClient = useQueryClient();
    const { hasRole } = useAuth();
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const focusedCriminalId = searchParams.get('criminal');

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
    const [actionNotice, setActionNotice] = useState<{
        tone: 'success' | 'warning' | 'error';
        message: string;
        reviewCaseIds?: string[];
    } | null>(null);
    const [existingFaceFile, setExistingFaceFile] = useState<File | null>(null);
    const [existingFacePrimary, setExistingFacePrimary] = useState(true);
    const [deletingFace, setDeletingFace] = useState<CriminalFace | null>(null);
    const [markingBadFace, setMarkingBadFace] = useState<CriminalFace | null>(null);
    const [markBadNotes, setMarkBadNotes] = useState('');

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

    const { data: focusedCriminal } = useQuery({
        queryKey: ['criminal', focusedCriminalId],
        queryFn: () => criminalsApi.getById(focusedCriminalId!),
        enabled: Boolean(focusedCriminalId),
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

    const markBadFaceMutation = useMutation({
        mutationFn: ({ criminalId, faceId, notes }: { criminalId: string; faceId: string; notes?: string }) =>
            criminalsApi.markFaceAsBad(criminalId, faceId, notes),
    });

    const recomputeTemplateMutation = useMutation({
        mutationFn: (criminalId: string) => criminalsApi.recomputeTemplate(criminalId),
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
                        setActionNotice(buildEnrollmentNotice(enrollmentResult.uploaded, enrollmentResult.failed));
                    } catch (uploadError: any) {
                        const uploadErrorDetails = getUploadErrorDetails(uploadError);
                        setActionNotice({
                            tone: 'warning',
                            message: uploadErrorDetails.message,
                            reviewCaseIds: uploadErrorDetails.reviewCaseIds,
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
        const currentFileName = existingFaceFile.name;
        try {
            const enrolledFace = await uploadFaceMutation.mutateAsync({
                criminalId: viewingCriminal.id,
                file: existingFaceFile,
                isPrimary: existingFacePrimary,
            });
            await queryClient.invalidateQueries({ queryKey: ['criminalFaces', viewingCriminal.id] });
            setExistingFaceFile(null);
            setExistingFacePrimary(true);
            if (enrolledFace.duplicate_review) {
                setActionNotice({
                    tone: 'warning',
                    message:
                        'Face image uploaded, but the system flagged a duplicate review. ' +
                        buildDuplicateReviewMessage(enrolledFace.duplicate_review, currentFileName),
                    reviewCaseIds: [enrolledFace.duplicate_review.review_case_id],
                });
            } else {
                setActionNotice({
                    tone: 'success',
                    message: 'Face image uploaded for the selected criminal.',
                    reviewCaseIds: [],
                });
            }
        } catch (uploadError: any) {
            const uploadErrorDetails = getUploadErrorDetails(uploadError);
            setActionNotice({
                tone: uploadError?.response?.status === 409 ? 'warning' : 'error',
                message: uploadErrorDetails.message,
                reviewCaseIds: uploadErrorDetails.reviewCaseIds,
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
        if (!viewingCriminal || face.is_primary || face.exclude_from_template) {
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

    const handleConfirmMarkFaceAsBad = async () => {
        if (!viewingCriminal || !markingBadFace) {
            return;
        }

        setActionNotice(null);
        try {
            const result = await markBadFaceMutation.mutateAsync({
                criminalId: viewingCriminal.id,
                faceId: markingBadFace.id,
                notes: markBadNotes.trim() || undefined,
            });
            await queryClient.invalidateQueries({ queryKey: ['criminalFaces', viewingCriminal.id] });
            await queryClient.invalidateQueries({ queryKey: ['criminals'] });
            await queryClient.invalidateQueries({ queryKey: ['criminal', viewingCriminal.id] });
            setMarkingBadFace(null);
            setMarkBadNotes('');
            setActionNotice({
                tone: 'warning',
                message:
                    result.message +
                    (result.promoted_face_id
                        ? ' Another eligible face was promoted as primary.'
                        : ' No replacement primary face was available.'),
            });
        } catch (markBadError: any) {
            setActionNotice({
                tone: 'error',
                message:
                    markBadError?.response?.data?.detail ||
                    'Failed to mark the selected enrollment as bad.',
            });
        }
    };

    const handleRecomputeTemplate = async () => {
        if (!viewingCriminal) {
            return;
        }

        setActionNotice(null);
        try {
            const result = await recomputeTemplateMutation.mutateAsync(viewingCriminal.id);
            await queryClient.invalidateQueries({ queryKey: ['criminalFaces', viewingCriminal.id] });
            await queryClient.invalidateQueries({ queryKey: ['criminals'] });
            await queryClient.invalidateQueries({ queryKey: ['criminal', viewingCriminal.id] });
            const template = result.template;
            setActionNotice({
                tone: 'success',
                message: template
                    ? `${result.message} Active ${template.active_face_count}, support ${template.support_face_count}, outlier ${template.outlier_face_count}.`
                    : `${result.message} No active template could be built from the current enrolled faces.`,
            });
        } catch (recomputeError: any) {
            setActionNotice({
                tone: 'error',
                message:
                    recomputeError?.response?.data?.detail ||
                    'Failed to rebuild the identity template.',
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
            setMarkingBadFace(null);
            setMarkBadNotes('');
        }
    }, [viewingCriminal]);

    useEffect(() => {
        if (!focusedCriminal || viewingCriminal?.id === focusedCriminal.id) {
            return;
        }

        setViewingCriminal(focusedCriminal);
    }, [focusedCriminal, viewingCriminal]);

    const clearFocusedCriminalParam = () => {
        if (!focusedCriminalId) {
            return;
        }

        const nextParams = new URLSearchParams(searchParams);
        nextParams.delete('criminal');
        setSearchParams(nextParams, { replace: true });
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
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
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
                        {hasRole(['admin', 'senior_officer']) && actionNotice.reviewCaseIds && actionNotice.reviewCaseIds.length > 0 ? (
                            <Button
                                variant="outline"
                                size="sm"
                                className="border-zinc-700"
                                onClick={() =>
                                    navigate(`/dashboard/review-queue?case=${actionNotice.reviewCaseIds?.[0]}`)
                                }
                            >
                                Open Review Queue
                            </Button>
                        ) : null}
                    </div>
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
                onOpenChange={(open) => {
                    if (!open) {
                        setViewingCriminal(undefined);
                        clearFocusedCriminalParam();
                    }
                }}
            >
                <DialogContent className="w-[min(96vw,78rem)] max-w-6xl gap-0 overflow-hidden p-0">
                    {viewingCriminal && (
                        <div className="grid h-[min(92vh,54rem)] grid-rows-[auto_minmax(0,1fr)]">
                            <DialogHeader className="border-b border-zinc-800 bg-zinc-950/90 px-6 py-5 pr-14">
                                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                                    <div className="space-y-2">
                                        <DialogTitle>
                                            {viewingCriminal.first_name} {viewingCriminal.last_name}
                                        </DialogTitle>
                                        <DialogDescription className="max-w-3xl">
                                            Full criminal profile, enrolled face history, and recognition-quality details. The header stays fixed and the
                                            profile body scrolls so the full record remains usable.
                                        </DialogDescription>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        <Badge variant={getThreatBadgeVariant(viewingCriminal.threat_level)}>
                                            Threat: {humanizeEnum(viewingCriminal.threat_level, 'Not set')}
                                        </Badge>
                                        <Badge variant={getStatusBadgeVariant(viewingCriminal.status)}>
                                            Status: {humanizeEnum(viewingCriminal.status, 'Not set')}
                                        </Badge>
                                        <Badge variant="outline">
                                            {isLoadingFaces ? 'Loading faces...' : `${viewingFaces.length} enrolled face${viewingFaces.length === 1 ? '' : 's'}`}
                                        </Badge>
                                    </div>
                                </div>
                            </DialogHeader>

                            <div className="min-h-0 overflow-y-auto px-6 py-6">
                                <div className="grid gap-6 xl:grid-cols-[minmax(18rem,24rem)_minmax(0,1fr)]">
                                    <div className="space-y-6 xl:sticky xl:top-0 xl:self-start">
                                        <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950/70">
                                            {viewingCriminal.primary_face_image_url ? (
                                                <img
                                                    src={buildBackendUrl(viewingCriminal.primary_face_image_url)}
                                                    alt={`${viewingCriminal.first_name} ${viewingCriminal.last_name}`}
                                                    className="w-full aspect-square object-cover object-top lg:h-auto lg:aspect-[4/3]"
                                                />
                                            ) : (
                                                <div className="flex h-72 items-center justify-center bg-zinc-950 text-sm text-zinc-500">
                                                    No primary face image enrolled
                                                </div>
                                            )}
                                            <div className="space-y-3 border-t border-zinc-800 p-5">
                                                <div>
                                                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
                                                        Identity Summary
                                                    </p>
                                                    <p className="mt-2 text-xl font-semibold text-white">
                                                        {viewingCriminal.first_name} {viewingCriminal.last_name}
                                                    </p>
                                                    <p className="mt-1 text-sm text-zinc-400">
                                                        NIC: {viewingCriminal.nic || 'Not provided'}
                                                    </p>
                                                </div>
                                                <div className="flex flex-wrap gap-2">
                                                    <Badge variant="outline">
                                                        Gender: {humanizeEnum(viewingCriminal.gender, 'Unknown')}
                                                    </Badge>
                                                    <Badge variant="outline">
                                                        DOB: {viewingCriminal.dob || 'Not provided'}
                                                    </Badge>
                                                    <Badge variant="outline">
                                                        Blood: {viewingCriminal.blood_type || 'Not provided'}
                                                    </Badge>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5">
                                            <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
                                                Profile Details
                                            </p>
                                            <div className="mt-4 grid gap-4 text-sm text-zinc-300 sm:grid-cols-2 xl:grid-cols-1">
                                                <div>
                                                    <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Aliases</p>
                                                    <p className="mt-1 text-sm text-zinc-200">{viewingCriminal.aliases || 'None recorded'}</p>
                                                </div>
                                                <div>
                                                    <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Last Known Address</p>
                                                    <p className="mt-1 text-sm text-zinc-200">
                                                        {viewingCriminal.last_known_address || 'Unknown'}
                                                    </p>
                                                </div>
                                                <div className="sm:col-span-2 xl:col-span-1">
                                                    <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Physical Description</p>
                                                    <p className="mt-1 text-sm leading-6 text-zinc-200">
                                                        {viewingCriminal.physical_description || 'None documented'}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-6">
                                        <div className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-950/50 p-5">
                                            <div className="flex flex-wrap items-start justify-between gap-3">
                                                <div>
                                                    <p className="text-sm font-semibold text-white">Enrolled Face Images</p>
                                                    <p className="text-xs text-zinc-500">
                                                        Stored mugshots and embedding metadata used by the recognition pipeline.
                                                    </p>
                                                </div>
                                                {hasRole(['admin', 'senior_officer', 'field_officer']) && (
                                                    <Button
                                                        type="button"
                                                        variant="outline"
                                                        size="sm"
                                                        className="border-zinc-700"
                                                        onClick={handleRecomputeTemplate}
                                                        disabled={recomputeTemplateMutation.isPending}
                                                    >
                                                        <RefreshCw
                                                            className={`mr-2 h-4 w-4 ${recomputeTemplateMutation.isPending ? 'animate-spin' : ''}`}
                                                        />
                                                        Recompute Template
                                                    </Button>
                                                )}
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
                                                    {viewingFaces.map((face: CriminalFace, index: number) => {
                                                        const qualityBadge = getFaceQualityBadge(face);
                                                        const faceWarnings = getStoredFaceWarnings(face);

                                                        return (
                                                            <div key={face.id} className="relative pl-8">
                                                                {index !== viewingFaces.length - 1 && (
                                                                    <div className="absolute left-[11px] top-8 h-[calc(100%-1rem)] w-px bg-zinc-800" />
                                                                )}
                                                                <div className="absolute left-0 top-2 flex h-6 w-6 items-center justify-center rounded-full border border-zinc-700 bg-zinc-950">
                                                                    <div
                                                                        className={`h-2.5 w-2.5 rounded-full ${face.is_primary ? 'bg-emerald-400' : 'bg-zinc-500'
                                                                            }`}
                                                                    />
                                                                </div>
                                                                <div className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950/60">
                                                                    <div className="grid gap-0 lg:grid-cols-[200px_minmax(0,1fr)]">
                                                                        <img
                                                                            src={buildBackendUrl(face.image_url)}
                                                                            alt="Enrolled criminal face"
                                                                            className="w-full aspect-square object-cover object-top lg:h-auto lg:aspect-[3/4] lg:self-start"
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
                                                                                    <Badge variant={qualityBadge.variant}>{qualityBadge.label}</Badge>
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

                                                                            <FaceTemplateSummary face={face} />
                                                                            <FaceOutlierWarning face={face} />

                                                                            <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
                                                                                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                                                                                    <div>
                                                                                        <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
                                                                                            Recognition Quality
                                                                                        </p>
                                                                                        <p className="mt-1 text-sm text-zinc-300">
                                                                                            Stored quality metrics that affect how reliably this face can match during identification.
                                                                                        </p>
                                                                                    </div>
                                                                                    {faceWarnings.length === 0 ? (
                                                                                        <div className="flex items-center gap-2 rounded-full border border-emerald-900/50 bg-emerald-950/30 px-3 py-1 text-xs text-emerald-200">
                                                                                            <ShieldCheck className="h-3.5 w-3.5" />
                                                                                            No active quality warnings
                                                                                        </div>
                                                                                    ) : (
                                                                                        <div className="flex items-center gap-2 rounded-full border border-amber-900/50 bg-amber-950/30 px-3 py-1 text-xs text-amber-200">
                                                                                            <ShieldAlert className="h-3.5 w-3.5" />
                                                                                            {faceWarnings.length} warning{faceWarnings.length === 1 ? '' : 's'} to review
                                                                                        </div>
                                                                                    )}
                                                                                </div>

                                                                                <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
                                                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                                                                                        <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Overall score</p>
                                                                                        <p className={`mt-2 text-lg font-semibold ${getMetricTone(face.quality.quality_score)}`}>
                                                                                            {formatMetricValue(face.quality.quality_score)}
                                                                                        </p>
                                                                                    </div>
                                                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                                                                                        <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Pose score</p>
                                                                                        <p className={`mt-2 text-lg font-semibold ${getMetricTone(face.quality.pose_score)}`}>
                                                                                            {formatMetricValue(face.quality.pose_score)}
                                                                                        </p>
                                                                                    </div>
                                                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                                                                                        <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Occlusion score</p>
                                                                                        <p className={`mt-2 text-lg font-semibold ${getMetricTone(face.quality.occlusion_score)}`}>
                                                                                            {formatMetricValue(face.quality.occlusion_score)}
                                                                                        </p>
                                                                                    </div>
                                                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                                                                                        <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Blur score</p>
                                                                                        <p className={`mt-2 text-lg font-semibold ${getMetricTone(face.quality.blur_score)}`}>
                                                                                            {formatMetricValue(face.quality.blur_score)}
                                                                                        </p>
                                                                                    </div>
                                                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                                                                                        <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Brightness</p>
                                                                                        <p className={`mt-2 text-lg font-semibold ${getMetricTone(face.quality.brightness_score)}`}>
                                                                                            {formatMetricValue(face.quality.brightness_score)}
                                                                                        </p>
                                                                                    </div>
                                                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                                                                                        <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Face area</p>
                                                                                        <p className={`mt-2 text-lg font-semibold ${getMetricTone(face.quality.face_area_ratio * 100)}`}>
                                                                                            {formatMetricValue(face.quality.face_area_ratio * 100, '%')}
                                                                                        </p>
                                                                                    </div>
                                                                                </div>

                                                                                {faceWarnings.length > 0 && (
                                                                                    <div className="mt-4 rounded-lg border border-amber-900/50 bg-amber-950/20 p-3">
                                                                                        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-amber-300">
                                                                                            Recognition warnings
                                                                                        </p>
                                                                                        <div className="mt-3 flex flex-wrap gap-2">
                                                                                            {faceWarnings.map((warning) => (
                                                                                                <Badge key={warning} variant="warning" className="font-medium">
                                                                                                    {humanizeQualityLabel(warning)}
                                                                                                </Badge>
                                                                                            ))}
                                                                                        </div>
                                                                                    </div>
                                                                                )}
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
                                                                                            disabled={setPrimaryFaceMutation.isPending || face.exclude_from_template}
                                                                                        >
                                                                                            Set Primary
                                                                                        </Button>
                                                                                    )}
                                                                                    {!face.exclude_from_template && (
                                                                                        <Button
                                                                                            type="button"
                                                                                            variant="outline"
                                                                                            size="sm"
                                                                                            className="border-amber-900/50 text-amber-300 hover:bg-amber-950/30"
                                                                                            onClick={() => {
                                                                                                setMarkingBadFace(face);
                                                                                                setMarkBadNotes(face.operator_review_notes || '');
                                                                                            }}
                                                                                            disabled={markBadFaceMutation.isPending}
                                                                                        >
                                                                                            <Ban className="mr-2 h-4 w-4" />
                                                                                            Mark Bad
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
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>

                                        {hasRole(['admin', 'senior_officer', 'field_officer']) && (
                                            <div className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-950/50 p-5">
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
                                                        disabled={
                                                            !existingFaceFile ||
                                                            uploadFaceMutation.isPending ||
                                                            setPrimaryFaceMutation.isPending
                                                        }
                                                        className="bg-primary text-primary-foreground hover:bg-primary/90"
                                                    >
                                                        {uploadFaceMutation.isPending ? 'Uploading...' : 'Upload Face Image'}
                                                    </Button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
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

            <Dialog
                open={!!markingBadFace}
                onOpenChange={(open) => {
                    if (!open) {
                        setMarkingBadFace(null);
                        setMarkBadNotes('');
                    }
                }}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Mark Face Enrollment As Bad</DialogTitle>
                        <DialogDescription>
                            Exclude this enrolled face from future identity-template rebuilds. The face record stays on the profile for audit history, but it will no longer be used for matching.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3">
                        <p className="text-sm text-zinc-300">
                            {markingBadFace?.is_primary
                                ? 'This face is currently primary. If another eligible face exists, it will be promoted automatically.'
                                : 'This face is not primary and will simply be excluded from the template.'}
                        </p>
                        <div className="space-y-2">
                            <label className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
                                Operator Notes
                            </label>
                            <Input
                                value={markBadNotes}
                                onChange={(event) => setMarkBadNotes(event.target.value)}
                                placeholder="Optional note, e.g. wrong person or blurred crop"
                                className="border-zinc-700 bg-zinc-950"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setMarkingBadFace(null);
                                setMarkBadNotes('');
                            }}
                            disabled={markBadFaceMutation.isPending}
                            className="border-zinc-700"
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleConfirmMarkFaceAsBad}
                            disabled={markBadFaceMutation.isPending}
                            className="bg-amber-600 text-black hover:bg-amber-500"
                        >
                            {markBadFaceMutation.isPending ? 'Saving...' : 'Mark As Bad'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
