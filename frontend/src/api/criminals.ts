import { api } from './client';
import type { Criminal, CriminalFace } from '@/types/criminal';

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
