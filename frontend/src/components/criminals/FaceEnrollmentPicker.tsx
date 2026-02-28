import { useEffect, useMemo, useState } from 'react';
import { Crop, ImagePlus, Star, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import {
    applyCropPreset,
    createFaceCropDrafts,
    revokeFaceCropDrafts,
    updateFaceCropDraft,
    type FaceCropDraft,
} from '@/lib/faceCrop';

interface FaceEnrollmentPickerProps {
    drafts: FaceCropDraft[];
    primaryIndex: number;
    disabled?: boolean;
    onDraftsChange: (drafts: FaceCropDraft[]) => void;
    onPrimaryIndexChange: (index: number) => void;
}

function formatPercent(value: number, total: number) {
    return `${((value / total) * 100).toFixed(2)}%`;
}

export function FaceEnrollmentPicker({
    drafts,
    primaryIndex,
    disabled = false,
    onDraftsChange,
    onPrimaryIndexChange,
}: FaceEnrollmentPickerProps) {
    const [isPreparing, setIsPreparing] = useState(false);
    const [selectionError, setSelectionError] = useState<string | null>(null);
    const [activeDraftId, setActiveDraftId] = useState<string | null>(null);

    const activeDraft = useMemo(
        () => drafts.find((draft) => draft.id === activeDraftId) ?? drafts[0] ?? null,
        [drafts, activeDraftId]
    );

    useEffect(() => {
        if (drafts.length === 0) {
            setActiveDraftId(null);
            return;
        }

        if (!drafts.some((draft) => draft.id === activeDraftId)) {
            setActiveDraftId(drafts[0].id);
        }
    }, [drafts, activeDraftId]);

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

    const handleDraftUpdate = (patch: Partial<Pick<FaceCropDraft, 'cropX' | 'cropY' | 'cropWidth' | 'cropHeight'>>) => {
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
                        Add multiple mugshots now. Every cropped image will be sent through face enrollment and stored as a real recognition embedding.
                    </p>
                </div>
                <div className="rounded-full border border-zinc-800 px-3 py-1 text-xs text-zinc-400">
                    {drafts.length} image{drafts.length === 1 ? '' : 's'} selected
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
                        {drafts.map((draft, index) => (
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
                                        <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-[11px] text-zinc-500">
                                            Crop {draft.cropWidth} x {draft.cropHeight}
                                        </span>
                                    </div>
                                </div>
                            </button>
                        ))}
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
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
