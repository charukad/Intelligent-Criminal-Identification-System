import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { AuthState } from '@/types/auth';
import type { User } from '@/types/user';

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            token: null,
            isAuthenticated: false,
            hasHydrated: false,
            setHasHydrated: (value: boolean) => set({ hasHydrated: value }),
            login: (token: string, user?: User) =>
                set({ token, user: user ?? get().user, isAuthenticated: true }),
            logout: () => set({ token: null, user: null, isAuthenticated: false }),
            setUser: (user: User | null) => set({ user }),
            setToken: (token: string | null) =>
                set({ token, isAuthenticated: Boolean(token) }),
        }),
        {
            name: 'auth-storage',
            storage: createJSONStorage(() => localStorage),
            onRehydrateStorage: () => (state) => {
                if (!state) {
                    return;
                }
                // Migrate legacy storage keys if present
                if (!state.token) {
                    const legacyToken = localStorage.getItem('token');
                    const legacyUser = localStorage.getItem('user');
                    if (legacyToken) {
                        state.setToken(legacyToken);
                    }
                    if (legacyUser) {
                        try {
                            state.setUser(JSON.parse(legacyUser));
                        } catch {
                            state.setUser(null);
                        }
                    }
                }
                state.setHasHydrated(true);
            },
        }
    )
);
