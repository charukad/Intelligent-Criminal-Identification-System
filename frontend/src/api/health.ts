import axios from 'axios';
import { getBackendRoot } from '@/api/baseUrl';

const BASE_URL = getBackendRoot();

export interface SystemHealth {
    status: string;
    services: {
        database: string;
        api: string;
    }
}

export const healthApi = {
    getHealth: async (): Promise<SystemHealth> => {
        const response = await axios.get(`${BASE_URL}/health`);
        return response.data;
    },
};
