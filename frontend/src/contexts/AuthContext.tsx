import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { User, UserRole } from '@/types/user';
import { api } from '@/api/client';

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
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Load token and user from localStorage on mount
    useEffect(() => {
        const storedToken = localStorage.getItem('token');
        const storedUser = localStorage.getItem('user');

        if (storedToken && storedUser) {
            setToken(storedToken);
            setUser(JSON.parse(storedUser));
        }
        setIsLoading(false);
    }, []);

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
        setToken(access_token);

        // Store token
        localStorage.setItem('token', access_token);

        // Fetch user profile
        const userResponse = await api.get('/auth/me', {
            headers: {
                Authorization: `Bearer ${access_token}`,
            },
        });

        const userData = userResponse.data;
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
    };

    const logout = () => {
        setUser(null);
        setToken(null);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
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
