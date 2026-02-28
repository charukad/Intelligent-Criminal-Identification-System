import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
    Users,
    ShieldAlert,
    Search,
    LogOut,
    LayoutDashboard,
    Menu,
    X
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/lib/utils';

export default function DashboardLayout() {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const user = useAuthStore((state) => state.user);
    const logout = useAuthStore((state) => state.logout);
    const navigate = useNavigate();

    const role = user?.role;
    const roleAccent =
        role === 'admin'
            ? 'bg-red-500'
            : role === 'senior_officer'
            ? 'bg-amber-500'
            : role === 'field_officer'
            ? 'bg-blue-500'
            : 'bg-zinc-500';
    const roleAccentText =
        role === 'admin'
            ? 'text-red-500'
            : role === 'senior_officer'
            ? 'text-amber-500'
            : role === 'field_officer'
            ? 'text-blue-500'
            : 'text-zinc-500';
    const roleClass =
        role === 'admin'
            ? 'role-admin'
            : role === 'senior_officer'
            ? 'role-senior'
            : role === 'field_officer'
            ? 'role-field'
            : 'role-default';

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const navItems = [
        { icon: LayoutDashboard, label: 'Overview', href: '/dashboard' },
        { icon: Users, label: 'Criminals', href: '/dashboard/criminals' },
        { icon: Search, label: 'Identify', href: '/dashboard/identify' },
        { icon: ShieldAlert, label: 'Alerts', href: '/dashboard/alerts' },
    ];

    return (
        <div className={cn("min-h-screen bg-background flex", roleClass)}>
            {/* Mobile Sidebar Overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={cn(
                "fixed lg:static inset-y-0 left-0 z-50 w-64 border-r bg-card transition-transform duration-300 ease-in-out lg:translate-x-0",
                sidebarOpen ? "translate-x-0" : "-translate-x-full"
            )}>
                <div className="h-full flex flex-col">
                    {/* Header */}
                    <div className="h-16 flex items-center px-6 border-b">
                        <div className={`w-8 h-8 rounded-full mr-3 animate-pulse ${roleAccent}`} />
                        <span className="font-bold text-xl tracking-tight">TraceIQ</span>
                        <button
                            className="ml-auto lg:hidden"
                            onClick={() => setSidebarOpen(false)}
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Nav */}
                    <div className="flex-1 py-6 px-3 space-y-1">
                        {navItems.map((item) => (
                            <NavLink
                                key={item.href}
                                to={item.href}
                                end={item.href === '/dashboard'} // Exact match for root dashboard
                                className={({ isActive }) => cn(
                                    "flex items-center px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                                    isActive
                                        ? "bg-primary text-primary-foreground shadow-sm"
                                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                                )}
                                onClick={() => setSidebarOpen(false)}
                            >
                                <item.icon className="w-4 h-4 mr-3" />
                                {item.label}
                            </NavLink>
                        ))}
                    </div>

                    {/* Footer / User */}
                    <div className="p-4 border-t bg-muted/20">
                        <div className="flex items-center mb-4">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${roleAccent} text-white`}>
                                {user?.username?.substring(0, 2).toUpperCase() || 'OF'}
                            </div>
                            <div className="ml-3 overflow-hidden">
                                <p className="text-sm font-medium truncate">{user?.username}</p>
                                <p className={`text-xs truncate capitalize ${roleAccentText}`}>
                                    {user?.role?.replace('_', ' ')}
                                </p>
                            </div>
                        </div>
                        <Button
                            variant="outline"
                            className="w-full justify-start text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
                            onClick={handleLogout}
                        >
                            <LogOut className="w-4 h-4 mr-2" />
                            Sign Out
                        </Button>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
                {/* Top Mobile Bar */}
                <header className="h-16 lg:hidden flex items-center px-4 border-b bg-card">
                    <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(true)}>
                        <Menu className="w-5 h-5" />
                    </Button>
                    <span className="ml-4 font-semibold">TraceIQ</span>
                </header>

                {/* Content Area */}
                <div className="flex-1 overflow-auto p-4 lg:p-8">
                    <div className="max-w-7xl mx-auto">
                        <Outlet />
                    </div>
                </div>
            </main>
        </div>
    );
}
