import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ClipboardList, Loader2, ShieldAlert } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

import { RoleGuard } from '@/components/common/RoleGuard';
import { DuplicateIdentityReviewCard } from '@/components/review/DuplicateIdentityReviewCard';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { reviewCasesApi } from '@/api/reviewCases';
import type { ReviewCaseStatus } from '@/types/review';

const OPEN_STATUS: ReviewCaseStatus = 'open';

function getRiskSummary(casesCount: number, probableCount: number) {
    if (casesCount === 0) {
        return 'No open duplicate-identity conflicts.';
    }

    if (probableCount === 0) {
        return `${casesCount} review case${casesCount === 1 ? '' : 's'} waiting for operator review.`;
    }

    return `${probableCount} probable duplicate case${probableCount === 1 ? '' : 's'} require immediate attention.`;
}

export default function ReviewQueue() {
    const queryClient = useQueryClient();
    const [searchParams] = useSearchParams();
    const focusedReviewCaseId = searchParams.get('case');
    const [actionNotice, setActionNotice] = useState<{
        tone: 'success' | 'warning' | 'error';
        message: string;
    } | null>(null);

    const { data: reviewCases = [], isLoading, error } = useQuery({
        queryKey: ['duplicateReviewCases', OPEN_STATUS],
        queryFn: () => reviewCasesApi.listDuplicateIdentityCases(OPEN_STATUS),
    });

    const resolveMutation = useMutation({
        mutationFn: ({
            reviewCaseId,
            status,
        }: {
            reviewCaseId: string;
            status: Exclude<ReviewCaseStatus, 'open'>;
        }) => reviewCasesApi.resolveDuplicateIdentityCase(reviewCaseId, { status }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['duplicateReviewCases'] });
        },
    });

    const mergeMutation = useMutation({
        mutationFn: ({
            reviewCaseId,
            survivorCriminalId,
        }: {
            reviewCaseId: string;
            survivorCriminalId: string;
        }) =>
            reviewCasesApi.mergeDuplicateIdentityCase(reviewCaseId, {
                survivor_criminal_id: survivorCriminalId,
                resolution_notes: 'Merged from duplicate review queue.',
            }),
        onSuccess: (result) => {
            setActionNotice({
                tone: 'success',
                message:
                    `Merged duplicate record into ${result.survivor_name}. ` +
                    `${result.moved_face_count} face(s), ${result.moved_offense_count} offense(s), ` +
                    `${result.moved_alert_count} alert(s), and ${result.moved_audit_count} audit log(s) were reassigned.`,
            });
            queryClient.invalidateQueries({ queryKey: ['duplicateReviewCases'] });
            queryClient.invalidateQueries({ queryKey: ['criminals'] });
        },
        onError: (error: any) => {
            setActionNotice({
                tone: 'error',
                message: error?.response?.data?.detail || 'Failed to merge the selected criminal records.',
            });
        },
    });

    const probableCount = reviewCases.filter((reviewCase) => reviewCase.risk_level === 'probable_duplicate').length;

    useEffect(() => {
        if (!focusedReviewCaseId || reviewCases.length === 0) {
            return;
        }

        const element = document.getElementById(`review-case-${focusedReviewCaseId}`);
        if (!element) {
            return;
        }

        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, [focusedReviewCaseId, reviewCases]);

    const handleMerge = (reviewCase: (typeof reviewCases)[number], survivorCriminalId: string) => {
        const survivorName =
            survivorCriminalId === reviewCase.source_criminal.id
                ? reviewCase.source_criminal.name
                : reviewCase.matched_criminal.name;
        const mergedName =
            survivorCriminalId === reviewCase.source_criminal.id
                ? reviewCase.matched_criminal.name
                : reviewCase.source_criminal.name;

        const confirmed = window.confirm(
            `Merge ${mergedName} into ${survivorName}? This will move faces and linked records into the kept profile.`,
        );
        if (!confirmed) {
            return;
        }

        setActionNotice(null);
        mergeMutation.mutate({
            reviewCaseId: reviewCase.id,
            survivorCriminalId,
        });
    };

    return (
        <RoleGuard
            allowedRoles={['admin', 'senior_officer']}
            fallback={
                <Card className="border-red-900/50 bg-red-950/20">
                    <CardHeader>
                        <CardTitle className="text-white">Review Queue Access Required</CardTitle>
                        <CardDescription>
                            Only admins and senior officers can review duplicate-identity conflicts.
                        </CardDescription>
                    </CardHeader>
                </Card>
            }
        >
            <div className="space-y-6">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight text-white">Duplicate Review Queue</h1>
                        <p className="mt-2 text-sm text-zinc-400">
                            Cases created automatically when a new enrollment looks too close to a different criminal profile.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Badge variant="outline" className="gap-1 border-zinc-700">
                            <ClipboardList className="h-3.5 w-3.5" />
                            {reviewCases.length} open case{reviewCases.length === 1 ? '' : 's'}
                        </Badge>
                        <Badge
                            variant={probableCount > 0 ? 'destructive' : 'secondary'}
                            className="gap-1"
                        >
                            <ShieldAlert className="h-3.5 w-3.5" />
                            {probableCount} probable duplicate{probableCount === 1 ? '' : 's'}
                        </Badge>
                    </div>
                </div>

                <Card className="border-zinc-800 bg-zinc-950/60">
                    <CardHeader>
                        <CardTitle className="text-white">Open Cases</CardTitle>
                        <CardDescription>{getRiskSummary(reviewCases.length, probableCount)}</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {actionNotice ? (
                            <div
                                className={
                                    actionNotice.tone === 'success'
                                        ? 'mb-4 rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-4 text-sm text-emerald-300'
                                        : actionNotice.tone === 'warning'
                                            ? 'mb-4 rounded-lg border border-amber-900/50 bg-amber-950/20 p-4 text-sm text-amber-300'
                                            : 'mb-4 rounded-lg border border-red-900/50 bg-red-950/20 p-4 text-sm text-red-300'
                                }
                            >
                                {actionNotice.message}
                            </div>
                        ) : null}
                        {isLoading ? (
                            <div className="flex flex-col items-center justify-center gap-3 py-12 text-zinc-400">
                                <Loader2 className="h-8 w-8 animate-spin" />
                                <p>Loading duplicate review queue...</p>
                            </div>
                        ) : error ? (
                            <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-4 text-sm text-red-300">
                                Failed to load duplicate review cases.
                            </div>
                        ) : reviewCases.length === 0 ? (
                            <div className="rounded-lg border border-dashed border-zinc-800 bg-zinc-900/40 p-8 text-center">
                                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10">
                                    <ClipboardList className="h-7 w-7 text-emerald-400" />
                                </div>
                                <h3 className="mt-4 text-lg font-semibold text-white">Queue Clear</h3>
                                <p className="mt-2 text-sm text-zinc-400">
                                    No duplicate-identity conflicts are waiting for review right now.
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {reviewCases.map((reviewCase) => (
                                    <DuplicateIdentityReviewCard
                                        key={reviewCase.id}
                                        reviewCase={reviewCase}
                                        isResolving={resolveMutation.isPending || mergeMutation.isPending}
                                        highlighted={reviewCase.id === focusedReviewCaseId}
                                        onResolve={(reviewCaseId, status) =>
                                            resolveMutation.mutate({ reviewCaseId, status })
                                        }
                                        onMerge={handleMerge}
                                    />
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </RoleGuard>
    );
}
