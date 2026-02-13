import { api } from './client';
import { Criminal } from '@/types/criminal';

export interface CriminalsListParams {
    page?: number;
    limit?: number;
    search?: string;
    threat_level?: string;
    legal_status?: string;
}

export interface CriminalsListResponse {
    items: Criminal[];
    total: number;
    page: number;
    pages: number;
}

export interface CreateCriminalData {
    full_name: string;
    aliases?: string[];
    nic?: string;
    date_of_birth?: string;
    nationality?: string;
    height?: number;
    weight?: number;
    eye_color?: string;
    hair_color?: string;
    identifying_marks?: string;
    threat_level?: string;
    legal_status?: string;
    last_known_location?: string;
}

export const criminalsApi = {
    // Get paginated list of criminals
    getAll: async (params: CriminalsListParams = {}): Promise<CriminalsListResponse> => {
        const { data } = await api.get('/criminals', { params });
        return data;
    },

    // Get single criminal by ID
    getById: async (id: string): Promise<Criminal> => {
        const { data } = await api.get(`/criminals/${id}`);
        return data;
    },

    // Create new criminal
    create: async (criminalData: CreateCriminalData): Promise<Criminal> => {
        const { data } = await api.post('/criminals', criminalData);
        return data;
    },

    // Update criminal
    update: async (id: string, criminalData: Partial<CreateCriminalData>): Promise<Criminal> => {
        const { data } = await api.put(`/criminals/${id}`, criminalData);
        return data;
    },

    // Delete criminal
    delete: async (id: string): Promise<void> => {
        await api.delete(`/criminals/${id}`);
    },

    // Search criminals
    search: async (query: string): Promise<Criminal[]> => {
        const { data } = await api.get('/criminals/search', { params: { q: query } });
        return data;
    },
};
