# Layer Bot

A Python-based tool for interacting with the Layer blockchain.

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Copy the example environment file:

```bash
cp .env.example .env
```

3. Edit the `.env` file with your RPC URL.

```bash
nano .env
```

4. Download and extract the latest [layer binary](https://github.com/tellor-io/layer/releases/tag/4.0.1). 
Be sure to choose the binary that matches your system and replace the link as needed:

```bash
wget https://github.com/tellor-io/layer/releases/download/v3.0.4/layer_Darwin_arm64.tar.gz && tar -xvzf layer_Darwin_arm64.tar.gz
```

## Usage

To generate csv files with Tellor testnet bridge information:

```bash
python bridge_info.py
```
