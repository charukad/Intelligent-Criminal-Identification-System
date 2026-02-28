import { useEffect, useState } from 'react';
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
    first_name: z.string().min(2, 'First name must be at least 2 characters'),
    last_name: z.string().min(2, 'Last name must be at least 2 characters'),
    aliases: z.string().optional(),
    nic: z.string().optional(),
    dob: z.string().optional(),
    gender: z.string().min(1, 'Gender is required'),
    blood_type: z.string().optional(),
    threat_level: z.string().optional(),
    status: z.string().optional(),
    last_known_address: z.string().optional(),
    physical_description: z.string().optional(),
});

type CriminalFields = z.infer<typeof criminalSchema>;

interface CriminalDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    criminal?: Criminal;
    onSubmit: (data: CriminalFormData) => void | Promise<void>;
    isLoading?: boolean;
}

export function CriminalDialog({
    open,
    onOpenChange,
    criminal,
    onSubmit,
    isLoading,
}: CriminalDialogProps) {
    const [faceFile, setFaceFile] = useState<File | null>(null);
    const [enrollFaceAsPrimary, setEnrollFaceAsPrimary] = useState(true);
    const {
        register,
        handleSubmit,
        reset,
        setValue,
        watch,
        formState: { errors },
    } = useForm<CriminalFields>({
        resolver: zodResolver(criminalSchema),
    });

    const threatLevel = watch('threat_level');
    const legalStatus = watch('status');
    const gender = watch('gender');

    useEffect(() => {
        if (criminal) {
            reset({
                first_name: criminal.first_name,
                last_name: criminal.last_name,
                aliases: criminal.aliases || '',
                nic: criminal.nic || '',
                dob: criminal.dob || '',
                gender: criminal.gender || '',
                blood_type: criminal.blood_type || '',
                threat_level: criminal.threat_level || '',
                status: criminal.status || '',
                last_known_address: criminal.last_known_address || '',
                physical_description: criminal.physical_description || '',
            });
            setFaceFile(null);
            setEnrollFaceAsPrimary(true);
        } else {
            reset({
                first_name: '',
                last_name: '',
                aliases: '',
                nic: '',
                dob: '',
                gender: '',
                blood_type: '',
                threat_level: '',
                status: '',
                last_known_address: '',
                physical_description: '',
            });
            setFaceFile(null);
            setEnrollFaceAsPrimary(true);
        }
    }, [criminal, reset]);

    useEffect(() => {
        if (!open) {
            setFaceFile(null);
            setEnrollFaceAsPrimary(true);
        }
    }, [open]);

    const handleFormSubmit = (data: CriminalFields) => {
        onSubmit({
            ...data,
            faceFile,
            enrollFaceAsPrimary,
        });
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
                                <Label htmlFor="first_name">First Name *</Label>
                                <Input
                                    id="first_name"
                                    {...register('first_name')}
                                    placeholder="John"
                                    className="bg-zinc-800 border-zinc-600"
                                />
                                {errors.first_name && (
                                    <p className="text-xs text-red-400">{errors.first_name.message}</p>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="last_name">Last Name *</Label>
                                <Input
                                    id="last_name"
                                    {...register('last_name')}
                                    placeholder="Doe"
                                    className="bg-zinc-800 border-zinc-600"
                                />
                                {errors.last_name && (
                                    <p className="text-xs text-red-400">{errors.last_name.message}</p>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="aliases">Aliases (comma-separated)</Label>
                                <Input
                                    id="aliases"
                                    {...register('aliases')}
                                    placeholder="Johnny, JD"
                                    className="bg-zinc-800 border-zinc-600"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="nic">NIC</Label>
                                <Input
                                    id="nic"
                                    {...register('nic')}
                                    placeholder="199012345678"
                                    className="bg-zinc-800 border-zinc-600"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="dob">Date of Birth</Label>
                                <Input
                                    id="dob"
                                    type="date"
                                    {...register('dob')}
                                    className="bg-zinc-800 border-zinc-600"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="gender">Gender *</Label>
                                <input type="hidden" {...register('gender')} />
                                <Select
                                    value={gender}
                                    onValueChange={(value) => setValue('gender', value)}
                                >
                                    <SelectTrigger className="bg-zinc-800 border-zinc-600">
                                        <SelectValue placeholder="Select gender" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="male">Male</SelectItem>
                                        <SelectItem value="female">Female</SelectItem>
                                        <SelectItem value="other">Other</SelectItem>
                                    </SelectContent>
                                </Select>
                                {errors.gender && (
                                    <p className="text-xs text-red-400">{errors.gender.message}</p>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Physical Characteristics */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-zinc-300">Physical Characteristics</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="blood_type">Blood Type</Label>
                                <Input
                                    id="blood_type"
                                    {...register('blood_type')}
                                    placeholder="O+"
                                    className="bg-zinc-800 border-zinc-600"
                                />
                            </div>

                            <div className="space-y-2 md:col-span-2">
                                <Label htmlFor="physical_description">Physical Description</Label>
                                <Input
                                    id="physical_description"
                                    {...register('physical_description')}
                                    placeholder="Scar on left cheek, tattoo on right arm"
                                    className="bg-zinc-800 border-zinc-600"
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
                                <input type="hidden" {...register('threat_level')} />
                                <Select
                                    value={threatLevel}
                                    onValueChange={(value) => setValue('threat_level', value)}
                                >
                                    <SelectTrigger className="bg-zinc-800 border-zinc-600">
                                        <SelectValue placeholder="Select threat level" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="low">Low</SelectItem>
                                        <SelectItem value="medium">Medium</SelectItem>
                                        <SelectItem value="high">High</SelectItem>
                                        <SelectItem value="critical">Critical</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="status">Legal Status</Label>
                                <input type="hidden" {...register('status')} />
                                <Select
                                    value={legalStatus}
                                    onValueChange={(value) => setValue('status', value)}
                                >
                                    <SelectTrigger className="bg-zinc-800 border-zinc-600">
                                        <SelectValue placeholder="Select legal status" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="wanted">Wanted</SelectItem>
                                        <SelectItem value="in_custody">In Custody</SelectItem>
                                        <SelectItem value="released">Released</SelectItem>
                                        <SelectItem value="deceased">Deceased</SelectItem>
                                        <SelectItem value="cleared">Cleared</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2 md:col-span-2">
                                <Label htmlFor="last_known_address">Last Known Address</Label>
                                <Input
                                    id="last_known_address"
                                    {...register('last_known_address')}
                                    placeholder="No. 12, Main Street, Colombo"
                                    className="bg-zinc-800 border-zinc-600"
                                />
                            </div>
                        </div>
                    </div>

                    {!criminal && (
                        <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
                            <div>
                                <h3 className="text-sm font-semibold text-zinc-200">Face Enrollment</h3>
                                <p className="mt-1 text-xs text-zinc-500">
                                    Upload a clear mugshot now to generate a TraceNet embedding for identification.
                                </p>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="face_image">Mugshot Image</Label>
                                <Input
                                    id="face_image"
                                    type="file"
                                    accept="image/jpeg,image/png,image/webp"
                                    className="bg-zinc-800 border-zinc-600 file:text-zinc-300"
                                    onChange={(event) => {
                                        setFaceFile(event.target.files?.[0] ?? null);
                                    }}
                                />
                                <p className="text-xs text-zinc-500">
                                    {faceFile ? `Selected: ${faceFile.name}` : 'Optional. Add later if needed.'}
                                </p>
                            </div>
                            <label className="flex items-center gap-3 text-sm text-zinc-300">
                                <input
                                    type="checkbox"
                                    className="h-4 w-4 rounded border-zinc-600 bg-zinc-900 text-primary"
                                    checked={enrollFaceAsPrimary}
                                    onChange={(event) => setEnrollFaceAsPrimary(event.target.checked)}
                                />
                                Mark this image as the primary face record
                            </label>
                        </div>
                    )}

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
                        <Button type="submit" disabled={isLoading} className="bg-primary text-primary-foreground hover:bg-primary/90">
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
