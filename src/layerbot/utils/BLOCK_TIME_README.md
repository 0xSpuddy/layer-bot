# Block Time Data Management

This document explains how the block time data is managed in the Layer Bot application.

## Overview

The block time tracking system records block height and time information in a CSV file (`block_time.csv`). This data is used to calculate average block times over different periods, which is useful for estimating when future blocks will be reached.

The system now includes robust data management features to preserve historical data while keeping the file size manageable.

## Key Features

1. **Data Preservation**: The system now preserves historical data by:
   - Creating automatic backups before any potentially destructive operations
   - Using a rolling window approach to keep the CSV file at a manageable size
   - Only removing data older than the configured retention period

2. **Backup and Restore**: You can now:
   - Create manual backups of the block time data
   - List all available backups
   - Restore data from any backup

3. **Data Cleaning**: The system intelligently cleans old data:
   - Only removes records older than `MAX_AGE_DAYS` (default: 7 days)
   - Always keeps a minimum number of records (even if all are older than the cutoff)
   - Creates automatic backups before cleaning

4. **Duplicate Detection**: The system can detect and remove duplicate records:
   - Identifies records with the same block height
   - Keeps the most recent record for each block height
   - Creates backups before deduplication

## Command-Line Interface

### Using the Direct Block Time Utility

```bash
# Run the block time tracker
python -m layerbot.utils.block_time run --interval 60

# Create a backup
python -m layerbot.utils.block_time backup --reason "pre-deployment"

# List available backups
python -m layerbot.utils.block_time list-backups

# Restore from a backup
python -m layerbot.utils.block_time restore --file block_time.csv.20250421_123456.pre-deployment.bak

# Clean old records
python -m layerbot.utils.block_time clean

# Show statistics
python -m layerbot.utils.block_time stats
```

### Using the Layer Bot CLI

```bash
# Create a backup
layerbot block-data-manage create-backup --reason "pre-deployment"

# List available backups
layerbot block-data-manage list-backups

# Restore from a backup
layerbot block-data-manage restore-backup --file block_time.csv.20250421_123456.pre-deployment.bak

# Clean old records
layerbot block-data-manage clean-old-records

# Show statistics
layerbot block-data-manage show-stats
```

## Configuration

The main configuration parameters are defined at the top of the `block_time.py` file:

- `CSV_FILE`: The name of the CSV file (default: `block_time.csv`)
- `CHECK_INTERVAL`: The default interval between checks in seconds (default: 60)
- `MAX_AGE_DAYS`: The maximum age of records to keep (default: 7)

## How Data Cleaning Works

The system now uses a smarter approach to clean old data:

1. Before cleaning, it creates a backup of the current CSV file
2. It reads the file into a pandas DataFrame
3. It calculates a cutoff date based on `MAX_AGE_DAYS`
4. It checks if any records are older than the cutoff date
5. If so, it filters the DataFrame to keep only newer records
6. If all records would be removed, it keeps at least `MAX_RECORDS_TO_KEEP` records
7. It writes the filtered data back to the CSV file

This approach ensures that historical data is never permanently lost while keeping the active file size manageable.

## Backup and Restore

Backups are automatically created before any potentially destructive operation:
- Before cleaning old records
- Before removing duplicates

Manual backups can be created at any time using the CLI commands.

Each backup filename includes:
- A timestamp in `YYYYMMDD_HHMMSS` format
- A reason for the backup (e.g., "before_cleaning", "manual")
- The `.bak` extension

The restore functionality can use the most recent backup or a specific backup file. 