export interface User {
    id: string;
    username: string;
    email: string;
    role: "admin" | "senior_officer" | "field_officer" | "viewer";
    is_active: boolean;
    station_id?: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
}

export interface AuthState {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    login: (token: string) => void;
    logout: () => void;
    setUser: (user: User) => void;
}
