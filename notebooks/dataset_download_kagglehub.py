# Use this cell in Google Colab notebook to download LFW dataset

# Install kagglehub
!pip install -q kagglehub

import kagglehub
import os
import shutil

# Download LFW dataset from Kaggle
if not os.path.exists('/content/lfw'):
    print("Downloading LFW dataset from Kaggle...")
    path = kagglehub.dataset_download("jessicali9530/lfw-dataset")
    
    print(f"✅ Dataset downloaded to: {path}")
    
    # Check dataset structure
    print("\nDataset contents:")
    !ls -la {path}
    
    # Find and move LFW folder to expected location
    lfw_folders = [f for f in os.listdir(path) if 'lfw' in f.lower()]
    if lfw_folders:
        source = os.path.join(path, lfw_folders[0])
        shutil.move(source, '/content/lfw')
        print(f"✅ Moved dataset to /content/lfw")
    else:
        # If no lfw subfolder, the path itself might be lfw
        shutil.copytree(path, '/content/lfw')
        print(f"✅ Copied dataset to /content/lfw")
else:
    print("✅ LFW dataset already available!")
