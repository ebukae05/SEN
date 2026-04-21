#!/bin/sh
set -e

# Generate processed data for all 4 datasets if not present
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

# Train models for all 4 datasets if weights not present
for DS in FD001 FD002 FD003 FD004; do
    WEIGHTS="models/saved/cnn_lstm_$(echo ${DS} | tr 'A-Z' 'a-z').pt"
    if [ ! -f "$WEIGHTS" ]; then
        echo "Model weights not found for ${DS} — training CNN-LSTM..."
        python models/train.py --dataset ${DS}
    fi
done

exec "$@"
