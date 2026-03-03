import { api } from './client';
import type { Criminal, CriminalFace, FaceQualityPreview } from '@/types/criminal';
import type { DuplicateReviewSummary } from '@/types/review';

export interface CriminalsListParams {
    page?: number;
    limit?: number;
    q?: string;
    threat_level?: string;
    status?: string;
}

export interface CriminalsListResponse {
    items: Criminal[];
    total: number;
    page: number;
    pages: number;
}

export interface CreateCriminalData {
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
}

export interface FaceUploadFailure {
    fileName: string;
    detail: string;
    duplicateReview?: DuplicateReviewSummary;
}

export interface FaceBatchUploadResult {
    uploaded: CriminalFace[];
    failed: FaceUploadFailure[];
}

export const criminalsApi = {
    // Get paginated list of criminals
    getAll: async (params: CriminalsListParams = {}): Promise<CriminalsListResponse> => {
        const cleanedParams = Object.fromEntries(
            Object.entries(params).filter(([, value]) => value !== '' && value !== undefined)
        );
        const { data } = await api.get('/criminals', { params: cleanedParams });
        return data;
    },

    // Get single criminal by ID
    getById: async (id: string): Promise<Criminal> => {
        const { data } = await api.get(`/criminals/${id}`);
        return data;
    },

    // Create new criminal
    create: async (criminalData: CreateCriminalData): Promise<Criminal> => {
        const cleaned = Object.fromEntries(
            Object.entries(criminalData).filter(([, value]) => value !== '' && value !== undefined)
        ) as CreateCriminalData;
        const { data } = await api.post('/criminals', cleaned);
        return data;
    },

    // Update criminal
    update: async (id: string, criminalData: Partial<CreateCriminalData>): Promise<Criminal> => {
        const cleaned = Object.fromEntries(
            Object.entries(criminalData).filter(([, value]) => value !== '' && value !== undefined)
        ) as Partial<CreateCriminalData>;
        const { data } = await api.put(`/criminals/${id}`, cleaned);
        return data;
    },

    uploadFace: async (criminalId: string, file: File, isPrimary = false): Promise<CriminalFace> => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('is_primary', String(isPrimary));
        const { data } = await api.post(`/criminals/${criminalId}/faces`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return data;
    },

    previewFaceQuality: async (file: File): Promise<FaceQualityPreview> => {
        const formData = new FormData();
        formData.append('file', file);
        const { data } = await api.post('/criminals/face-quality/preview', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return data;
    },

    uploadFaces: async (criminalId: string, files: File[], primaryIndex = 0): Promise<FaceBatchUploadResult> => {
        const uploaded: CriminalFace[] = [];
        const failed: FaceUploadFailure[] = [];
        let primaryWasUploaded = false;

        for (const [index, file] of files.entries()) {
            try {
                const response = await criminalsApi.uploadFace(criminalId, file, index === primaryIndex);
                if (index === primaryIndex) {
                    primaryWasUploaded = true;
                }
                uploaded.push(response);
            } catch (error: any) {
                const duplicateReview = parseDuplicateReviewFailure(error);
                failed.push({
                    fileName: file.name,
                    detail: duplicateReview?.message || parseErrorDetail(error),
                    duplicateReview: duplicateReview?.summary,
                });
            }
        }

        if (!primaryWasUploaded && uploaded.length > 0) {
            await criminalsApi.setPrimaryFace(criminalId, uploaded[0].id);
            uploaded[0] = {
                ...uploaded[0],
                is_primary: true,
            };
        }

        return { uploaded, failed };
    },

    listFaces: async (criminalId: string): Promise<CriminalFace[]> => {
        const { data } = await api.get(`/criminals/${criminalId}/faces`);
        return data;
    },

    deleteFace: async (criminalId: string, faceId: string): Promise<void> => {
        await api.delete(`/criminals/${criminalId}/faces/${faceId}`);
    },

    setPrimaryFace: async (criminalId: string, faceId: string): Promise<void> => {
        await api.post(`/criminals/${criminalId}/faces/${faceId}/primary`);
    },

    // Delete criminal
    delete: async (id: string): Promise<void> => {
        await api.delete(`/criminals/${id}`);
    },

    // Search criminals (uses list endpoint with q)
    search: async (query: string): Promise<CriminalsListResponse> => {
        const { data } = await api.get('/criminals', { params: { q: query } });
        return data;
    },
};

function parseErrorDetail(error: any): string {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string') {
        return detail;
    }
    if (detail && typeof detail?.message === 'string') {
        return detail.message;
    }
    return 'Face enrollment failed';
}

function parseDuplicateReviewFailure(error: any): { message: string; summary: DuplicateReviewSummary } | null {
    const detail = error?.response?.data?.detail;
    if (!detail || typeof detail !== 'object' || !detail.review_case_id || !detail.conflicting_criminal) {
        return null;
    }

    const summary: DuplicateReviewSummary = {
        review_case_id: String(detail.review_case_id),
        risk_level: detail.risk_level,
        distance: Number(detail.distance ?? 0),
        conflicting_criminal: {
            id: String(detail.conflicting_criminal.id),
            name: detail.conflicting_criminal.name,
            primary_face_image_url: detail.conflicting_criminal.primary_face_image_url ?? null,
        },
        status: 'open',
    };

    return {
        message:
            typeof detail.message === 'string'
                ? detail.message
                : `Probable duplicate identity conflict with ${summary.conflicting_criminal.name}.`,
        summary,
    };
}
