export type ReviewCaseStatus = 'open' | 'confirmed_duplicate' | 'false_positive' | 'dismissed';
export type DuplicateRiskLevel = 'probable_duplicate' | 'needs_review';

export interface ReviewCaseCriminalRef {
    id: string;
    name: string;
    primary_face_image_url?: string | null;
}

export interface DuplicateReviewSummary {
    review_case_id: string;
    risk_level: DuplicateRiskLevel;
    distance: number;
    conflicting_criminal: ReviewCaseCriminalRef;
    status: ReviewCaseStatus;
}

export interface ReviewCase {
    id: string;
    case_type: 'duplicate_identity';
    status: ReviewCaseStatus;
    risk_level: DuplicateRiskLevel;
    source_criminal: ReviewCaseCriminalRef;
    matched_criminal: ReviewCaseCriminalRef;
    source_face_id?: string | null;
    matched_face_id?: string | null;
    distance: number;
    embedding_version: string;
    template_version?: string | null;
    submitted_filename?: string | null;
    notes?: string | null;
    resolution_notes?: string | null;
    created_by_id?: string | null;
    resolved_by_id?: string | null;
    created_at: string;
    resolved_at?: string | null;
}
