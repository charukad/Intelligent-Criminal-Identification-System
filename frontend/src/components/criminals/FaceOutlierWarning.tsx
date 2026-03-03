import { AlertTriangle } from 'lucide-react';

import type { CriminalFace } from '@/types/criminal';

interface FaceOutlierWarningProps {
    face: CriminalFace;
}

function formatDistance(value?: number | null) {
    if (value === null || value === undefined) {
        return 'n/a';
    }
    return value.toFixed(6);
}

export function FaceOutlierWarning({ face }: FaceOutlierWarningProps) {
    if (face.exclude_from_template || face.operator_review_status === 'marked_bad') {
        return (
            <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-4 text-red-200">
                <div className="flex items-start gap-3">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="space-y-1 text-sm">
                        <p className="font-medium">Operator removed this face from active matching</p>
                        <p>
                            This enrollment stays on the profile for traceability, but it will not be used when rebuilding the criminal identity template.
                        </p>
                        {face.operator_review_notes ? (
                            <p className="text-xs opacity-90">Notes: {face.operator_review_notes}</p>
                        ) : null}
                    </div>
                </div>
            </div>
        );
    }

    if (face.template_role !== 'outlier' && face.template_role !== 'archived') {
        return null;
    }

    const tone =
        face.template_role === 'outlier'
            ? 'border-amber-900/50 bg-amber-950/20 text-amber-200'
            : 'border-zinc-800 bg-zinc-950/50 text-zinc-300';
    const title =
        face.template_role === 'outlier' ? 'Excluded from active template' : 'Stored as history only';
    const detail =
        face.template_role === 'outlier'
            ? 'This face is far enough from the criminal template that it is treated as an outlier during recognition.'
            : 'This face remains on the record, but it is not part of the current identity template used for ranking.';

    return (
        <div className={`rounded-lg border p-4 ${tone}`}>
            <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <div className="space-y-1 text-sm">
                    <p className="font-medium">{title}</p>
                    <p>{detail}</p>
                    <p className="font-mono text-xs opacity-90">template_distance={formatDistance(face.template_distance)}</p>
                </div>
            </div>
        </div>
    );
}
