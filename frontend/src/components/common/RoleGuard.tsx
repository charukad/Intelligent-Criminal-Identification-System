import type { ReactNode } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import type { UserRole } from '@/types/user';

interface RoleGuardProps {
    allowedRoles: UserRole[];
    children: ReactNode;
    fallback?: ReactNode;
}

/**
 * RoleGuard component - conditionally renders children based on user role
 * 
 * @example
 * <RoleGuard allowedRoles={['admin', 'senior_officer']}>
 *   <AdminOnlyButton />
 * </RoleGuard>
 */
export function RoleGuard({ allowedRoles, children, fallback = null }: RoleGuardProps) {
    const { hasRole } = useAuth();

    if (!hasRole(allowedRoles)) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
}
