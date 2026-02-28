import { useState, useRef } from 'react';
import { UploadCloud, Loader2, UserCheck, UserX, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { recognitionApi, type RecognitionResult } from '@/api/recognition';

export default function Identify() {
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState<RecognitionResult[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            setFile(selectedFile);
            setPreview(URL.createObjectURL(selectedFile));
            setResults(null);
            setError(null);
        }
    };

    const handleIdentify = async () => {
        if (!file) return;

        try {
            setIsLoading(true);
            setError(null);
            const response = await recognitionApi.identifySuspect(file);
            setResults(response.results);
        } catch (err: any) {
            setError(err.response?.data?.detail || "Failed to identify faces.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-6 p-6 max-w-5xl mx-auto">
            <div>
                <h1 className="text-3xl font-bold text-white">Identify Suspect</h1>
                <p className="mt-1 text-sm text-zinc-400">
                    Upload an image or connect a camera feed to run facial recognition against the criminal database.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="border-zinc-800 bg-zinc-950/50 h-fit">
                    <CardHeader>
                        <CardTitle>Image Upload</CardTitle>
                        <CardDescription>Select an image to analyze</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col items-center justify-center p-8 m-4 border-2 border-dashed border-zinc-700 rounded-lg bg-zinc-900/40 relative overflow-hidden group">
                        {preview ? (
                            <div className="w-full text-center space-y-4">
                                <img src={preview} alt="Preview" className="max-h-64 object-contain mx-auto rounded" />
                                <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} className="border-zinc-700">Change Image</Button>
                            </div>
                        ) : (
                            <>
                                <UploadCloud className="w-12 h-12 text-zinc-500 mb-4 group-hover:text-blue-500 transition-colors" />
                                <p className="text-sm text-zinc-400 mb-4">Supported formats: JPG, PNG, WEBP</p>
                                <Button variant="outline" onClick={() => fileInputRef.current?.click()} className="border-zinc-700 hover:bg-zinc-800 hover:text-white">
                                    Select Image
                                </Button>
                            </>
                        )}
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            accept="image/jpeg, image/png, image/webp"
                            className="hidden"
                        />
                    </CardContent>
                    <CardFooter className="flex justify-end gap-3 px-6 pb-6">
                        <Button variant="ghost" onClick={() => { setFile(null); setPreview(null); setResults(null); }} disabled={!file || isLoading}>Clear</Button>
                        <Button onClick={handleIdentify} disabled={!file || isLoading} className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg w-32">
                            {isLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                            {isLoading ? 'Scanning...' : 'Identify'}
                        </Button>
                    </CardFooter>
                </Card>

                <div className="space-y-4">
                    <h3 className="text-lg font-semibold border-b border-zinc-800 pb-2">Analysis Results</h3>

                    {error && (
                        <div className="p-4 rounded-md bg-red-950/50 border border-red-900 text-red-200 text-sm flex items-start gap-3">
                            <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5" />
                            <p>{error}</p>
                        </div>
                    )}

                    {!results && !isLoading && !error && (
                        <div className="h-64 flex items-center justify-center border border-zinc-800 rounded-lg border-dashed text-zinc-500 text-sm">
                            Upload an image and run identification to see matches here.
                        </div>
                    )}

                    {isLoading && (
                        <div className="h-64 flex flex-col gap-4 items-center justify-center border border-zinc-800 rounded-lg bg-zinc-900/20 text-zinc-500">
                            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                            <p className="text-sm animate-pulse">Running vector similarity search...</p>
                        </div>
                    )}

                    {results && results.length === 0 && (
                        <div className="p-6 text-center border border-zinc-800 rounded-lg bg-zinc-900/20">
                            <UserX className="w-12 h-12 text-zinc-600 mx-auto mb-3" />
                            <h4 className="text-zinc-300 font-medium">No Faces Detected</h4>
                            <p className="text-sm text-zinc-500 mt-1">The AI could not detect any faces in this image.</p>
                        </div>
                    )}

                    {results && results.map((result, idx) => (
                        <Card key={idx} className={`border-l-4 ${result.status === 'match' ? 'border-l-red-500' : 'border-l-zinc-500'} bg-zinc-950`}>
                            <CardHeader className="pb-2">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-base flex items-center gap-2">
                                        {result.status === 'match' ? <UserCheck className="text-red-500 w-5 h-5" /> : <UserX className="text-zinc-500 w-5 h-5" />}
                                        {result.status === 'match' ? 'Database Match Found' : 'Unknown Individual'}
                                    </CardTitle>
                                    <span className={`text-xs px-2 py-1 rounded font-mono ${result.status === 'match' ? 'bg-red-950/50 text-red-400' : 'bg-zinc-800 text-zinc-400'}`}>
                                        {result.confidence.toFixed(1)}% Match
                                    </span>
                                </div>
                            </CardHeader>
                            {result.status === 'match' && result.criminal && (
                                <CardContent>
                                    <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-sm mt-2">
                                        <div>
                                            <p className="text-xs text-zinc-500">Name</p>
                                            <p className="font-semibold text-white">{result.criminal.name}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs text-zinc-500">NIC Mapping</p>
                                            <p className="text-zinc-300 font-mono">{result.criminal.nic}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs text-zinc-500">Threat Level</p>
                                            <span className="inline-flex items-center rounded-full mt-1 px-2 py-0.5 text-xs font-medium bg-red-950 text-red-400 border border-red-900">
                                                {result.criminal.threat_level}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="mt-4 pt-4 border-t border-zinc-800">
                                        <Button variant="outline" size="sm" className="w-full text-xs">View Full Profile</Button>
                                    </div>
                                </CardContent>
                            )}
                        </Card>
                    ))}
                </div>
            </div>
        </div>
    );
}
