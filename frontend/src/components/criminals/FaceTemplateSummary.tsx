import { Badge } from '@/components/ui/badge';
import type { CriminalFace } from '@/types/criminal';

interface FaceTemplateSummaryProps {
    face: CriminalFace;
}

function getRoleCopy(role: CriminalFace['template_role']) {
    if (role === 'primary') {
        return {
            label: 'Primary template anchor',
            variant: 'success' as const,
            detail: 'This face is the anchor record used to represent the criminal identity template.',
        };
    }
    if (role === 'support') {
        return {
            label: 'Support template face',
            variant: 'info' as const,
            detail: 'This face contributes to the active identity template and broadens pose or lighting coverage.',
        };
    }
    if (role === 'outlier') {
        return {
            label: 'Template outlier',
            variant: 'warning' as const,
            detail: 'This face was kept in history but excluded from the active identity template because it does not cluster well.',
        };
    }
    return {
        label: 'Archived from template',
        variant: 'outline' as const,
        detail: 'This face is stored for history, but it is not part of the active identity template used for ranking.',
    };
}

function formatDistance(value?: number | null) {
    if (value === null || value === undefined) {
        return 'n/a';
    }
    return value.toFixed(6);
}

export function FaceTemplateSummary({ face }: FaceTemplateSummaryProps) {
    if (face.exclude_from_template || face.operator_review_status === 'marked_bad') {
        return (
            <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-xs font-medium uppercase tracking-[0.18em] text-red-300">
                            Template Membership
                        </p>
                        <p className="mt-1 text-sm text-red-100">
                            This face was manually excluded from the active identity template by an operator review action.
                        </p>
                        {face.operator_review_notes ? (
                            <p className="mt-2 text-xs text-red-200/80">Notes: {face.operator_review_notes}</p>
                        ) : null}
                    </div>
                    <Badge variant="destructive">manually excluded</Badge>
                </div>
                <div className="mt-4 grid gap-3 text-xs text-zinc-400 sm:grid-cols-3">
                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                        <p className="uppercase tracking-[0.14em] text-zinc-500">Operator Status</p>
                        <p className="mt-2 font-semibold text-zinc-100">{face.operator_review_status}</p>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                        <p className="uppercase tracking-[0.14em] text-zinc-500">Distance To Template</p>
                        <p className="mt-2 font-mono font-semibold text-zinc-100">{formatDistance(face.template_distance)}</p>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                        <p className="uppercase tracking-[0.14em] text-zinc-500">Recognition Use</p>
                        <p className="mt-2 font-semibold text-zinc-100">Excluded</p>
                    </div>
                </div>
            </div>
        );
    }

    const roleCopy = getRoleCopy(face.template_role);

    return (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
                        Template Membership
                    </p>
                    <p className="mt-1 text-sm text-zinc-300">{roleCopy.detail}</p>
                </div>
                <Badge variant={roleCopy.variant}>{roleCopy.label}</Badge>
            </div>
            <div className="mt-4 grid gap-3 text-xs text-zinc-400 sm:grid-cols-3">
                <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                    <p className="uppercase tracking-[0.14em] text-zinc-500">Role</p>
                    <p className="mt-2 font-semibold text-zinc-100">{face.template_role}</p>
                </div>
                <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                    <p className="uppercase tracking-[0.14em] text-zinc-500">Distance To Template</p>
                    <p className="mt-2 font-mono font-semibold text-zinc-100">{formatDistance(face.template_distance)}</p>
                </div>
                <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                    <p className="uppercase tracking-[0.14em] text-zinc-500">Recognition Use</p>
                    <p className="mt-2 font-semibold text-zinc-100">
                        {face.template_role === 'primary' || face.template_role === 'support'
                            ? 'Included'
                            : 'Excluded'}
                    </p>
                </div>
            </div>
        </div>
    );
}
