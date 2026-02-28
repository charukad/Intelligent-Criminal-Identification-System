import { api } from './client';

export interface RecognitionResult {
    box: [number, number, number, number];
    status: 'match' | 'unknown';
    confidence: number;
    criminal?: {
        id: string;
        name: string;
        nic: string;
        threat_level: string;
    };
}

export interface RecognitionResponse {
    results: RecognitionResult[];
}

export const recognitionApi = {
    identifySuspect: async (file: File): Promise<RecognitionResponse> => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await api.post<RecognitionResponse>('/recognition/identify', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });

        return response.data;
    },
};
