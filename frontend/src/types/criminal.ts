export interface Criminal {
    id: string;
    full_name: string;
    aliases?: string[];
    nic?: string;
    date_of_birth?: string;
    nationality?: string;
    height?: number;
    weight?: number;
    eye_color?: string;
    hair_color?: string;
    identifying_marks?: string;
    threat_level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    legal_status?: 'WANTED' | 'DETAINED' | 'CONVICTED' | 'RELEASED' | 'UNDER_INVESTIGATION';
    last_known_location?: string;
    mugshot_url?: string;
    created_at?: string;
    updated_at?: string;
}

export interface CriminalFormData {
    full_name: string;
    aliases?: string;
    nic?: string;
    date_of_birth?: string;
    nationality?: string;
    height?: number;
    weight?: number;
    eye_color?: string;
    hair_color?: string;
    identifying_marks?: string;
    threat_level?: string;
    legal_status?: string;
    last_known_location?: string;
}
