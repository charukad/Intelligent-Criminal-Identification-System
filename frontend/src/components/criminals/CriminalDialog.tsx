import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import type { Criminal, CriminalFormData } from '@/types/criminal';

const criminalSchema = z.object({
    full_name: z.string().min(3, 'Name must be at least 3 characters'),
    aliases: z.string().optional(),
    nic: z.string().optional(),
    date_of_birth: z.string().optional(),
    nationality: z.string().optional(),
    height: z.coerce.number().positive().optional(),
    weight: z.coerce.number().positive().optional(),
    eye_color: z.string().optional(),
    hair_color: z.string().optional(),
    identifying_marks: z.string().optional(),
    threat_level: z.string().optional(),
    legal_status: z.string().optional(),
    last_known_location: z.string().optional(),
});

interface CriminalDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    criminal?: Criminal;
    onSubmit: (data: CriminalFormData) => void;
    isLoading?: boolean;
}

export function CriminalDialog({
    open,
    onOpenChange,
    criminal,
    onSubmit,
    isLoading,
}: CriminalDialogProps) {
    const {
        register,
        handleSubmit,
        reset,
        setValue,
        watch,
        formState: { errors },
    } = useForm<CriminalFormData>({
        resolver: zodResolver(criminalSchema),
    });

    const threatLevel = watch('threat_level');
    const legalStatus = watch('legal_status');

    useEffect(() => {
        if (criminal) {
            reset({
                full_name: criminal.full_name,
                aliases: criminal.aliases?.join(', '),
                nic: criminal.nic || '',
                date_of_birth: criminal.date_of_birth || '',
                nationality: criminal.nationality || '',
                height: criminal.height,
                weight: criminal.weight,
                eye_color: criminal.eye_color || '',
                hair_color: criminal.hair_color || '',
                identifying_marks: criminal.identifying_marks || '',
                threat_level: criminal.threat_level || '',
                legal_status: criminal.legal_status || '',
                last_known_location: criminal.last_known_location || '',
            });
        } else {
            reset({
                full_name: '',
                aliases: '',
                nic: '',
                date_of_birth: '',
                nationality: '',
                height: undefined,
                weight: undefined,
                eye_color: '',
                hair_color: '',
                identifying_marks: '',
                threat_level: '',
                legal_status: '',
                last_known_location: '',
            });
        }
    }, [criminal, reset]);

    const handleFormSubmit = (data: CriminalFormData) => {
        onSubmit(data);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>
                        {criminal ? 'Edit Criminal Record' : 'Create New Criminal Record'}
                    </DialogTitle>
                    <DialogDescription>
                        {criminal
                            ? 'Update the criminal information below.'
                            : 'Fill in the details to create a new criminal record.'}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
                    {/* Personal Information */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-zinc-300">Personal Information</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="full_name">Full Name *</Label>
                                <Input
                                    id="full_name"
                                    {...register('full_name')}
                                    placeholder="John Doe"
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                                {errors.full_name && (
                                    <p className="text-xs text-red-400">{errors.full_name.message}</p>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="aliases">Aliases (comma-separated)</Label>
                                <Input
                                    id="aliases"
                                    {...register('aliases')}
                                    placeholder="Johnny, JD"
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="nic">NIC</Label>
                                <Input
                                    id="nic"
                                    {...register('nic')}
                                    placeholder="199012345678"
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="date_of_birth">Date of Birth</Label>
                                <Input
                                    id="date_of_birth"
                                    type="date"
                                    {...register('date_of_birth')}
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="nationality">Nationality</Label>
                                <Input
                                    id="nationality"
                                    {...register('nationality')}
                                    placeholder="Sri Lankan"
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Physical Characteristics */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-zinc-300">Physical Characteristics</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="height">Height (cm)</Label>
                                <Input
                                    id="height"
                                    type="number"
                                    {...register('height')}
                                    placeholder="175"
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="weight">Weight (kg)</Label>
                                <Input
                                    id="weight"
                                    type="number"
                                    {...register('weight')}
                                    placeholder="70"
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="eye_color">Eye Color</Label>
                                <Input
                                    id="eye_color"
                                    {...register('eye_color')}
                                    placeholder="Brown"
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="hair_color">Hair Color</Label>
                                <Input
                                    id="hair_color"
                                    {...register('hair_color')}
                                    placeholder="Black"
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                            </div>

                            <div className="space-y-2 md:col-span-2">
                                <Label htmlFor="identifying_marks">Identifying Marks</Label>
                                <Input
                                    id="identifying_marks"
                                    {...register('identifying_marks')}
                                    placeholder="Scar on left cheek, tattoo on right arm"
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Criminal Information */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-zinc-300">Criminal Information</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="threat_level">Threat Level</Label>
                                <Select
                                    value={threatLevel}
                                    onValueChange={(value) => setValue('threat_level', value)}
                                >
                                    <SelectTrigger className="bg-zinc-900/50 border-zinc-800">
                                        <SelectValue placeholder="Select threat level" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="LOW">Low</SelectItem>
                                        <SelectItem value="MEDIUM">Medium</SelectItem>
                                        <SelectItem value="HIGH">High</SelectItem>
                                        <SelectItem value="CRITICAL">Critical</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="legal_status">Legal Status</Label>
                                <Select
                                    value={legalStatus}
                                    onValueChange={(value) => setValue('legal_status', value)}
                                >
                                    <SelectTrigger className="bg-zinc-900/50 border-zinc-800">
                                        <SelectValue placeholder="Select legal status" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="WANTED">Wanted</SelectItem>
                                        <SelectItem value="DETAINED">Detained</SelectItem>
                                        <SelectItem value="CONVICTED">Convicted</SelectItem>
                                        <SelectItem value="RELEASED">Released</SelectItem>
                                        <SelectItem value="UNDER_INVESTIGATION">Under Investigation</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2 md:col-span-2">
                                <Label htmlFor="last_known_location">Last Known Location</Label>
                                <Input
                                    id="last_known_location"
                                    {...register('last_known_location')}
                                    placeholder="Colombo, Sri Lanka"
                                    className="bg-zinc-900/50 border-zinc-800"
                                />
                            </div>
                        </div>
                    </div>

                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={isLoading}
                            className="border-zinc-700"
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isLoading} className="bg-blue-600 hover:bg-blue-700">
                            {isLoading ? (
                                <>
                                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-transparent"></div>
                                    Saving...
                                </>
                            ) : criminal ? (
                                'Update Criminal'
                            ) : (
                                'Create Criminal'
                            )}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
