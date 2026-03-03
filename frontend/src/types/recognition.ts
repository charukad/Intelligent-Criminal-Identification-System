export interface RecognitionCriminalSummary {
    id: string;
    name: string;
    nic?: string | null;
    threat_level?: string | null;
}

export interface RecognitionCandidate {
    criminal: RecognitionCriminalSummary;
    face_id: string;
    image_url: string;
    is_primary: boolean;
    embedding_version: string;
    distance: number;
}

export interface RecognitionResult {
    box: [number, number, number, number];
    status: 'match' | 'unknown';
    confidence: number;
    decision_reason: string;
    distance?: number | null;
    criminal?: RecognitionCriminalSummary | null;
}

export interface RecognitionDebugFace {
    box: [number, number, number, number];
    area: number;
    selected: boolean;
    decision_reason: string;
    best_distance?: number | null;
    second_best_distance?: number | null;
    top_candidates: RecognitionCandidate[];
}

export interface RecognitionDebug {
    threshold: number;
    ambiguity_margin: number;
    single_face_only: boolean;
    detected_face_count: number;
    analyzed_face_count: number;
    faces: RecognitionDebugFace[];
}

export interface RecognitionResponse {
    results: RecognitionResult[];
    debug?: RecognitionDebug | null;
}
