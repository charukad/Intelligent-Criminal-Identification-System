import type { DuplicateReviewSummary } from '@/types/review';

export type FaceTemplateRole = 'primary' | 'support' | 'archived' | 'outlier' | (string & {});

export interface Criminal {
    id: string;
    first_name: string;
    last_name: string;
    aliases?: string;
    nic?: string;
    dob?: string;
    gender: string;
    blood_type?: string;
    status?: 'wanted' | 'in_custody' | 'released' | 'deceased' | 'cleared';
    threat_level?: 'low' | 'medium' | 'high' | 'critical';
    last_known_address?: string;
    physical_description?: string;
    primary_face_image_url?: string | null;
}

export interface CriminalFace {
    id: string;
    criminal_id: string;
    image_url: string;
    is_primary: boolean;
    embedding_version: string;
    created_at: string;
    box: [number, number, number, number];
    exclude_from_template: boolean;
    operator_review_status: string;
    operator_review_notes?: string | null;
    template_role: FaceTemplateRole;
    template_distance?: number | null;
    quality: FaceQuality;
    duplicate_review?: DuplicateReviewSummary | null;
}

export interface FaceQuality {
    status: 'accepted' | 'accepted_with_warnings' | 'rejected';
    quality_score: number;
    blur_score: number;
    brightness_score: number;
    face_area_ratio: number;
    pose_score: number;
    occlusion_score: number;
    warnings: string[];
}

export interface FaceQualityPreview {
    status: 'accepted' | 'accepted_with_warnings' | 'rejected';
    detected_face_count: number;
    decision_reason: string;
    message: string;
    box?: [number, number, number, number] | null;
    quality?: FaceQuality | null;
}

export interface CriminalFaceReviewActionResponse {
    status: string;
    message: string;
    promoted_face_id?: string | null;
    face: CriminalFace;
}

export interface CriminalTemplateRebuild {
    id: string;
    criminal_id: string;
    template_version: string;
    embedding_version: string;
    primary_face_id?: string | null;
    included_face_ids: string[];
    support_face_ids: string[];
    archived_face_ids: string[];
    outlier_face_ids: string[];
    active_face_count: number;
    support_face_count: number;
    archived_face_count: number;
    outlier_face_count: number;
    updated_at: string;
}

export interface CriminalTemplateRebuildResponse {
    status: string;
    message: string;
    criminal_id: string;
    template?: CriminalTemplateRebuild | null;
}

export interface CriminalFormData {
    first_name: string;
    last_name: string;
    aliases?: string;
    nic?: string;
    dob?: string;
    gender: string;
    blood_type?: string;
    status?: string;
    threat_level?: string;
    last_known_address?: string;
    physical_description?: string;
    faceFiles?: File[];
    primaryFaceIndex?: number;
}
