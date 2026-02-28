import { createContext, useContext, useEffect, type ReactNode } from 'react';
import type { User, UserRole } from '@/types/user';
import { api } from '@/api/client';
import { useAuthStore } from '@/store/authStore';

interface AuthContextType {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
    hasRole: (roles: UserRole[]) => boolean;
    isAdmin: boolean;
    isSeniorOfficer: boolean;
    isFieldOfficer: boolean;
    isViewer: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const user = useAuthStore((state) => state.user);
    const token = useAuthStore((state) => state.token);
    const isLoading = !useAuthStore((state) => state.hasHydrated);
    const hasHydrated = useAuthStore((state) => state.hasHydrated);
    const setUser = useAuthStore((state) => state.setUser);
    const loginToStore = useAuthStore((state) => state.login);
    const logoutFromStore = useAuthStore((state) => state.logout);

    useEffect(() => {
        if (!hasHydrated || !token) {
            return;
        }

        const fetchProfile = async () => {
            try {
                const userResponse = await api.get('/auth/me', {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });
                const userData = userResponse.data;
                setUser(userData);
                loginToStore(token, userData);
            } catch {
                logoutFromStore();
            }
        };
        fetchProfile();
    }, [hasHydrated, token, setUser, loginToStore, logoutFromStore]);

    const login = async (username: string, password: string) => {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await api.post('/auth/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });

        const { access_token } = response.data;
        loginToStore(access_token);

        // Fetch user profile
        const userResponse = await api.get('/auth/me', {
            headers: {
                Authorization: `Bearer ${access_token}`,
            },
        });

        const userData = userResponse.data;
        setUser(userData);
        loginToStore(access_token, userData);
    };

    const logout = () => {
        logoutFromStore();
    };

    const hasRole = (roles: UserRole[]): boolean => {
        if (!user) return false;
        return roles.includes(user.role);
    };

    const value: AuthContextType = {
        user,
        token,
        isLoading,
        login,
        logout,
        hasRole,
        isAdmin: user?.role === 'admin',
        isSeniorOfficer: user?.role === 'senior_officer',
        isFieldOfficer: user?.role === 'field_officer',
        isViewer: user?.role === 'viewer',
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
