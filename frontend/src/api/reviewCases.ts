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
};
