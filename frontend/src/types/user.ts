export type UserRole = 'admin' | 'senior_officer' | 'field_officer' | 'viewer';

export interface User {
    id: string;
    username: string;
    email: string;
    role: UserRole;
    badge_number?: string;
    is_active: boolean;
    station_id?: string;
    created_at: string;
}

export interface UserCreate {
    username: string;
    email: string;
    password: string;
    role?: UserRole;
    badge_number?: string;
    station_id?: string;
}

export interface UserUpdate {
    username?: string;
    email?: string;
    password?: string;
    role?: UserRole;
    badge_number?: string;
    station_id?: string;
    is_active?: boolean;
}

export interface UserResponse {
    id: string;
    username: string;
    email: string;
    role: UserRole;
    badge_number?: string;
    is_active: boolean;
    station_id?: string;
    created_at: string;
}
