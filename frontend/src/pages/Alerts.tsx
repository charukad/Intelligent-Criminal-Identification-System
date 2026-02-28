import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Bell, ShieldAlert, AlertTriangle, AlertCircle, Loader2 } from 'lucide-react';
import { alertsApi } from '@/api/alerts';
import { formatDistanceToNow } from 'date-fns';

export default function Alerts() {
    const { data: alerts, isLoading } = useQuery({
        queryKey: ['activeAlerts'],
        queryFn: alertsApi.getActiveAlerts,
        refetchInterval: 10000 // Refetch every 10 seconds
    });

    const getIcon = (severity: string) => {
        switch (severity) {
            case 'CRITICAL': return <ShieldAlert className="w-5 h-5 text-red-500" />;
            case 'WARNING': return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
            case 'INFO':
            default: return <AlertCircle className="w-5 h-5 text-blue-500" />;
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">System Alerts</h1>
                <p className="text-muted-foreground mt-2">
                    Active notifications and critical events require attention.
                </p>
            </div>

            <Card className="border-red-900 border xl:col-span-2">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Bell className="w-5 h-5 text-red-500" />
                        <CardTitle>Active Alerts</CardTitle>
                    </div>
                    <CardDescription>Real-time notifications from the AI tracking pipeline.</CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="flex justify-center flex-col items-center py-10">
                            <Loader2 className="w-8 h-8 animate-spin text-zinc-500 mb-4" />
                            <p className="text-zinc-500">Loading alerts...</p>
                        </div>
                    ) : alerts && alerts.length > 0 ? (
                        <div className="space-y-4">
                            {alerts.map((alert) => (
                                <div key={alert.id} className="flex gap-4 p-4 border border-zinc-800 rounded-lg bg-zinc-900/50 hover:bg-zinc-800/80 transition-colors">
                                    <div className="mt-1">
                                        {getIcon(alert.severity)}
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center justify-between mb-1">
                                            <h4 className="font-semibold text-zinc-100">{alert.title}</h4>
                                            <span className="text-xs text-zinc-500">
                                                {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                                            </span>
                                        </div>
                                        <p className="text-sm text-zinc-400">{alert.message}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center p-10 border-2 border-dashed border-zinc-800 rounded-lg">
                            <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mb-4">
                                <Bell className="w-8 h-8 text-green-500" />
                            </div>
                            <h3 className="text-lg font-medium text-white mb-2">No Active Alerts</h3>
                            <p className="text-zinc-500 text-center max-w-sm">The system is currently operating nominally. Any suspect identifications will appear here.</p>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
