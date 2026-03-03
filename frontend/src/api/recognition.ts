import { api } from './client';
import type { RecognitionResponse } from '@/types/recognition';

export const recognitionApi = {
    identifySuspect: async (
        file: File,
        options?: {
            debug?: boolean;
            mode?: 'single' | 'scene';
        }
    ): Promise<RecognitionResponse> => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await api.post<RecognitionResponse>('/recognition/identify', formData, {
            params: {
                debug: options?.debug ?? false,
                mode: options?.mode ?? 'single',
            },
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });

        return response.data;
    },
};
