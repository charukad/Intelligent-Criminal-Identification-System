import { formatDistanceToNow } from 'date-fns';
import { AlertTriangle, ArrowRightLeft, CheckCircle2, FolderX, GitPullRequest, XCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { ReviewCase } from '@/types/review';

interface DuplicateIdentityReviewCardProps {
    reviewCase: ReviewCase;
    isResolving?: boolean;
    highlighted?: boolean;
    onResolve: (reviewCaseId: string, status: 'confirmed_duplicate' | 'false_positive' | 'dismissed') => void;
    onMerge: (reviewCase: ReviewCase, survivorCriminalId: string) => void;
}

function getRiskBadge(riskLevel: ReviewCase['risk_level']) {
    if (riskLevel === 'probable_duplicate') {
        return {
            label: 'Probable Duplicate',
            variant: 'destructive' as const,
            icon: <AlertTriangle className="h-3.5 w-3.5" />,
        };
    }

    return {
        label: 'Needs Review',
        variant: 'warning' as const,
        icon: <GitPullRequest className="h-3.5 w-3.5" />,
    };
}

export function DuplicateIdentityReviewCard({
    reviewCase,
    isResolving = false,
    highlighted = false,
    onResolve,
    onMerge,
}: DuplicateIdentityReviewCardProps) {
    const riskBadge = getRiskBadge(reviewCase.risk_level);

    return (
        <Card
            id={`review-case-${reviewCase.id}`}
            className={
                highlighted
                    ? 'border-amber-500/70 bg-amber-950/20 shadow-[0_0_0_1px_rgba(245,158,11,0.35)]'
                    : 'border-zinc-800 bg-zinc-950/60'
            }
        >
            <CardHeader className="space-y-3">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={riskBadge.variant} className="gap-1">
                                {riskBadge.icon}
                                {riskBadge.label}
                            </Badge>
                            <Badge variant="outline">Distance {reviewCase.distance.toFixed(6)}</Badge>
                            <Badge variant="secondary">{reviewCase.embedding_version}</Badge>
                            {highlighted ? <Badge variant="info">Focused Case</Badge> : null}
                        </div>
                        <CardTitle className="text-xl text-white">
                            {reviewCase.source_criminal.name} vs {reviewCase.matched_criminal.name}
                        </CardTitle>
                        <CardDescription>
                            Created {formatDistanceToNow(new Date(reviewCase.created_at), { addSuffix: true })}
                            {reviewCase.submitted_filename ? ` from ${reviewCase.submitted_filename}` : ''}
                        </CardDescription>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-xs text-zinc-400 md:min-w-[220px]">
                        <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                            <p className="text-zinc-500">Source Criminal</p>
                            <p className="mt-1 font-medium text-zinc-100">{reviewCase.source_criminal.name}</p>
                        </div>
                        <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                            <p className="text-zinc-500">Matched Criminal</p>
                            <p className="mt-1 font-medium text-zinc-100">{reviewCase.matched_criminal.name}</p>
                        </div>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">Source Profile</p>
                        <p className="mt-2 text-sm font-semibold text-white">{reviewCase.source_criminal.name}</p>
                        <p className="mt-1 text-xs text-zinc-400">Criminal ID: {reviewCase.source_criminal.id}</p>
                        <Button asChild variant="link" className="mt-2 h-auto px-0 text-amber-300">
                            <Link to={`/dashboard/criminals?criminal=${reviewCase.source_criminal.id}`}>
                                View Criminal Profile
                            </Link>
                        </Button>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">Conflicting Profile</p>
                        <p className="mt-2 text-sm font-semibold text-white">{reviewCase.matched_criminal.name}</p>
                        <p className="mt-1 text-xs text-zinc-400">Criminal ID: {reviewCase.matched_criminal.id}</p>
                        <Button asChild variant="link" className="mt-2 h-auto px-0 text-amber-300">
                            <Link to={`/dashboard/criminals?criminal=${reviewCase.matched_criminal.id}`}>
                                View Criminal Profile
                            </Link>
                        </Button>
                    </div>
                </div>

                {reviewCase.notes ? (
                    <div className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-4 text-sm text-amber-200">
                        {reviewCase.notes}
                    </div>
                ) : null}

                <div className="flex flex-wrap gap-3">
                    <Button
                        onClick={() => onMerge(reviewCase, reviewCase.source_criminal.id)}
                        disabled={isResolving}
                        className="bg-amber-500 text-black hover:bg-amber-400"
                    >
                        <ArrowRightLeft className="mr-2 h-4 w-4" />
                        Keep Source Profile
                    </Button>
                    <Button
                        onClick={() => onMerge(reviewCase, reviewCase.matched_criminal.id)}
                        disabled={isResolving}
                        className="bg-amber-200 text-black hover:bg-amber-100"
                    >
                        <ArrowRightLeft className="mr-2 h-4 w-4" />
                        Keep Matched Profile
                    </Button>
                    <Button
                        onClick={() => onResolve(reviewCase.id, 'confirmed_duplicate')}
                        disabled={isResolving}
                        className="bg-red-600 text-white hover:bg-red-700"
                    >
                        <AlertTriangle className="mr-2 h-4 w-4" />
                        Confirm Duplicate
                    </Button>
                    <Button
                        variant="outline"
                        onClick={() => onResolve(reviewCase.id, 'false_positive')}
                        disabled={isResolving}
                        className="border-emerald-700 text-emerald-300 hover:bg-emerald-950/30"
                    >
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Mark False Positive
                    </Button>
                    <Button
                        variant="outline"
                        onClick={() => onResolve(reviewCase.id, 'dismissed')}
                        disabled={isResolving}
                        className="border-zinc-700 text-zinc-200 hover:bg-zinc-900"
                    >
                        <FolderX className="mr-2 h-4 w-4" />
                        Dismiss
                    </Button>
                </div>

                {reviewCase.resolution_notes ? (
                    <div className="flex items-start gap-2 rounded-lg border border-zinc-800 bg-zinc-900/70 p-4 text-sm text-zinc-300">
                        <XCircle className="mt-0.5 h-4 w-4 text-zinc-500" />
                        <span>{reviewCase.resolution_notes}</span>
                    </div>
                ) : null}
            </CardContent>
        </Card>
    );
}
