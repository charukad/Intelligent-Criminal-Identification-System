import { useEffect, useMemo, useRef, useState } from 'react';
import {
    AlertTriangle,
    CheckCircle2,
    Crop,
    ImagePlus,
    Loader2,
    ScanFace,
    Star,
    Trash2,
} from 'lucide-react';

import { criminalsApi } from '@/api/criminals';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { FaceQualityPreview } from '@/types/criminal';
import { cn } from '@/lib/utils';
import {
    applyCropPreset,
    createFaceCropDrafts,
    renderCroppedFaceFile,
    revokeFaceCropDrafts,
    updateFaceCropDraft,
    type FaceCropDraft,
} from '@/lib/faceCrop';

export interface FaceEnrollmentQualitySummary {
    total: number;
    pending: number;
    rejected: number;
    warnings: number;
}

interface DraftQualityState {
    signature: string;
    status: 'analyzing' | 'ready' | 'error';
    preview?: FaceQualityPreview;
    error?: string;
}

interface FaceEnrollmentPickerProps {
    drafts: FaceCropDraft[];
    primaryIndex: number;
    disabled?: boolean;
    onDraftsChange: (drafts: FaceCropDraft[]) => void;
    onPrimaryIndexChange: (index: number) => void;
    onQualitySummaryChange?: (summary: FaceEnrollmentQualitySummary) => void;
}

function formatPercent(value: number, total: number) {
    return `${((value / total) * 100).toFixed(2)}%`;
}

function getDraftSignature(draft: FaceCropDraft) {
    return [
        draft.sourceFile.name,
        draft.sourceFile.size,
        draft.sourceFile.lastModified,
        draft.cropX,
        draft.cropY,
        draft.cropWidth,
        draft.cropHeight,
    ].join(':');
}

function humanizeReason(value: string) {
    return value.replace(/_/g, ' ');
}

function getPreviewBadge(preview?: FaceQualityPreview) {
    if (!preview) {
        return { label: 'Pending', variant: 'outline' as const };
    }
    if (preview.status === 'accepted') {
        return { label: 'Ready', variant: 'success' as const };
    }
    if (preview.status === 'accepted_with_warnings') {
        return { label: 'Warnings', variant: 'warning' as const };
    }
    return { label: 'Rejected', variant: 'destructive' as const };
}

export function FaceEnrollmentPicker({
    drafts,
    primaryIndex,
    disabled = false,
    onDraftsChange,
    onPrimaryIndexChange,
    onQualitySummaryChange,
}: FaceEnrollmentPickerProps) {
    const [isPreparing, setIsPreparing] = useState(false);
    const [selectionError, setSelectionError] = useState<string | null>(null);
    const [activeDraftId, setActiveDraftId] = useState<string | null>(null);
    const [qualityStates, setQualityStates] = useState<Record<string, DraftQualityState>>({});
    const latestSignaturesRef = useRef<Record<string, string>>({});

    const activeDraft = useMemo(
        () => drafts.find((draft) => draft.id === activeDraftId) ?? drafts[0] ?? null,
        [drafts, activeDraftId]
    );
    const activeQualityState = activeDraft ? qualityStates[activeDraft.id] : undefined;
    const activePreview = activeQualityState?.preview;

    useEffect(() => {
        if (drafts.length === 0) {
            setActiveDraftId(null);
            setQualityStates({});
            latestSignaturesRef.current = {};
            return;
        }

        if (!drafts.some((draft) => draft.id === activeDraftId)) {
            setActiveDraftId(drafts[0].id);
        }
    }, [drafts, activeDraftId]);

    useEffect(() => {
        const activeIds = new Set(drafts.map((draft) => draft.id));
        latestSignaturesRef.current = Object.fromEntries(
            drafts.map((draft) => [draft.id, getDraftSignature(draft)])
        );

        setQualityStates((prev) =>
            Object.fromEntries(
                Object.entries(prev).filter(([draftId]) => activeIds.has(draftId))
            )
        );

        const draftsToAnalyze = drafts.filter((draft) => {
            const signature = latestSignaturesRef.current[draft.id];
            return qualityStates[draft.id]?.signature !== signature;
        });

        if (draftsToAnalyze.length === 0) {
            return;
        }

        setQualityStates((prev) => {
            const next = { ...prev };
            for (const draft of draftsToAnalyze) {
                next[draft.id] = {
                    signature: latestSignaturesRef.current[draft.id],
                    status: 'analyzing',
                };
            }
            return next;
        });

        let cancelled = false;
        const timeoutId = window.setTimeout(() => {
            const runPreview = async () => {
                await Promise.all(
                    draftsToAnalyze.map(async (draft) => {
                        const signature = latestSignaturesRef.current[draft.id];
                        try {
                            const croppedFile = await renderCroppedFaceFile(draft);
                            const preview = await criminalsApi.previewFaceQuality(croppedFile);
                            if (cancelled || latestSignaturesRef.current[draft.id] !== signature) {
                                return;
                            }

                            setQualityStates((prev) => ({
                                ...prev,
                                [draft.id]: {
                                    signature,
                                    status: 'ready',
                                    preview,
                                },
                            }));
                        } catch (error: any) {
                            if (cancelled || latestSignaturesRef.current[draft.id] !== signature) {
                                return;
                            }

                            setQualityStates((prev) => ({
                                ...prev,
                                [draft.id]: {
                                    signature,
                                    status: 'error',
                                    error:
                                        error?.response?.data?.detail ||
                                        'Quality preview failed. Try adjusting the crop.',
                                },
                            }));
                        }
                    })
                );
            };

            void runPreview();
        }, 350);

        return () => {
            cancelled = true;
            window.clearTimeout(timeoutId);
        };
    }, [drafts]);

    const qualitySummary = useMemo<FaceEnrollmentQualitySummary>(() => {
        const summary = {
            total: drafts.length,
            pending: 0,
            rejected: 0,
            warnings: 0,
        };

        for (const draft of drafts) {
            const state = qualityStates[draft.id];
            if (!state || state.status === 'analyzing') {
                summary.pending += 1;
                continue;
            }

            if (state.status === 'error') {
                summary.rejected += 1;
                continue;
            }

            if (state.preview?.status === 'rejected') {
                summary.rejected += 1;
            } else if (state.preview?.status === 'accepted_with_warnings') {
                summary.warnings += 1;
            }
        }

        return summary;
    }, [drafts, qualityStates]);

    useEffect(() => {
        onQualitySummaryChange?.(qualitySummary);
    }, [onQualitySummaryChange, qualitySummary]);

    const handleFileSelection = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(event.target.files ?? []);
        if (files.length === 0) {
            return;
        }

        setIsPreparing(true);
        setSelectionError(null);
        try {
            const newDrafts = await createFaceCropDrafts(files);
            if (newDrafts.length === 0) {
                setSelectionError('Only image files can be added for face enrollment.');
                return;
            }

            const nextDrafts = [...drafts, ...newDrafts];
            onDraftsChange(nextDrafts);
            if (primaryIndex < 0) {
                onPrimaryIndexChange(0);
            }
            if (!activeDraftId && nextDrafts.length > 0) {
                setActiveDraftId(nextDrafts[0].id);
            }
        } catch (error) {
            console.error(error);
            setSelectionError('Failed to prepare one or more selected images.');
        } finally {
            event.target.value = '';
            setIsPreparing(false);
        }
    };

    const handleDraftUpdate = (
        patch: Partial<Pick<FaceCropDraft, 'cropX' | 'cropY' | 'cropWidth' | 'cropHeight'>>
    ) => {
        if (!activeDraft) {
            return;
        }

        onDraftsChange(
            drafts.map((draft) => (draft.id === activeDraft.id ? updateFaceCropDraft(draft, patch) : draft))
        );
    };

    const handlePreset = (preset: 'reset' | 'square' | 'portrait' | 'landscape') => {
        if (!activeDraft) {
            return;
        }

        onDraftsChange(
            drafts.map((draft) => (draft.id === activeDraft.id ? applyCropPreset(draft, preset) : draft))
        );
    };

    const handleRemoveDraft = (draftId: string) => {
        const draftToRemove = drafts.find((draft) => draft.id === draftId);
        if (!draftToRemove) {
            return;
        }

        revokeFaceCropDrafts([draftToRemove]);
        const removedIndex = drafts.findIndex((draft) => draft.id === draftId);
        const nextDrafts = drafts.filter((draft) => draft.id !== draftId);
        onDraftsChange(nextDrafts);
        setQualityStates((prev) => {
            const next = { ...prev };
            delete next[draftId];
            return next;
        });

        if (nextDrafts.length === 0) {
            onPrimaryIndexChange(-1);
            return;
        }

        if (primaryIndex === removedIndex) {
            onPrimaryIndexChange(0);
        } else if (removedIndex < primaryIndex) {
            onPrimaryIndexChange(primaryIndex - 1);
        }
    };

    return (
        <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
            <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                    <h3 className="text-sm font-semibold text-zinc-200">Face Enrollment</h3>
                    <p className="mt-1 text-xs text-zinc-500">
                        Add multiple mugshots now. Every cropped image is quality-checked before it reaches the recognition pipeline.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                    <div className="rounded-full border border-zinc-800 px-3 py-1 text-zinc-400">
                        {drafts.length} image{drafts.length === 1 ? '' : 's'} selected
                    </div>
                    {qualitySummary.pending > 0 && (
                        <div className="rounded-full border border-blue-900/70 bg-blue-950/50 px-3 py-1 text-blue-300">
                            {qualitySummary.pending} analyzing
                        </div>
                    )}
                    {qualitySummary.warnings > 0 && (
                        <div className="rounded-full border border-amber-900/70 bg-amber-950/50 px-3 py-1 text-amber-300">
                            {qualitySummary.warnings} warning{qualitySummary.warnings === 1 ? '' : 's'}
                        </div>
                    )}
                    {qualitySummary.rejected > 0 && (
                        <div className="rounded-full border border-red-900/70 bg-red-950/50 px-3 py-1 text-red-300">
                            {qualitySummary.rejected} rejected
                        </div>
                    )}
                </div>
            </div>

            <div className="space-y-2">
                <Label htmlFor="face_images">Mugshot Images</Label>
                <Input
                    id="face_images"
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/webp"
                    className="bg-zinc-800 border-zinc-600 file:text-zinc-300"
                    onChange={handleFileSelection}
                    disabled={disabled || isPreparing}
                />
                <p className="text-xs text-zinc-500">
                    Select front, left, right, and other clean angles. Choose one primary image for the active profile thumbnail.
                </p>
                {selectionError && <p className="text-xs text-red-400">{selectionError}</p>}
            </div>

            {drafts.length === 0 ? (
                <div className="rounded-lg border border-dashed border-zinc-700 bg-zinc-900/40 p-6 text-center text-sm text-zinc-500">
                    <ImagePlus className="mx-auto mb-3 h-7 w-7 text-zinc-600" />
                    Add one or more face images to unlock crop controls and batch enrollment.
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        {drafts.map((draft, index) => {
                            const state = qualityStates[draft.id];
                            const badge = getPreviewBadge(state?.preview);
                            const isAnalyzing = state?.status === 'analyzing' || !state;
                            const isError = state?.status === 'error';
                            return (
                                <button
                                    key={draft.id}
                                    type="button"
                                    onClick={() => setActiveDraftId(draft.id)}
                                    className={cn(
                                        'overflow-hidden rounded-lg border text-left transition-colors',
                                        activeDraft?.id === draft.id
                                            ? 'border-emerald-500 bg-emerald-950/20'
                                            : 'border-zinc-800 bg-zinc-900/60 hover:border-zinc-700'
                                    )}
                                >
                                    <img
                                        src={draft.previewUrl}
                                        alt={draft.sourceFile.name}
                                        className="h-32 w-full object-cover"
                                    />
                                    <div className="space-y-3 p-3">
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="min-w-0">
                                                <p className="truncate text-sm font-medium text-zinc-100">{draft.sourceFile.name}</p>
                                                <p className="text-xs text-zinc-500">
                                                    {draft.naturalWidth} x {draft.naturalHeight}
                                                </p>
                                            </div>
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 text-zinc-400 hover:text-red-400"
                                                onClick={(event) => {
                                                    event.stopPropagation();
                                                    handleRemoveDraft(draft.id);
                                                }}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>

                                        <div className="flex flex-wrap items-center gap-2">
                                            <Button
                                                type="button"
                                                variant={primaryIndex === index ? 'default' : 'outline'}
                                                size="sm"
                                                className={cn(
                                                    'h-8 text-xs',
                                                    primaryIndex === index
                                                        ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                                                        : 'border-zinc-700 text-zinc-300'
                                                )}
                                                onClick={(event) => {
                                                    event.stopPropagation();
                                                    onPrimaryIndexChange(index);
                                                }}
                                            >
                                                <Star className="mr-1.5 h-3.5 w-3.5" />
                                                {primaryIndex === index ? 'Primary' : 'Set Primary'}
                                            </Button>
                                            <Badge variant={badge.variant}>{badge.label}</Badge>
                                            <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-[11px] text-zinc-500">
                                                Crop {draft.cropWidth} x {draft.cropHeight}
                                            </span>
                                        </div>

                                        {isAnalyzing && (
                                            <div className="flex items-center gap-2 text-xs text-blue-300">
                                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                Running quality preview...
                                            </div>
                                        )}
                                        {isError && (
                                            <div className="flex items-center gap-2 text-xs text-red-300">
                                                <AlertTriangle className="h-3.5 w-3.5" />
                                                {state.error}
                                            </div>
                                        )}
                                        {state?.status === 'ready' && state.preview && (
                                            <div
                                                className={cn(
                                                    'rounded-md border px-2 py-2 text-xs',
                                                    state.preview.status === 'rejected'
                                                        ? 'border-red-900/60 bg-red-950/40 text-red-200'
                                                        : state.preview.status === 'accepted_with_warnings'
                                                            ? 'border-amber-900/60 bg-amber-950/40 text-amber-200'
                                                            : 'border-emerald-900/60 bg-emerald-950/40 text-emerald-200'
                                                )}
                                            >
                                                {state.preview.message}
                                            </div>
                                        )}
                                    </div>
                                </button>
                            );
                        })}
                    </div>

                    {activeDraft && (
                        <div className="grid gap-5 xl:grid-cols-[1.45fr_0.9fr]">
                            <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                        <p className="text-sm font-medium text-white">Crop Composer</p>
                                        <p className="text-xs text-zinc-500">
                                            Active image: {activeDraft.sourceFile.name}
                                        </p>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        <Button type="button" size="sm" variant="outline" className="border-zinc-700 text-zinc-300" onClick={() => handlePreset('reset')}>
                                            Reset
                                        </Button>
                                        <Button type="button" size="sm" variant="outline" className="border-zinc-700 text-zinc-300" onClick={() => handlePreset('square')}>
                                            Square
                                        </Button>
                                        <Button type="button" size="sm" variant="outline" className="border-zinc-700 text-zinc-300" onClick={() => handlePreset('portrait')}>
                                            Portrait
                                        </Button>
                                        <Button type="button" size="sm" variant="outline" className="border-zinc-700 text-zinc-300" onClick={() => handlePreset('landscape')}>
                                            Landscape
                                        </Button>
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <div className="relative overflow-hidden rounded-xl border border-zinc-800 bg-black/60">
                                        <div className="aspect-[4/3]">
                                            <img
                                                src={activeDraft.previewUrl}
                                                alt="Crop source"
                                                className="h-full w-full object-contain"
                                            />

                                            <div
                                                className="pointer-events-none absolute border-2 border-emerald-400 shadow-[0_0_0_999px_rgba(0,0,0,0.58)]"
                                                style={{
                                                    left: formatPercent(activeDraft.cropX, activeDraft.naturalWidth),
                                                    top: formatPercent(activeDraft.cropY, activeDraft.naturalHeight),
                                                    width: formatPercent(activeDraft.cropWidth, activeDraft.naturalWidth),
                                                    height: formatPercent(activeDraft.cropHeight, activeDraft.naturalHeight),
                                                }}
                                            >
                                                <div className="absolute left-2 top-2 rounded-full bg-emerald-500/90 px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.2em] text-black">
                                                    Crop
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="grid gap-4 md:grid-cols-2">
                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between text-xs text-zinc-500">
                                                <span>Horizontal Start</span>
                                                <span>{activeDraft.cropX}px</span>
                                            </div>
                                            <input
                                                type="range"
                                                min={0}
                                                max={Math.max(0, activeDraft.naturalWidth - activeDraft.cropWidth)}
                                                value={activeDraft.cropX}
                                                onChange={(event) => handleDraftUpdate({ cropX: Number(event.target.value) })}
                                                className="w-full accent-emerald-500"
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between text-xs text-zinc-500">
                                                <span>Vertical Start</span>
                                                <span>{activeDraft.cropY}px</span>
                                            </div>
                                            <input
                                                type="range"
                                                min={0}
                                                max={Math.max(0, activeDraft.naturalHeight - activeDraft.cropHeight)}
                                                value={activeDraft.cropY}
                                                onChange={(event) => handleDraftUpdate({ cropY: Number(event.target.value) })}
                                                className="w-full accent-emerald-500"
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between text-xs text-zinc-500">
                                                <span>Crop Width</span>
                                                <span>{activeDraft.cropWidth}px</span>
                                            </div>
                                            <input
                                                type="range"
                                                min={80}
                                                max={activeDraft.naturalWidth}
                                                value={activeDraft.cropWidth}
                                                onChange={(event) => handleDraftUpdate({ cropWidth: Number(event.target.value) })}
                                                className="w-full accent-emerald-500"
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between text-xs text-zinc-500">
                                                <span>Crop Height</span>
                                                <span>{activeDraft.cropHeight}px</span>
                                            </div>
                                            <input
                                                type="range"
                                                min={80}
                                                max={activeDraft.naturalHeight}
                                                value={activeDraft.cropHeight}
                                                onChange={(event) => handleDraftUpdate({ cropHeight: Number(event.target.value) })}
                                                className="w-full accent-emerald-500"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
                                <div className="flex items-center gap-2">
                                    <Crop className="h-4 w-4 text-emerald-400" />
                                    <p className="text-sm font-medium text-white">Enrollment Preview</p>
                                </div>

                                <div className="overflow-hidden rounded-xl border border-zinc-800 bg-black/70">
                                    <div
                                        className="relative mx-auto max-h-[360px] w-full overflow-hidden"
                                        style={{ aspectRatio: `${activeDraft.cropWidth} / ${activeDraft.cropHeight}` }}
                                    >
                                        <img
                                            src={activeDraft.previewUrl}
                                            alt="Cropped enrollment preview"
                                            className="absolute max-w-none"
                                            style={{
                                                left: `-${(activeDraft.cropX / activeDraft.cropWidth) * 100}%`,
                                                top: `-${(activeDraft.cropY / activeDraft.cropHeight) * 100}%`,
                                                width: `${(activeDraft.naturalWidth / activeDraft.cropWidth) * 100}%`,
                                                height: `${(activeDraft.naturalHeight / activeDraft.cropHeight) * 100}%`,
                                            }}
                                        />
                                    </div>
                                </div>

                                <div className="grid gap-3 text-xs text-zinc-500 sm:grid-cols-2">
                                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                                        <p className="text-zinc-400">Primary Enrollment</p>
                                        <p className="mt-1 text-sm text-white">
                                            {primaryIndex >= 0 ? drafts[primaryIndex]?.sourceFile.name ?? 'None selected' : 'None selected'}
                                        </p>
                                    </div>
                                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                                        <p className="text-zinc-400">Stored Crop Size</p>
                                        <p className="mt-1 text-sm text-white">
                                            {activeDraft.cropWidth} x {activeDraft.cropHeight}
                                        </p>
                                    </div>
                                </div>

                                <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
                                    <div className="mb-3 flex items-center gap-2">
                                        <ScanFace className="h-4 w-4 text-blue-400" />
                                        <p className="text-sm font-medium text-white">Quality Preview</p>
                                    </div>

                                    {!activeQualityState || activeQualityState.status === 'analyzing' ? (
                                        <div className="flex items-center gap-2 text-sm text-blue-300">
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                            Analyzing the cropped face...
                                        </div>
                                    ) : activeQualityState.status === 'error' ? (
                                        <div className="rounded-md border border-red-900/60 bg-red-950/40 p-3 text-sm text-red-200">
                                            {activeQualityState.error}
                                        </div>
                                    ) : activePreview ? (
                                        <div className="space-y-3">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <Badge variant={getPreviewBadge(activePreview).variant}>
                                                    {getPreviewBadge(activePreview).label}
                                                </Badge>
                                                <span className="text-xs text-zinc-500">
                                                    Detected faces: {activePreview.detected_face_count}
                                                </span>
                                            </div>

                                            <div
                                                className={cn(
                                                    'rounded-md border p-3 text-sm',
                                                    activePreview.status === 'rejected'
                                                        ? 'border-red-900/60 bg-red-950/40 text-red-100'
                                                        : activePreview.status === 'accepted_with_warnings'
                                                            ? 'border-amber-900/60 bg-amber-950/40 text-amber-100'
                                                            : 'border-emerald-900/60 bg-emerald-950/40 text-emerald-100'
                                                )}
                                            >
                                                <div className="flex items-start gap-2">
                                                    {activePreview.status === 'rejected' ? (
                                                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                                                    ) : (
                                                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                                                    )}
                                                    <div>
                                                        <p className="font-medium">{activePreview.message}</p>
                                                        <p className="mt-1 text-xs opacity-80">
                                                            Decision: {humanizeReason(activePreview.decision_reason)}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>

                                            {activePreview.quality && (
                                                <div className="grid gap-3 text-xs text-zinc-400 sm:grid-cols-2 xl:grid-cols-3">
                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                                                        <p>Quality score</p>
                                                        <p className="mt-1 text-lg font-semibold text-zinc-100">
                                                            {activePreview.quality.quality_score.toFixed(1)}
                                                        </p>
                                                    </div>
                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                                                        <p>Blur score</p>
                                                        <p className="mt-1 text-lg font-semibold text-zinc-100">
                                                            {activePreview.quality.blur_score.toFixed(1)}
                                                        </p>
                                                    </div>
                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                                                        <p>Brightness</p>
                                                        <p className="mt-1 text-lg font-semibold text-zinc-100">
                                                            {activePreview.quality.brightness_score.toFixed(1)}
                                                        </p>
                                                    </div>
                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                                                        <p>Face area ratio</p>
                                                        <p className="mt-1 text-lg font-semibold text-zinc-100">
                                                            {(activePreview.quality.face_area_ratio * 100).toFixed(2)}%
                                                        </p>
                                                    </div>
                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                                                        <p>Pose score</p>
                                                        <p className="mt-1 text-lg font-semibold text-zinc-100">
                                                            {activePreview.quality.pose_score.toFixed(1)}
                                                        </p>
                                                    </div>
                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                                                        <p>Occlusion score</p>
                                                        <p className="mt-1 text-lg font-semibold text-zinc-100">
                                                            {activePreview.quality.occlusion_score.toFixed(1)}
                                                        </p>
                                                    </div>
                                                </div>
                                            )}

                                            {activePreview.quality?.warnings && activePreview.quality.warnings.length > 0 && (
                                                <div className="rounded-md border border-amber-900/60 bg-amber-950/30 p-3">
                                                    <p className="text-xs font-medium uppercase tracking-wide text-amber-300">
                                                        Quality warnings
                                                    </p>
                                                    <ul className="mt-2 space-y-1 text-sm text-amber-100">
                                                        {activePreview.quality.warnings.map((warning) => (
                                                            <li key={warning}>• {humanizeReason(warning)}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    ) : null}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
