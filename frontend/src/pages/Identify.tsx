import { useMemo, useRef, useState } from 'react';
import { UploadCloud, Loader2, UserCheck, UserX, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { recognitionApi } from '@/api/recognition';
import { reviewCasesApi } from '@/api/reviewCases';
import { RecognitionCandidateTable } from '@/components/recognition/RecognitionCandidateTable';
import { RecognitionDebugPanel } from '@/components/recognition/RecognitionDebugPanel';
import { RecognitionOverlay } from '@/components/recognition/RecognitionOverlay';
import type {
    RecognitionCandidate,
    RecognitionDebugFace,
    RecognitionOverlayFace,
    RecognitionResponse,
    RecognitionResult,
} from '@/types/recognition';

const decisionReasonLabels: Record<string, string> = {
    matched: 'Match accepted',
    possible_match_threshold: 'Needs review: close but not strong enough',
    possible_match_ambiguous: 'Needs review: top candidates are too close',
    over_possible_threshold: 'Rejected: no close enough identity',
    no_candidate_embeddings: 'Rejected: no enrolled faces available',
    missing_criminal_record: 'Rejected: missing criminal record',
};

function formatDistance(value?: number | null) {
    if (value === null || value === undefined) {
        return 'n/a';
    }
    return value.toFixed(4);
}

function boxKey(box: [number, number, number, number]) {
    return box.join(':');
}

export default function Identify() {
    const navigate = useNavigate();
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [recognitionResponse, setRecognitionResponse] = useState<RecognitionResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [debugEnabled, setDebugEnabled] = useState(true);
    const [sceneModeEnabled, setSceneModeEnabled] = useState(false);
    const [reviewNotice, setReviewNotice] = useState<{ reviewCaseId: string; message: string } | null>(null);
    const [escalatingCandidateId, setEscalatingCandidateId] = useState<string | null>(null);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const results: RecognitionResult[] | null = recognitionResponse?.results ?? null;
    const debugFaces = recognitionResponse?.debug?.faces ?? [];

    const overlayFaces = useMemo<RecognitionOverlayFace[]>(() => {
        if (debugFaces.length > 0) {
            return debugFaces.map((face, index) => {
                const result = results?.find((item) => boxKey(item.box) === boxKey(face.box));
                const status = result?.status ?? 'unknown';

                return {
                    box: face.box,
                    status,
                    label: face.selected
                        ? `Selected face #${index + 1}`
                        : `${status === 'match' ? 'Match' : status === 'possible_match' ? 'Review' : 'Unknown'} #${index + 1}`,
                    selected: face.selected,
                };
            });
        }

        return (results ?? []).map((result, index) => ({
            box: result.box,
            status: result.status,
            label:
                result.status === 'match'
                    ? `Match #${index + 1}`
                    : result.status === 'possible_match'
                        ? `Review #${index + 1}`
                        : `Unknown #${index + 1}`,
            selected: index === 0,
        }));
    }, [debugFaces, results]);

    const getDebugFaceForResult = (result: RecognitionResult): RecognitionDebugFace | undefined =>
        debugFaces.find((face) => boxKey(face.box) === boxKey(result.box));

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            setFile(selectedFile);
            setPreview(URL.createObjectURL(selectedFile));
            setRecognitionResponse(null);
            setError(null);
            setReviewNotice(null);
        }
    };

    const handleEscalateMergeReview = async (
        result: RecognitionResult,
        debugFace: RecognitionDebugFace,
        candidate: RecognitionCandidate,
    ) => {
        if (!result.criminal) {
            return;
        }

        const selectedCandidate = debugFace.top_candidates.find(
            (item) => item.criminal.id === result.criminal?.id,
        );

        setEscalatingCandidateId(candidate.criminal.id);
        setReviewNotice(null);
        setError(null);

        try {
            const createdCase = await reviewCasesApi.createManualDuplicateIdentityCase({
                source_criminal_id: result.criminal.id,
                matched_criminal_id: candidate.criminal.id,
                source_face_id: selectedCandidate?.face_id ?? null,
                matched_face_id: candidate.face_id,
                distance: candidate.distance,
                embedding_version: candidate.embedding_version,
                template_version: candidate.template_version,
                submitted_filename: file?.name ?? null,
                notes:
                    `Manual escalation from recognition review. ` +
                    `Decision=${result.decision_reason}. ` +
                    `Analyzed box=${result.box.join(', ')}. ` +
                    `Candidate distance=${candidate.distance.toFixed(6)}.`,
            });
            setReviewNotice({
                reviewCaseId: createdCase.id,
                message: `Opened duplicate review between ${createdCase.source_criminal.name} and ${createdCase.matched_criminal.name}.`,
            });
        } catch (reviewError: any) {
            setError(
                reviewError?.response?.data?.detail ||
                    'Failed to create a duplicate review case from this recognition result.',
            );
        } finally {
            setEscalatingCandidateId(null);
        }
    };

    const handleIdentify = async () => {
        if (!file) return;

        try {
            setIsLoading(true);
            setError(null);
            const response = await recognitionApi.identifySuspect(file, {
                debug: debugEnabled,
                mode: sceneModeEnabled ? 'scene' : 'single',
            });
            setRecognitionResponse(response);
        } catch (err: any) {
            setError(err.response?.data?.detail || "Failed to identify faces.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-6 p-6 max-w-5xl mx-auto">
            <div>
                <h1 className="text-3xl font-bold text-white">Identify Suspect</h1>
                <p className="mt-1 text-sm text-zinc-400">
                    Upload an image or connect a camera feed to run facial recognition against the criminal database.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="border-zinc-800 bg-zinc-950/50 h-fit">
                    <CardHeader>
                        <CardTitle>Image Upload</CardTitle>
                        <CardDescription>Select an image to analyze</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col items-center justify-center p-8 m-4 border-2 border-dashed border-zinc-700 rounded-lg bg-zinc-900/40 relative overflow-hidden group">
                        {preview ? (
                            <div className="w-full text-center space-y-4">
                                <RecognitionOverlay
                                    imageUrl={preview}
                                    faces={overlayFaces}
                                    alt="Uploaded suspect preview"
                                />
                                <p className="text-xs text-zinc-500">
                                    {sceneModeEnabled
                                        ? 'Scene mode reviews every detected face region.'
                                        : 'Single mode analyzes only the largest detected face.'}
                                </p>
                                <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} className="border-zinc-700">Change Image</Button>
                            </div>
                        ) : (
                            <>
                                <UploadCloud className="w-12 h-12 text-zinc-500 mb-4 group-hover:text-blue-500 transition-colors" />
                                <p className="text-sm text-zinc-400 mb-4">Supported formats: JPG, PNG, WEBP</p>
                                <Button variant="outline" onClick={() => fileInputRef.current?.click()} className="border-zinc-700 hover:bg-zinc-800 hover:text-white">
                                    Select Image
                                </Button>
                            </>
                        )}
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            accept="image/jpeg, image/png, image/webp"
                            className="hidden"
                        />
                    </CardContent>
                    <CardFooter className="flex justify-end gap-3 px-6 pb-6">
                        <label className="mr-auto flex items-center gap-2 text-sm text-zinc-400">
                            <input
                                type="checkbox"
                                className="h-4 w-4 rounded border-zinc-700 bg-zinc-900 text-emerald-500"
                                checked={debugEnabled}
                                onChange={(event) => setDebugEnabled(event.target.checked)}
                                disabled={isLoading}
                            />
                            Show recognition diagnostics
                        </label>
                        <label className="flex items-center gap-2 text-sm text-zinc-400">
                            <input
                                type="checkbox"
                                className="h-4 w-4 rounded border-zinc-700 bg-zinc-900 text-emerald-500"
                                checked={sceneModeEnabled}
                                onChange={(event) => setSceneModeEnabled(event.target.checked)}
                                disabled={isLoading}
                            />
                            Scene mode
                        </label>
                        <Button
                            variant="ghost"
                            onClick={() => {
                                setFile(null);
                                setPreview(null);
                                setRecognitionResponse(null);
                                setError(null);
                            }}
                            disabled={!file || isLoading}
                        >
                            Clear
                        </Button>
                        <Button onClick={handleIdentify} disabled={!file || isLoading} className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg w-32">
                            {isLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                            {isLoading ? 'Scanning...' : 'Identify'}
                        </Button>
                    </CardFooter>
                </Card>

                <div className="space-y-4">
                    <h3 className="text-lg font-semibold border-b border-zinc-800 pb-2">Analysis Results</h3>

                    {error && (
                        <div className="p-4 rounded-md bg-red-950/50 border border-red-900 text-red-200 text-sm flex items-start gap-3">
                            <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5" />
                            <p>{error}</p>
                        </div>
                    )}

                    {reviewNotice && (
                        <div className="p-4 rounded-md bg-amber-950/30 border border-amber-900/60 text-amber-100 text-sm flex flex-col gap-3">
                            <p>{reviewNotice.message}</p>
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="w-fit border-amber-900/60 text-amber-200 hover:bg-amber-950/30"
                                onClick={() => navigate(`/dashboard/review-queue?case=${reviewNotice.reviewCaseId}`)}
                            >
                                Open Review Queue
                            </Button>
                        </div>
                    )}

                    {!results && !isLoading && !error && (
                        <div className="h-64 flex items-center justify-center border border-zinc-800 rounded-lg border-dashed text-zinc-500 text-sm">
                            Upload an image and run identification to see matches here.
                        </div>
                    )}

                    {isLoading && (
                        <div className="h-64 flex flex-col gap-4 items-center justify-center border border-zinc-800 rounded-lg bg-zinc-900/20 text-zinc-500">
                            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                            <p className="text-sm animate-pulse">Running vector similarity search...</p>
                        </div>
                    )}

                    {results && results.length === 0 && (
                        <div className="p-6 text-center border border-zinc-800 rounded-lg bg-zinc-900/20">
                            <UserX className="w-12 h-12 text-zinc-600 mx-auto mb-3" />
                            <h4 className="text-zinc-300 font-medium">No Faces Detected</h4>
                            <p className="text-sm text-zinc-500 mt-1">The AI could not detect any faces in this image.</p>
                        </div>
                    )}

                    {results && results.map((result, idx) => (
                        <Card
                            key={idx}
                            className={`border-l-4 ${
                                result.status === 'match'
                                    ? 'border-l-red-500'
                                    : result.status === 'possible_match'
                                        ? 'border-l-amber-500'
                                        : 'border-l-zinc-500'
                            } bg-zinc-950`}
                        >
                            {(() => {
                                const debugFace = getDebugFaceForResult(result);

                                return (
                                    <>
                                        <CardHeader className="pb-2">
                                            <div className="flex items-center justify-between">
                                                <CardTitle className="text-base flex items-center gap-2">
                                                    {result.status === 'match' ? (
                                                        <UserCheck className="text-red-500 w-5 h-5" />
                                                    ) : result.status === 'possible_match' ? (
                                                        <AlertTriangle className="text-amber-500 w-5 h-5" />
                                                    ) : (
                                                        <UserX className="text-zinc-500 w-5 h-5" />
                                                    )}
                                                    {result.status === 'match'
                                                        ? 'Database Match Found'
                                                        : result.status === 'possible_match'
                                                            ? 'Possible Match'
                                                            : 'Unknown Individual'}
                                                </CardTitle>
                                                <span
                                                    className={`text-xs px-2 py-1 rounded font-mono ${
                                                        result.status === 'match'
                                                            ? 'bg-red-950/50 text-red-400'
                                                            : result.status === 'possible_match'
                                                                ? 'bg-amber-950/50 text-amber-300'
                                                                : 'bg-zinc-800 text-zinc-400'
                                                    }`}
                                                >
                                                    {result.confidence.toFixed(1)}% Confidence
                                                </span>
                                            </div>
                                            <div className="flex flex-wrap items-center gap-3 pt-2 text-xs text-zinc-500">
                                                <span>Decision: {decisionReasonLabels[result.decision_reason] ?? result.decision_reason}</span>
                                                <span>Distance: <span className="font-mono text-zinc-300">{formatDistance(result.distance)}</span></span>
                                                <span>Box: <span className="font-mono text-zinc-300">{result.box.join(', ')}</span></span>
                                            </div>
                                        </CardHeader>
                                        <CardContent className="space-y-4">
                                            {(result.status === 'match' || result.status === 'possible_match') && result.criminal ? (
                                                <div>
                                                    <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-sm mt-2">
                                                        <div>
                                                            <p className="text-xs text-zinc-500">Name</p>
                                                            <p className="font-semibold text-white">{result.criminal.name}</p>
                                                        </div>
                                                        <div>
                                                            <p className="text-xs text-zinc-500">NIC Mapping</p>
                                                            <p className="text-zinc-300 font-mono">{result.criminal.nic}</p>
                                                        </div>
                                                        <div>
                                                            <p className="text-xs text-zinc-500">Threat Level</p>
                                                            <span
                                                                className={`inline-flex items-center rounded-full mt-1 px-2 py-0.5 text-xs font-medium border ${
                                                                    result.status === 'match'
                                                                        ? 'bg-red-950 text-red-400 border-red-900'
                                                                        : 'bg-amber-950 text-amber-300 border-amber-900'
                                                                }`}
                                                            >
                                                                {result.criminal.threat_level}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <div className="mt-4 pt-4 border-t border-zinc-800">
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            className="w-full text-xs border-zinc-700"
                                                            onClick={() => navigate(`/dashboard/criminals?criminal=${result.criminal!.id}`)}
                                                        >
                                                            {result.status === 'match' ? 'View Full Profile' : 'Review Candidate'}
                                                        </Button>
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-4 text-sm text-zinc-400">
                                                    The system rejected this face as unknown. Use the candidate list below to inspect nearby identities and the raw distance gap before trusting any manual conclusion.
                                                </div>
                                            )}

                                            {debugFace ? (
                                                <RecognitionCandidateTable
                                                    candidates={debugFace.top_candidates}
                                                    selectedCriminalId={result.criminal?.id ?? null}
                                                    title={
                                                        result.status === 'unknown'
                                                            ? 'Nearest reviewed candidates'
                                                            : 'Candidate identities behind this decision'
                                                    }
                                                    onEscalateMergeReview={
                                                        result.criminal
                                                            ? (candidate) =>
                                                                  handleEscalateMergeReview(result, debugFace, candidate)
                                                            : undefined
                                                    }
                                                    isEscalatingCandidateId={escalatingCandidateId}
                                                />
                                            ) : null}
                                        </CardContent>
                                    </>
                                );
                            })()}
                        </Card>
                    ))}

                    {debugEnabled && recognitionResponse?.debug && (
                        <RecognitionDebugPanel debug={recognitionResponse.debug} />
                    )}
                </div>
            </div>
        </div>
    );
}
