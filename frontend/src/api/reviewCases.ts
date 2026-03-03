import { api } from '@/api/client';
import type { ReviewCase, ReviewCaseStatus } from '@/types/review';

export const reviewCasesApi = {
    listDuplicateIdentityCases: async (status: ReviewCaseStatus = 'open'): Promise<ReviewCase[]> => {
        const { data } = await api.get('/criminals/review-cases/duplicate-identities', {
            params: { status },
        });
        return data;
    },

    resolveDuplicateIdentityCase: async (
        reviewCaseId: string,
        payload: { status: Exclude<ReviewCaseStatus, 'open'>; resolution_notes?: string },
    ): Promise<ReviewCase> => {
        const { data } = await api.post(`/criminals/review-cases/${reviewCaseId}/resolve`, payload);
        return data;
    },

    mergeDuplicateIdentityCase: async (
        reviewCaseId: string,
        payload: { survivor_criminal_id: string; resolution_notes?: string },
    ): Promise<{
        status: string;
        review_case_id: string;
        survivor_criminal_id: string;
        merged_criminal_id: string;
        moved_face_count: number;
        moved_offense_count: number;
        moved_alert_count: number;
        moved_audit_count: number;
        dismissed_review_case_count: number;
        survivor_name: string;
    }> => {
        const { data } = await api.post(`/criminals/review-cases/${reviewCaseId}/merge`, payload);
        return data;
    },

    createManualDuplicateIdentityCase: async (payload: {
        source_criminal_id: string;
        matched_criminal_id: string;
        source_face_id?: string | null;
        matched_face_id?: string | null;
        distance: number;
        embedding_version: string;
        template_version?: string | null;
        submitted_filename?: string | null;
        notes?: string;
    }): Promise<ReviewCase> => {
        const { data } = await api.post('/criminals/review-cases/duplicate-identities/manual', payload);
        return data;
    },
};
