# Layer Bot

A Python-based tool for interacting with the Layer blockchain.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Copy the example environment file and configure it:
```bash
cp .env.example .env
```

3. Edit the `.env` file with your RPC URL.

## Usage

To list all keys:
```bash
python list_keys.py
```

## Requirements

- Python 3.7+
- The `layerd` binary in the project root directory
- python-dotenv package 