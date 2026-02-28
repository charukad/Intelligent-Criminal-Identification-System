import type { User } from '@/types/user';

export interface AuthResponse {
    access_token: string;
    token_type: string;
}

export interface AuthState {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    hasHydrated: boolean;
    setHasHydrated: (value: boolean) => void;
    login: (token: string, user?: User) => void;
    logout: () => void;
    setUser: (user: User | null) => void;
    setToken: (token: string | null) => void;
}
