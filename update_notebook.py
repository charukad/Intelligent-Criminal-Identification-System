import json

with open("notebooks/TraceNet_Training.ipynb", "r") as f:
    nb = json.load(f)

seed_cell = {
  "cell_type": "code",
  "execution_count": None,
  "metadata": {},
  "outputs": [],
  "source": [
    "# Set seeds for reproducibility\n",
    "import torch\n",
    "import numpy as np\n",
    "import random\n",
    "\n",
    "def set_seed(seed=42):\n",
    "    random.seed(seed)\n",
    "    np.random.seed(seed)\n",
    "    torch.manual_seed(seed)\n",
    "    torch.cuda.manual_seed_all(seed)\n",
    "    torch.backends.cudnn.deterministic = True\n",
    "    torch.backends.cudnn.benchmark = False\n",
    "    print(f\"🌱 Seed planted: {seed}\")\n",
    "\n",
    "set_seed(42)\n"
  ]
}

# Insert it right after the environment setup (cell 4 or 5)
nb["cells"].insert(5, seed_cell)

with open("notebooks/TraceNet_Training.ipynb", "w") as f:
    json.dump(nb, f, indent=2)

print("Seed cell injected into notebook.")
