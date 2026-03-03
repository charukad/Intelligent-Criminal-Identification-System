import { ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

import { buildBackendUrl } from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { RecognitionCandidate } from '@/types/recognition';

interface RecognitionCandidateTableProps {
    candidates: RecognitionCandidate[];
    selectedCriminalId?: string | null;
    title?: string;
    emptyMessage?: string;
    onEscalateMergeReview?: (candidate: RecognitionCandidate) => void;
    isEscalatingCandidateId?: string | null;
}

function formatDistance(value: number) {
    return value.toFixed(6);
}

export function RecognitionCandidateTable({
    candidates,
    selectedCriminalId = null,
    title = 'Candidate identities',
    emptyMessage = 'No candidate identities were returned for this face.',
    onEscalateMergeReview,
    isEscalatingCandidateId = null,
}: RecognitionCandidateTableProps) {
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">{title}</p>
                <p className="text-xs text-zinc-500">{candidates.length} candidate{candidates.length === 1 ? '' : 's'}</p>
            </div>

            {candidates.length === 0 ? (
                <div className="rounded-lg border border-dashed border-zinc-800 bg-zinc-950/50 p-4 text-sm text-zinc-500">
                    {emptyMessage}
                </div>
            ) : (
                <div className="space-y-2">
                    {candidates.map((candidate, index) => {
                        const isSelected = selectedCriminalId === candidate.criminal.id;

                        return (
                            <div
                                key={`${candidate.face_id}-${index}`}
                                className={`grid gap-3 rounded-lg border p-3 md:grid-cols-[72px_minmax(0,1fr)_auto] ${
                                    isSelected
                                        ? 'border-emerald-700/60 bg-emerald-950/10'
                                        : 'border-zinc-800 bg-zinc-950/60'
                                }`}
                            >
                                <div className="overflow-hidden rounded-md border border-zinc-800 bg-zinc-900/60">
                                    <img
                                        src={buildBackendUrl(candidate.image_url)}
                                        alt={candidate.criminal.name}
                                        className="h-[72px] w-[72px] object-cover"
                                    />
                                </div>
                                <div className="min-w-0 space-y-2">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <p className="truncate text-sm font-semibold text-zinc-100">
                                            #{index + 1} {candidate.criminal.name}
                                        </p>
                                        {isSelected ? <Badge variant="success">selected result</Badge> : null}
                                        <Badge variant={candidate.is_primary ? 'info' : 'outline'}>
                                            {candidate.is_primary ? 'primary face' : 'support face'}
                                        </Badge>
                                    </div>
                                    <div className="grid gap-2 text-xs text-zinc-400 sm:grid-cols-2 xl:grid-cols-4">
                                        <p>Distance: <span className="font-mono text-zinc-200">{formatDistance(candidate.distance)}</span></p>
                                        <p>NIC: <span className="font-mono text-zinc-200">{candidate.criminal.nic || 'n/a'}</span></p>
                                        <p>Threat: <span className="text-zinc-200">{candidate.criminal.threat_level || 'unknown'}</span></p>
                                        <p>Embedding: <span className="font-mono text-zinc-200">{candidate.embedding_version}</span></p>
                                        <p>Template: <span className="font-mono text-zinc-200">{candidate.template_version}</span></p>
                                        <p>Active: <span className="text-zinc-200">{candidate.active_face_count}</span></p>
                                        <p>Support: <span className="text-zinc-200">{candidate.support_face_count}</span></p>
                                        <p>Outlier: <span className="text-zinc-200">{candidate.outlier_face_count}</span></p>
                                    </div>
                                </div>
                                <div className="flex flex-wrap items-start justify-start gap-2 md:justify-end">
                                    {onEscalateMergeReview && selectedCriminalId && candidate.criminal.id !== selectedCriminalId ? (
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="sm"
                                            className="border-amber-900/50 text-amber-300 hover:bg-amber-950/30"
                                            onClick={() => onEscalateMergeReview(candidate)}
                                            disabled={isEscalatingCandidateId === candidate.criminal.id}
                                        >
                                            {isEscalatingCandidateId === candidate.criminal.id ? 'Escalating...' : 'Escalate Merge Review'}
                                        </Button>
                                    ) : null}
                                    <Button asChild variant="outline" size="sm" className="border-zinc-700">
                                        <Link to={`/dashboard/criminals?criminal=${candidate.criminal.id}`}>
                                            <ExternalLink className="mr-2 h-4 w-4" />
                                            View Profile
                                        </Link>
                                    </Button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
