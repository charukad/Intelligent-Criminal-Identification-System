import { api } from './client';

export interface Alert {
    id: string;
    title: string;
    message: string;
    severity: 'INFO' | 'WARNING' | 'CRITICAL';
    is_resolved: boolean;
    timestamp: string;
    criminal_id?: string;
    resolved_by_id?: string;
}

export const alertsApi = {
    getActiveAlerts: async (): Promise<Alert[]> => {
        const response = await api.get<Alert[]>('/alerts');
        return response.data;
    },
};
