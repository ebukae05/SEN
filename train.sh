#!/bin/sh
# Prepare processed CSVs and CNN-LSTM weights for every dataset.
# Idempotent: skips any dataset whose outputs already exist on the mounted volumes.
# Intended to be run once as a separate "trainer" compose service before the API starts.
set -e

for DS in FD001 FD002 FD003 FD004; do
    if [ ! -f "data/processed/train_${DS}_clean.csv" ]; then
        echo "Processed data not found for ${DS} — running ingest pipeline..."
        python -c "
from tools.ingest_tools import load_dataset, clean_data, generate_rul_labels
import yaml, pathlib

dataset_id = '${DS}'
cfg = yaml.safe_load(open('config.yaml'))
df = load_dataset('train', dataset_id=dataset_id)
df = clean_data(df, dataset_id=dataset_id)
df = generate_rul_labels(df)
out = pathlib.Path(cfg['data']['processed_dir'])
out.mkdir(parents=True, exist_ok=True)
df.to_csv(out / f'train_{dataset_id}_clean.csv', index=False)
print(f'Saved {len(df)} rows for {dataset_id}')
"
    fi
done

for DS in FD001 FD002 FD003 FD004; do
    WEIGHTS="models/saved/cnn_lstm_$(echo ${DS} | tr 'A-Z' 'a-z').pt"
    if [ ! -f "$WEIGHTS" ]; then
        echo "Model weights not found for ${DS} — training CNN-LSTM..."
        python models/train.py --dataset ${DS}
    else
        echo "Weights already present for ${DS} — skipping."
    fi
done

echo "Trainer finished: all datasets ready."
