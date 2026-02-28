const rawBaseUrl = import.meta.env.VITE_API_URL || '';
const normalizedBaseUrl = rawBaseUrl.replace(/\/+$/, '');

function getLocalBackendRoot(): string {
    if (typeof window === 'undefined') {
        return '';
    }

    const { hostname } = window.location;
    if (!['localhost', '127.0.0.1'].includes(hostname)) {
        return '';
    }

    // For local browser use, call the backend directly on :8000 instead of
    // depending on a reverse proxy being present on the current origin.
    return `http://${hostname}:8000`;
}

export function getBackendRoot(): string {
    if (normalizedBaseUrl) {
        return normalizedBaseUrl.endsWith('/api/v1')
            ? normalizedBaseUrl.slice(0, -7)
            : normalizedBaseUrl;
    }

    return getLocalBackendRoot();
}

export function getApiBaseUrl(): string {
    const backendRoot = getBackendRoot();
    return backendRoot ? `${backendRoot}/api/v1` : '/api/v1';
}
