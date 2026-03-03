import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { RecognitionDebug } from '@/types/recognition';

interface RecognitionDebugPanelProps {
    debug: RecognitionDebug | null | undefined;
}

const decisionReasonLabels: Record<string, string> = {
    matched: 'Accepted match',
    possible_match_threshold: 'Review: near threshold band',
    possible_match_ambiguous: 'Review: top candidates are too close',
    over_possible_threshold: 'Rejected: distance above possible-match band',
    no_candidate_embeddings: 'Rejected: no enrolled candidates',
    missing_criminal_record: 'Rejected: missing criminal record',
};

function formatDistance(value?: number | null) {
    if (value === null || value === undefined) {
        return 'n/a';
    }
    return value.toFixed(4);
}

function formatBox(box: [number, number, number, number]) {
    return `x:${box[0]} y:${box[1]} w:${box[2]} h:${box[3]}`;
}

export function RecognitionDebugPanel({ debug }: RecognitionDebugPanelProps) {
    if (!debug) {
        return null;
    }

    return (
        <Card className="border-zinc-800 bg-zinc-950/60">
            <CardHeader>
                <CardTitle className="text-base text-zinc-100">Recognition Diagnostics</CardTitle>
                <CardDescription>
                    Inspect the backend decision path before trusting a match.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-zinc-500">Detected Faces</p>
                        <p className="mt-1 text-xl font-semibold text-zinc-100">{debug.detected_face_count}</p>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-zinc-500">Analyzed Faces</p>
                        <p className="mt-1 text-xl font-semibold text-zinc-100">{debug.analyzed_face_count}</p>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-zinc-500">Match Threshold</p>
                        <p className="mt-1 text-xl font-semibold text-zinc-100">{formatDistance(debug.threshold)}</p>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-zinc-500">Mode</p>
                        <p className="mt-1 text-xl font-semibold text-zinc-100">
                            {debug.single_face_only ? 'Largest face only' : 'All faces'}
                        </p>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-zinc-500">Possible Threshold</p>
                        <p className="mt-1 text-xl font-semibold text-zinc-100">{formatDistance(debug.possible_match_threshold)}</p>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-zinc-500">Separation</p>
                        <p className="mt-1 text-xl font-semibold text-zinc-100">
                            {formatDistance(debug.match_separation_margin)} / {formatDistance(debug.possible_match_separation_margin)}
                        </p>
                    </div>
                </div>

                {debug.faces.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-zinc-800 bg-zinc-900/40 p-4 text-sm text-zinc-500">
                        No analyzed faces were returned by the backend.
                    </div>
                ) : (
                    <div className="space-y-3">
                        {debug.faces.map((face, index) => (
                            <div key={`${face.box.join('-')}-${index}`} className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-4">
                                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                                    <div className="space-y-2">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <p className="text-sm font-semibold text-zinc-100">Analyzed Face #{index + 1}</p>
                                            {face.selected && <Badge variant="info">selected</Badge>}
                                            <Badge
                                                variant={
                                                    face.decision_reason === 'matched'
                                                        ? 'success'
                                                        : face.decision_reason.startsWith('possible_match')
                                                            ? 'warning'
                                                            : 'outline'
                                                }
                                            >
                                                {decisionReasonLabels[face.decision_reason] ?? face.decision_reason}
                                            </Badge>
                                        </div>
                                        <div className="grid gap-2 text-xs text-zinc-400 sm:grid-cols-2 xl:grid-cols-4">
                                            <p>Box: <span className="font-mono text-zinc-200">{formatBox(face.box)}</span></p>
                                            <p>Area: <span className="font-mono text-zinc-200">{face.area}</span></p>
                                            <p>Best distance: <span className="font-mono text-zinc-200">{formatDistance(face.best_distance)}</span></p>
                                            <p>Second best: <span className="font-mono text-zinc-200">{formatDistance(face.second_best_distance)}</span></p>
                                        </div>
                                    </div>
                                </div>

                                <div className="mt-4 space-y-2">
                                    <p className="text-xs uppercase tracking-wide text-zinc-500">Top Candidates</p>
                                    {face.top_candidates.length === 0 ? (
                                        <div className="rounded-md border border-dashed border-zinc-800 bg-zinc-950/50 p-3 text-sm text-zinc-500">
                                            No enriched candidate list available for this face.
                                        </div>
                                    ) : (
                                        <div className="space-y-2">
                                            {face.top_candidates.map((candidate, candidateIndex) => (
                                                <div
                                                    key={`${candidate.face_id}-${candidateIndex}`}
                                                    className="grid gap-2 rounded-md border border-zinc-800 bg-zinc-950/60 p-3 text-sm text-zinc-300 md:grid-cols-[minmax(0,1fr)_auto_auto]"
                                                >
                                                    <div className="min-w-0">
                                                        <p className="truncate font-medium text-zinc-100">
                                                            #{candidateIndex + 1} {candidate.criminal.name}
                                                        </p>
                                                        <p className="truncate text-xs text-zinc-500">
                                                            {candidate.criminal.nic || 'No NIC'} · {candidate.criminal.threat_level || 'Unknown threat'}
                                                        </p>
                                                    </div>
                                                    <div className="text-xs text-zinc-400">
                                                        <p className="font-mono text-zinc-200">{formatDistance(candidate.distance)}</p>
                                                        <p>{candidate.embedding_version}</p>
                                                        <p>{candidate.template_version}</p>
                                                        <p>
                                                            {candidate.active_face_count} active · {candidate.support_face_count} support · {candidate.outlier_face_count} outlier
                                                        </p>
                                                    </div>
                                                    <div className="flex items-center justify-start md:justify-end">
                                                        <Badge variant={candidate.is_primary ? 'success' : 'outline'}>
                                                            {candidate.is_primary ? 'Primary face' : 'Support face'}
                                                        </Badge>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
