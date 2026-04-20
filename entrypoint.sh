#!/bin/sh
set -e

# Generate processed data if not present
if [ ! -f "data/processed/train_clean.csv" ]; then
    echo "Processed data not found — running ingest pipeline..."
    python -c "
from tools.ingest_tools import load_dataset, clean_data, generate_rul_labels
import yaml, pathlib

cfg = yaml.safe_load(open('config.yaml'))
df = load_dataset('train')
df = clean_data(df)
df = generate_rul_labels(df)
out = pathlib.Path(cfg['data']['processed_dir'])
out.mkdir(parents=True, exist_ok=True)
df.to_csv(out / 'train_clean.csv', index=False)
print(f'Saved {len(df)} rows to {out / \"train_clean.csv\"}')
"
fi

# Train model if weights not present
if [ ! -f "models/saved/cnn_lstm_fd001.pt" ]; then
    echo "Model weights not found — training CNN-LSTM (this takes a few minutes)..."
    python models/train.py
fi

exec "$@"
