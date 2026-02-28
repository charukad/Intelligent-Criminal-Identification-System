import { api } from './client';

export interface StatsData {
    totalCriminals: number;
    criticalAlerts: number;
    recentIdentifications: number;
    activeInvestigations: number;
}

export const statsApi = {
    getDashboardStats: async (): Promise<StatsData> => {
        const response = await api.get('/stats');
        return response.data;
    },
};
