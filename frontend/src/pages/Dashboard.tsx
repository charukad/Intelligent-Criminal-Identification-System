import { useQuery } from '@tanstack/react-query';
import { Users, ShieldAlert, Activity, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { statsApi } from '@/api/stats';
import { healthApi } from '@/api/health';

export default function Dashboard() {
    const { data: stats } = useQuery({
        queryKey: ['dashboardStats'],
        queryFn: statsApi.getDashboardStats,
        initialData: {
            totalCriminals: 0,
            criticalAlerts: 0,
            recentIdentifications: 0,
            activeInvestigations: 0,
        },
        refetchInterval: 10000 // refresh every 10s
    });

    const { data: health } = useQuery({
        queryKey: ['systemHealth'],
        queryFn: healthApi.getHealth,
        initialData: {
            status: 'degraded',
            services: { database: 'offline', api: 'offline' }
        },
        refetchInterval: 30000 // refresh every 30s
    });

    const statCards = [
        {
            title: 'Total Criminals',
            value: stats.totalCriminals.toLocaleString(),
            description: 'Registered in database',
            icon: Users,
            color: 'text-blue-500',
        },
        {
            title: 'Critical Alerts',
            value: stats.criticalAlerts,
            description: 'High-threat suspects',
            icon: ShieldAlert,
            color: 'text-red-500',
        },
        {
            title: 'Recent IDs',
            value: stats.recentIdentifications,
            description: 'Last 24 hours',
            icon: Activity,
            color: 'text-green-500',
        },
        {
            title: 'Active Cases',
            value: stats.activeInvestigations,
            description: 'Ongoing investigations',
            icon: TrendingUp,
            color: 'text-yellow-500',
        },
    ];

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Dashboard Overview</h1>
                <p className="text-muted-foreground mt-2">
                    Real-time monitoring and analytics for law enforcement operations
                </p>
            </div>

            {/* Stats Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {statCards.map((stat) => (
                    <Card key={stat.title} className="hover:shadow-lg transition-shadow">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                            <stat.icon className={`h-5 w-5 ${stat.color}`} />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{stat.value}</div>
                            <p className="text-xs text-muted-foreground mt-1">{stat.description}</p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Recent Activity */}
            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Recent Identifications</CardTitle>
                        <CardDescription>Latest facial recognition matches</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="h-40 flex items-center justify-center text-sm text-muted-foreground">
                            No recent identifications to show yet.
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>System Status</CardTitle>
                        <CardDescription>AI engine and database health</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <span className="text-sm">Database Access</span>
                                <div className="flex items-center gap-2">
                                    <div className={`w-2 h-2 rounded-full ${health.services.database === 'online' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                                    <span className="text-xs text-muted-foreground capitalize">{health.services.database}</span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm">Server API</span>
                                <div className="flex items-center gap-2">
                                    <div className={`w-2 h-2 rounded-full ${health.services.api === 'online' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                                    <span className="text-xs text-muted-foreground capitalize">{health.services.api}</span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm">System Status</span>
                                <div className="flex items-center gap-2">
                                    <div className={`w-2 h-2 rounded-full ${health.status === 'ok' ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`} />
                                    <span className="text-xs text-muted-foreground capitalize">{health.status === 'ok' ? 'nominal' : health.status}</span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between pt-2 border-t">
                                <span className="text-sm text-muted-foreground">{stats.totalCriminals.toLocaleString()} profiles</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
