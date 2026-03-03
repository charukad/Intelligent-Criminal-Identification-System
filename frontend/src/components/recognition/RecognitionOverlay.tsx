import { useState } from 'react';

import type { RecognitionOverlayFace } from '@/types/recognition';

interface RecognitionOverlayProps {
    imageUrl: string;
    faces?: RecognitionOverlayFace[];
    alt?: string;
}

function getFaceTone(status: RecognitionOverlayFace['status']) {
    if (status === 'match') {
        return {
            border: 'border-emerald-400',
            label: 'bg-emerald-500/90 text-black',
        };
    }
    if (status === 'possible_match') {
        return {
            border: 'border-amber-400',
            label: 'bg-amber-400/90 text-black',
        };
    }
    return {
        border: 'border-zinc-300',
        label: 'bg-zinc-900/85 text-zinc-100',
    };
}

export function RecognitionOverlay({
    imageUrl,
    faces = [],
    alt = 'Recognition preview',
}: RecognitionOverlayProps) {
    const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(null);

    return (
        <div className="space-y-3">
            <div className="relative overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950/50">
                <img
                    src={imageUrl}
                    alt={alt}
                    className="max-h-[420px] w-full object-contain"
                    onLoad={(event) =>
                        setNaturalSize({
                            width: event.currentTarget.naturalWidth,
                            height: event.currentTarget.naturalHeight,
                        })
                    }
                />
                {naturalSize ? (
                    <div className="pointer-events-none absolute inset-0">
                        {faces.map((face, index) => {
                            const tone = getFaceTone(face.status);
                            const [x, y, width, height] = face.box;

                            return (
                                <div
                                    key={`${face.box.join('-')}-${index}`}
                                    className={`absolute border-2 shadow-[0_0_0_1px_rgba(0,0,0,0.35)] ${tone.border} ${face.selected ? 'ring-2 ring-white/70' : ''}`}
                                    style={{
                                        left: `${(x / naturalSize.width) * 100}%`,
                                        top: `${(y / naturalSize.height) * 100}%`,
                                        width: `${(width / naturalSize.width) * 100}%`,
                                        height: `${(height / naturalSize.height) * 100}%`,
                                    }}
                                >
                                    <div className={`absolute left-0 top-0 rounded-br px-2 py-1 text-[11px] font-semibold shadow ${tone.label}`}>
                                        {face.label}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : null}
            </div>

            {faces.length > 0 ? (
                <div className="flex flex-wrap gap-2 text-xs text-zinc-400">
                    <span className="rounded-full border border-emerald-900/60 bg-emerald-950/30 px-3 py-1 text-emerald-200">
                        Green: accepted match
                    </span>
                    <span className="rounded-full border border-amber-900/60 bg-amber-950/30 px-3 py-1 text-amber-200">
                        Amber: possible match
                    </span>
                    <span className="rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-zinc-300">
                        Gray: rejected or unknown
                    </span>
                    <span className="rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-zinc-300">
                        White ring: selected face for single mode
                    </span>
                </div>
            ) : null}
        </div>
    );
}
