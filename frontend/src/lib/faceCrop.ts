export interface FaceCropDraft {
    id: string;
    sourceFile: File;
    previewUrl: string;
    naturalWidth: number;
    naturalHeight: number;
    cropX: number;
    cropY: number;
    cropWidth: number;
    cropHeight: number;
}

export type CropPreset = 'reset' | 'square' | 'portrait' | 'landscape';

const MIN_CROP_SIZE = 80;

function getCenteredCrop(width: number, height: number) {
    const size = Math.max(MIN_CROP_SIZE, Math.round(Math.min(width, height) * 0.82));
    return {
        cropWidth: Math.min(width, size),
        cropHeight: Math.min(height, size),
        cropX: Math.max(0, Math.round((width - size) / 2)),
        cropY: Math.max(0, Math.round((height - size) / 2)),
    };
}

function clamp(value: number, min: number, max: number) {
    return Math.min(Math.max(value, min), max);
}

async function loadImageDimensions(file: File): Promise<{ width: number; height: number }> {
    const objectUrl = URL.createObjectURL(file);
    try {
        const image = new Image();
        const dimensions = await new Promise<{ width: number; height: number }>((resolve, reject) => {
            image.onload = () => resolve({ width: image.naturalWidth, height: image.naturalHeight });
            image.onerror = () => reject(new Error(`Failed to load ${file.name}`));
            image.src = objectUrl;
        });
        return dimensions;
    } finally {
        URL.revokeObjectURL(objectUrl);
    }
}

export async function createFaceCropDrafts(files: File[]): Promise<FaceCropDraft[]> {
    const imageFiles = files.filter((file) => file.type.startsWith('image/'));

    return Promise.all(
        imageFiles.map(async (file) => {
            const { width, height } = await loadImageDimensions(file);
            const crop = getCenteredCrop(width, height);

            return {
                id: crypto.randomUUID(),
                sourceFile: file,
                previewUrl: URL.createObjectURL(file),
                naturalWidth: width,
                naturalHeight: height,
                ...crop,
            };
        })
    );
}

export function revokeFaceCropDrafts(drafts: FaceCropDraft[]) {
    for (const draft of drafts) {
        URL.revokeObjectURL(draft.previewUrl);
    }
}

export function updateFaceCropDraft(
    draft: FaceCropDraft,
    patch: Partial<Pick<FaceCropDraft, 'cropX' | 'cropY' | 'cropWidth' | 'cropHeight'>>
): FaceCropDraft {
    let cropWidth = Math.round(patch.cropWidth ?? draft.cropWidth);
    let cropHeight = Math.round(patch.cropHeight ?? draft.cropHeight);
    cropWidth = clamp(cropWidth, MIN_CROP_SIZE, draft.naturalWidth);
    cropHeight = clamp(cropHeight, MIN_CROP_SIZE, draft.naturalHeight);

    const maxX = Math.max(0, draft.naturalWidth - cropWidth);
    const maxY = Math.max(0, draft.naturalHeight - cropHeight);
    const cropX = clamp(Math.round(patch.cropX ?? draft.cropX), 0, maxX);
    const cropY = clamp(Math.round(patch.cropY ?? draft.cropY), 0, maxY);

    return {
        ...draft,
        cropX,
        cropY,
        cropWidth,
        cropHeight,
    };
}

export function applyCropPreset(draft: FaceCropDraft, preset: CropPreset): FaceCropDraft {
    if (preset === 'reset') {
        return {
            ...draft,
            ...getCenteredCrop(draft.naturalWidth, draft.naturalHeight),
        };
    }

    const maxWidth = draft.naturalWidth;
    const maxHeight = draft.naturalHeight;
    let cropWidth = maxWidth;
    let cropHeight = maxHeight;

    if (preset === 'square') {
        const size = Math.max(MIN_CROP_SIZE, Math.round(Math.min(maxWidth, maxHeight) * 0.82));
        cropWidth = size;
        cropHeight = size;
    }

    if (preset === 'portrait') {
        const height = Math.max(MIN_CROP_SIZE, Math.round(maxHeight * 0.88));
        cropHeight = height;
        cropWidth = Math.max(MIN_CROP_SIZE, Math.min(maxWidth, Math.round((height * 3) / 4)));
    }

    if (preset === 'landscape') {
        const width = Math.max(MIN_CROP_SIZE, Math.round(maxWidth * 0.9));
        cropWidth = width;
        cropHeight = Math.max(MIN_CROP_SIZE, Math.min(maxHeight, Math.round((width * 3) / 4)));
    }

    return updateFaceCropDraft(draft, {
        cropWidth,
        cropHeight,
        cropX: Math.round((maxWidth - cropWidth) / 2),
        cropY: Math.round((maxHeight - cropHeight) / 2),
    });
}

function getOutputFileName(fileName: string) {
    const dotIndex = fileName.lastIndexOf('.');
    if (dotIndex === -1) {
        return `${fileName}-cropped.png`;
    }

    const name = fileName.slice(0, dotIndex);
    const ext = fileName.slice(dotIndex);
    return `${name}-cropped${ext}`;
}

async function loadImage(url: string): Promise<HTMLImageElement> {
    const image = new Image();
    return new Promise((resolve, reject) => {
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error('Failed to render cropped preview'));
        image.src = url;
    });
}

export async function renderCroppedFaceFile(draft: FaceCropDraft): Promise<File> {
    const image = await loadImage(draft.previewUrl);
    const canvas = document.createElement('canvas');
    canvas.width = draft.cropWidth;
    canvas.height = draft.cropHeight;

    const context = canvas.getContext('2d');
    if (!context) {
        throw new Error('Canvas rendering is not available in this browser');
    }

    context.drawImage(
        image,
        draft.cropX,
        draft.cropY,
        draft.cropWidth,
        draft.cropHeight,
        0,
        0,
        draft.cropWidth,
        draft.cropHeight
    );

    const outputType = draft.sourceFile.type || 'image/png';
    const blob = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob(
            (value) => {
                if (!value) {
                    reject(new Error(`Failed to crop ${draft.sourceFile.name}`));
                    return;
                }
                resolve(value);
            },
            outputType,
            0.95
        );
    });

    return new File([blob], getOutputFileName(draft.sourceFile.name), {
        type: blob.type || outputType,
    });
}
