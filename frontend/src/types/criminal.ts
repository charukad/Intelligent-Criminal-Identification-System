export interface Criminal {
    id: string;
    first_name: string;
    last_name: string;
    aliases?: string;
    nic?: string;
    dob?: string;
    gender: string;
    blood_type?: string;
    status?: 'wanted' | 'in_custody' | 'released' | 'deceased' | 'cleared';
    threat_level?: 'low' | 'medium' | 'high' | 'critical';
    last_known_address?: string;
    physical_description?: string;
    primary_face_image_url?: string | null;
}

export interface CriminalFace {
    id: string;
    criminal_id: string;
    image_url: string;
    is_primary: boolean;
    embedding_version: string;
    created_at: string;
    box: [number, number, number, number];
}

export interface CriminalFormData {
    first_name: string;
    last_name: string;
    aliases?: string;
    nic?: string;
    dob?: string;
    gender: string;
    blood_type?: string;
    status?: string;
    threat_level?: string;
    last_known_address?: string;
    physical_description?: string;
    faceFiles?: File[];
    primaryFaceIndex?: number;
}
