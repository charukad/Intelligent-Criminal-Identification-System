import { useEffect, useState } from 'react';
import { Users, ShieldAlert, Activity, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface StatsData {
    totalCriminals: number;
    criticalAlerts: number;
    recentIdentifications: number;
    activeInvestigations: number;
}

export default function Dashboard() {
    const [stats, setStats] = useState<StatsData>({
        totalCriminals: 0,
        criticalAlerts: 0,
        recentIdentifications: 0,
        activeInvestigations: 0,
    });

    useEffect(() => {
        // TODO: Fetch real stats from API
        // For now, using mock data
        setStats({
            totalCriminals: 1247,
            criticalAlerts: 8,
            recentIdentifications: 34,
            activeInvestigations: 156,
        });
    }, []);

    const statCards = [
        {
            title: 'Total Criminals',
            value: stats.totalCriminals.toLocaleString(),
            description: 'Registered in database',
            icon: Users,
            trend: '+12% from last month',
            color: 'text-blue-500',
        },
        {
            title: 'Critical Alerts',
            value: stats.criticalAlerts,
            description: 'High-threat suspects',
            icon: ShieldAlert,
            trend: '-3 from last week',
            color: 'text-red-500',
        },
        {
            title: 'Recent IDs',
            value: stats.recentIdentifications,
            description: 'Last 24 hours',
            icon: Activity,
            trend: '+8 since yesterday',
            color: 'text-green-500',
        },
        {
            title: 'Active Cases',
            value: stats.activeInvestigations,
            description: 'Ongoing investigations',
            icon: TrendingUp,
            trend: 'Stable',
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
                            <p className="text-xs text-muted-foreground mt-2 opacity-70">{stat.trend}</p>
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
                        <div className="space-y-4">
                            {[1, 2, 3].map((i) => (
                                <div key={i} className="flex items-center justify-between border-b pb-3 last:border-0">
                                    <div className="space-y-1">
                                        <p className="text-sm font-medium">Suspect #{1000 + i}</p>
                                        <p className="text-xs text-muted-foreground">
                                            Matched at {i === 1 ? 'Central Station' : i === 2 ? 'Airport Terminal' : 'City Mall'}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xs text-muted-foreground">{i}h ago</p>
                                        <span className="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-red-50 text-red-700 dark:bg-red-950/20">
                                            {i === 1 ? 'Critical' : 'Medium'}
                                        </span>
                                    </div>
                                </div>
                            ))}
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
                                <span className="text-sm">Face Detection Service</span>
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                    <span className="text-xs text-muted-foreground">Online</span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm">Vector Database</span>
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                    <span className="text-xs text-muted-foreground">Online</span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm">Recognition API</span>
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                    <span className="text-xs text-muted-foreground">Online</span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between pt-2 border-t">
                                <span className="text-sm font-medium">Database Size</span>
                                <span className="text-sm text-muted-foreground">1,247 profiles</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
