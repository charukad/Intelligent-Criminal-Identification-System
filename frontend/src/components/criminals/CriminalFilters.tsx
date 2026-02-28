import { useState } from 'react';
import { Search, Filter, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';

interface CriminalFiltersProps {
    onSearchChange: (search: string) => void;
    onThreatLevelChange: (level: string) => void;
    onLegalStatusChange: (status: string) => void;
    onReset: () => void;
}

export function CriminalFilters({
    onSearchChange,
    onThreatLevelChange,
    onLegalStatusChange,
    onReset,
}: CriminalFiltersProps) {
    const [search, setSearch] = useState('');
    const [threatLevel, setThreatLevel] = useState('all');
    const [legalStatus, setLegalStatus] = useState('all');

    const handleSearchChange = (value: string) => {
        setSearch(value);
        onSearchChange(value);
    };

    const handleThreatLevelChange = (value: string) => {
        setThreatLevel(value);
        onThreatLevelChange(value === 'all' ? '' : value);
    };

    const handleLegalStatusChange = (value: string) => {
        setLegalStatus(value);
        onLegalStatusChange(value === 'all' ? '' : value);
    };

    const handleReset = () => {
        setSearch('');
        setThreatLevel('all');
        setLegalStatus('all');
        onReset();
    };

    const hasActiveFilters = search || threatLevel !== 'all' || legalStatus !== 'all';

    return (
        <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                <Input
                    placeholder="Search by name or NIC..."
                    value={search}
                    onChange={(e) => handleSearchChange(e.target.value)}
                    className="pl-10"
                />
            </div>

            <div className="flex gap-2">
                <Select value={threatLevel} onValueChange={handleThreatLevelChange}>
                    <SelectTrigger className="w-[180px]">
                        <Filter className="mr-2 h-4 w-4" />
                        <SelectValue placeholder="Threat Level" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Threat Levels</SelectItem>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="critical">Critical</SelectItem>
                    </SelectContent>
                </Select>

                <Select value={legalStatus} onValueChange={handleLegalStatusChange}>
                    <SelectTrigger className="w-[200px]">
                        <Filter className="mr-2 h-4 w-4" />
                        <SelectValue placeholder="Legal Status" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Statuses</SelectItem>
                        <SelectItem value="wanted">Wanted</SelectItem>
                        <SelectItem value="in_custody">In Custody</SelectItem>
                        <SelectItem value="released">Released</SelectItem>
                        <SelectItem value="deceased">Deceased</SelectItem>
                        <SelectItem value="cleared">Cleared</SelectItem>
                    </SelectContent>
                </Select>

                {hasActiveFilters && (
                    <Button
                        variant="outline"
                        onClick={handleReset}
                        className="border-zinc-700"
                    >
                        <X className="mr-2 h-4 w-4" />
                        Clear
                    </Button>
                )}
            </div>
        </div>
    );
}
