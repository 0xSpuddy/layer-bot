from flask import Flask, make_response, render_template, request, jsonify, send_from_directory
import pandas as pd
from pandas.errors import EmptyDataError, ParserError
from datetime import datetime
from layerbot.utils.scan_time import get_last_scan_time
import os
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Get mount path from environment variable, default to empty string for root mount
MOUNT_PATH = os.environ.get('MOUNT_PATH', '').rstrip('/')

# Map known bridge contract addresses to human-readable version labels.
# Keys are lowercased for case-insensitive matching.
def _build_contract_versions():
    mapping = {}
    for env_var, label in [
        ('BRIDGE_CONTRACT_ADDRESS_0', 'V0'),
        ('BRIDGE_CONTRACT_ADDRESS_1', 'V1'),
        ('BRIDGE_CONTRACT_ADDRESS_CURRENT', 'V1'),
        ('BRIDGE_CONTRACT_V2_ADDRESS', 'V2'),
    ]:
        addr = os.environ.get(env_var, '')
        if addr:
            mapping[addr.lower()] = label
    return mapping

CONTRACT_VERSIONS = _build_contract_versions()

# Ensure mount path starts with / if it's not empty
if MOUNT_PATH and not MOUNT_PATH.startswith('/'):
    MOUNT_PATH = '/' + MOUNT_PATH


class CsvDataUnavailable(Exception):
    """Raised when a runtime CSV cannot be read safely."""

    def __init__(self, dataset, path, detail):
        self.dataset = dataset
        self.path = path
        self.detail = detail
        super().__init__(f"{dataset} data unavailable at {path}: {detail}")


def get_deposits_csv_path():
    return os.getenv('BRIDGE_DEPOSITS_CSV', 'bridge_deposits.csv')


def get_withdrawals_csv_path():
    return os.getenv('BRIDGE_WITHDRAWALS_CSV', 'bridge_withdrawals.csv')


def read_csv_or_unavailable(dataset, path):
    try:
        return pd.read_csv(path)
    except FileNotFoundError as e:
        raise CsvDataUnavailable(dataset, path, 'file not found') from e
    except EmptyDataError as e:
        raise CsvDataUnavailable(dataset, path, 'file is empty') from e
    except ParserError as e:
        raise CsvDataUnavailable(dataset, path, 'file could not be parsed') from e
    except OSError as e:
        raise CsvDataUnavailable(dataset, path, str(e)) from e


def format_time_ago(timestamp):
    if pd.isna(timestamp):
        return 'N/A'

    try:
        now = datetime.now()
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize('UTC')
        now = now.replace(tzinfo=timestamp.tz)

        diff = now - timestamp
        total_seconds = int(diff.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s ago"
        if total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m ago"
        if total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h ago"

        days = total_seconds // 86400
        return f"{days}d ago"
    except Exception as e:
        print(f"Error calculating age for timestamp {timestamp}: {e}")
        return 'N/A'


def calculate_hours_since(timestamp):
    if pd.isna(timestamp):
        return None

    try:
        now = datetime.now()
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize('UTC')
        now = now.replace(tzinfo=timestamp.tz)
        diff = now - timestamp
        return diff.total_seconds() / 3600
    except Exception as e:
        print(f"Error calculating hours since timestamp {timestamp}: {e}")
        return None


def json_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, 'item'):
        try:
            return value.item()
        except Exception:
            pass
    return value


def records_for_api(df):
    return [
        {key: json_safe(value) for key, value in row.items()}
        for row in df.to_dict('records')
    ]


def parse_limit(default=1000):
    raw_limit = request.args.get('limit')
    if raw_limit is None:
        return default

    try:
        limit = int(raw_limit)
    except ValueError:
        return default

    return max(0, min(limit, 10000))


def bool_arg(name):
    raw_value = request.args.get(name)
    if raw_value is None:
        return None
    return raw_value.strip().lower() in ('true', '1', 'yes')


def add_no_store(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


def api_error(error, status_code=503):
    response = jsonify({
        'error': {
            'code': 'csv_data_unavailable',
            'dataset': error.dataset,
            'path': error.path,
            'detail': error.detail,
        }
    })
    return add_no_store(response), status_code

def prepare_chart_data(deposits_df):
    """Prepare deposits data for the chart visualization."""
    try:
        # Create a copy to avoid modifying the original
        df = deposits_df.copy()
        
        # Sort by timestamp for proper chronological order
        df = df.sort_values('Timestamp')
        
        # Prepare individual deposit data (scatter points)
        individual_deposits = []
        cumulative_total = 0
        cumulative_data = []
        
        for _, row in df.iterrows():
            try:
                # Skip rows with invalid data
                if pd.isna(row['Timestamp']) or pd.isna(row['Amount']):
                    continue
                    
                # Individual deposit data
                individual_deposits.append({
                    'x': row['Timestamp'].isoformat(),
                    'y': float(row['Amount']),
                    'deposit_id': int(row['Deposit ID']),
                    'formatted_date': row['Formatted_Timestamp']
                })
                
                # Cumulative total data
                cumulative_total += float(row['Amount'])
                cumulative_data.append({
                    'x': row['Timestamp'].isoformat(),
                    'y': cumulative_total,
                    'count': len(cumulative_data) + 1,
                    'formatted_date': row['Formatted_Timestamp']
                })
            except Exception as e:
                print(f"Error processing row {row.get('Deposit ID', 'unknown')}: {e}")
                continue
        
        return {
            'individual_deposits': individual_deposits,
            'cumulative_deposits': cumulative_data
        }
    
    except Exception as e:
        print(f"Error preparing chart data: {e}")
        return {
            'individual_deposits': [],
            'cumulative_deposits': []
        }

def prepare_withdrawals_chart_data(withdrawals_df):
    """Prepare withdrawals data for the chart visualization."""
    try:
        # Create a copy to avoid modifying the original
        df = withdrawals_df.copy()
        
        # Sort by timestamp for proper chronological order
        df = df.sort_values('Timestamp')
        
        # Prepare individual withdrawal data (scatter points)
        individual_withdrawals = []
        cumulative_total = 0
        cumulative_data = []
        
        for _, row in df.iterrows():
            try:
                # Skip rows with invalid data
                if pd.isna(row['Timestamp']) or pd.isna(row['Amount_TRB']):
                    continue
                    
                # Individual withdrawal data
                individual_withdrawals.append({
                    'x': row['Timestamp'].isoformat(),
                    'y': float(row['Amount_TRB']),
                    'withdraw_id': int(row['withdraw_id']),
                    'formatted_date': row['Formatted_Timestamp']
                })
                
                # Cumulative total data
                cumulative_total += float(row['Amount_TRB'])
                cumulative_data.append({
                    'x': row['Timestamp'].isoformat(),
                    'y': cumulative_total,
                    'count': len(cumulative_data) + 1,
                    'formatted_date': row['Formatted_Timestamp']
                })
            except Exception as e:
                print(f"Error processing withdrawal row {row.get('withdraw_id', 'unknown')}: {e}")
                continue
        
        return {
            'individual_withdrawals': individual_withdrawals,
            'cumulative_withdrawals': cumulative_data
        }
    
    except Exception as e:
        print(f"Error preparing withdrawals chart data: {e}")
        return {
            'individual_withdrawals': [],
            'cumulative_withdrawals': []
        }


def load_deposits_data():
    deposits_df = read_csv_or_unavailable('deposits', get_deposits_csv_path())

    most_recent_scan = get_last_scan_time()
    if not most_recent_scan:
        most_recent_scan = "No scan time available"

    # Convert timestamp columns to more readable format with error handling (for all data)
    try:
        deposits_df['Timestamp'] = pd.to_datetime(deposits_df['Timestamp'], errors='coerce')
        # Remove rows with invalid timestamps
        deposits_df = deposits_df.dropna(subset=['Timestamp'])
        deposits_df['Formatted_Timestamp'] = deposits_df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        deposits_df['Age'] = deposits_df['Timestamp'].apply(format_time_ago)

    except Exception as e:
        print(f"Error processing timestamps: {e}")
        # Fallback: create dummy timestamps if all fail
        deposits_df['Timestamp'] = pd.to_datetime('1970-01-01')
        deposits_df['Formatted_Timestamp'] = '1970-01-01 00:00:00 UTC'
        deposits_df['Age'] = 'N/A'
    
    # Compute a human-readable contract version label (V0 / V1 / V2) from the address
    if 'Bridge Contract Address' in deposits_df.columns:
        deposits_df['Contract_Version'] = (
            deposits_df['Bridge Contract Address']
            .fillna('')
            .str.lower()
            .map(CONTRACT_VERSIONS)
            .fillna('Unknown')
        )
    else:
        deposits_df['Contract_Version'] = 'Unknown'

    # Keep original data for chart (after timestamp processing, before filtering)
    chart_deposits_df = deposits_df.copy()

    # Filter out deposit IDs 27 and 32 for table display only
    deposits_df = deposits_df[~deposits_df['Deposit ID'].isin([27, 32])].copy()

    # Preserve the source units while exposing the dashboard's TRB-normalized amount.
    deposits_df['Amount_Raw'] = deposits_df['Amount']
    chart_deposits_df['Amount_Raw'] = chart_deposits_df['Amount']
    deposits_df['Amount'] = pd.to_numeric(deposits_df['Amount'], errors='coerce') / 1e18
    chart_deposits_df['Amount'] = pd.to_numeric(chart_deposits_df['Amount'], errors='coerce') / 1e18

    # Calculate which rows need highlighting
    current_time = datetime.now().timestamp()
    twelve_hours = 12 * 60 * 60  # 12 hours in seconds
    fourteen_hours = 14 * 60 * 60  # 14 hours in seconds
    
    # Convert deposit timestamp for comparison
    deposit_timestamps = deposits_df['Timestamp'].apply(lambda x: x.timestamp() if pd.notna(x) else None)
    
    # Calculate status based on time and claimed status
    def calculate_status(row):
        # Check if already claimed/completed (handle both old 'Claimed' and new 'Status' columns)
        if pd.notna(row.get('Status')) and str(row['Status']).lower() == 'completed':
            return 'completed'
        elif pd.notna(row.get('Claimed')) and str(row['Claimed']).lower() == 'yes':
            return 'completed'
        
        # Calculate time since deposit for unclaimed deposits
        if pd.notna(row['Timestamp']):
            deposit_time = row['Timestamp'].timestamp()
            time_elapsed = current_time - deposit_time
            
            if time_elapsed < fourteen_hours:
                return 'in progress'
            else:
                return 'past due'
        else:
            return 'past due'  # Default for invalid timestamps

    deposits_df['Status'] = deposits_df.apply(calculate_status, axis=1)

    # Ready to claim status (green) - based on deposit timestamp
    deposits_df['ready_to_claim'] = (
        (deposits_df['Status'].str.lower() != 'completed') &
        (deposit_timestamps.notna()) &
        ((current_time - deposit_timestamps) > twelve_hours)
    )

    # Recent scan status (pale green)
    if isinstance(most_recent_scan, str) and most_recent_scan != "No scan time available":
        most_recent_scan_time = pd.to_datetime(most_recent_scan).timestamp()
        deposits_df['recent_scan'] = (
            (deposit_timestamps.notna()) &
            ((most_recent_scan_time - deposit_timestamps) <= twelve_hours) &
            (deposits_df['Status'].str.lower() != 'completed')  # Exclude completed deposits
        )
    else:
        deposits_df['recent_scan'] = False
    
    # Invalid recipient status (red)
    deposits_df['invalid_recipient'] = ~deposits_df['Recipient'].fillna('').str.startswith('tellor1')
    
    # Sort the deposits dataframe - highest deposit ID first
    deposits_df['Status'] = deposits_df['Status'].fillna('past due')
    deposits_df = deposits_df.sort_values(
        by=['Deposit ID'],
        ascending=[False]
    )

    chart_data = prepare_chart_data(chart_deposits_df)

    return {
        'deposits_df': deposits_df,
        'chart_deposits_df': chart_deposits_df,
        'chart_data': chart_data,
        'most_recent_scan': most_recent_scan,
    }


def load_withdrawals_data():
    withdrawals_df = read_csv_or_unavailable('withdrawals', get_withdrawals_csv_path())

    # Handle timestamp column if it exists
    if 'Timestamp' in withdrawals_df.columns:
        try:
            withdrawals_df['Timestamp'] = pd.to_datetime(withdrawals_df['Timestamp'], errors='coerce')
            valid_timestamp_mask = withdrawals_df['Timestamp'].notna()

            withdrawals_df.loc[valid_timestamp_mask, 'Formatted_Timestamp'] = withdrawals_df.loc[valid_timestamp_mask, 'Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            withdrawals_df.loc[~valid_timestamp_mask, 'Formatted_Timestamp'] = 'N/A'
            withdrawals_df['Age'] = withdrawals_df['Timestamp'].apply(format_time_ago)
            withdrawals_df['hours_since_withdrawal'] = withdrawals_df['Timestamp'].apply(calculate_hours_since)

        except Exception as e:
            print(f"Error processing withdrawal timestamps: {e}")
            withdrawals_df['Formatted_Timestamp'] = 'N/A'
            withdrawals_df['Age'] = 'N/A'
            withdrawals_df['hours_since_withdrawal'] = None
    else:
        # If no Timestamp column exists, create a placeholder
        withdrawals_df['Formatted_Timestamp'] = 'N/A'
        withdrawals_df['Age'] = 'N/A'
        withdrawals_df['hours_since_withdrawal'] = None

    # Handle withdraw_id column
    if withdrawals_df['withdraw_id'].dtype == 'object':
        # If it's a string, clean it up
        withdrawals_df['withdraw_id'] = withdrawals_df['withdraw_id'].str.replace('"', '')
    withdrawals_df['withdraw_id'] = pd.to_numeric(withdrawals_df['withdraw_id'])

    # Convert boolean columns to proper format
    # 'success' may be blank for stub rows — treat blank as False
    withdrawals_df['success'] = (
        withdrawals_df['success']
        .fillna('')
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(['true', '1', 'yes'])
    )

    # 'Claimed' can be True/False or blank ('') for stub rows where we haven't
    # yet confirmed status. Blank rows will show as "Unknown" in the UI.
    if 'Claimed' not in withdrawals_df.columns:
        withdrawals_df['Claimed'] = False
    else:
        withdrawals_df['Claimed'] = (
            withdrawals_df['Claimed']
            .fillna('')
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(['true', '1', 'yes'])
        )

    # Rows with no transaction data (no creator AND no amount) are stub rows
    # that represent withdrawal IDs we know exist on-chain but have no details for.
    has_creator = withdrawals_df['creator'].fillna('').astype(str).str.strip().ne('')
    has_amount = withdrawals_df['Amount'].fillna('').astype(str).str.strip().ne('')
    withdrawals_df['has_tx_data'] = has_creator | has_amount

    if 'Amount' in withdrawals_df.columns:
        withdrawals_df['Amount_Raw'] = withdrawals_df['Amount']
        withdrawals_df['Amount'] = pd.to_numeric(withdrawals_df['Amount'], errors='coerce')
        withdrawals_df['Amount_TRB'] = withdrawals_df['Amount'] / 1e6  # Convert loya to TRB
    else:
        withdrawals_df['Amount_Raw'] = None
        withdrawals_df['Amount_TRB'] = 0

    withdrawals_df = withdrawals_df.sort_values('withdraw_id', ascending=False)
    withdrawals_chart_data = prepare_withdrawals_chart_data(withdrawals_df)

    return {
        'withdrawals_df': withdrawals_df,
        'withdrawals_chart_data': withdrawals_chart_data,
    }


def build_summary(deposits_data, withdrawals_data):
    deposits_df = deposits_data['deposits_df']
    withdrawals_df = withdrawals_data['withdrawals_df']

    completed_deposits = deposits_df['Status'].astype(str).str.lower().eq('completed')
    past_due_deposits = deposits_df['Status'].astype(str).str.lower().eq('past due')
    claimed_withdrawals = withdrawals_df['Claimed'].fillna(False).astype(bool)

    return {
        'last_scan': deposits_data['most_recent_scan'],
        'deposits': {
            'count': int(len(deposits_df)),
            'completed_count': int(completed_deposits.sum()),
            'past_due_count': int(past_due_deposits.sum()),
            'ready_to_claim_count': int(deposits_df['ready_to_claim'].fillna(False).sum()),
            'total_amount_trb': json_safe(deposits_df['Amount'].sum()),
        },
        'withdrawals': {
            'count': int(len(withdrawals_df)),
            'claimed_count': int(claimed_withdrawals.sum()),
            'with_tx_data_count': int(withdrawals_df['has_tx_data'].fillna(False).sum()),
            'total_amount_trb': json_safe(withdrawals_df['Amount_TRB'].sum()),
        },
        'files': {
            'deposits_csv': get_deposits_csv_path(),
            'withdrawals_csv': get_withdrawals_csv_path(),
        }
    }


def show_deposits():
    try:
        deposits_data = load_deposits_data()
    except CsvDataUnavailable as e:
        return make_response(f"Deposits data unavailable: {e.detail}", 503)

    try:
        withdrawals_data = load_withdrawals_data()
        withdrawals = withdrawals_data['withdrawals_df'].to_dict('records')
        withdrawals_chart_data = withdrawals_data['withdrawals_chart_data']
    except Exception as e:
        print(f"Error reading withdrawals CSV: {e}")
        withdrawals = []
        withdrawals_chart_data = prepare_withdrawals_chart_data(pd.DataFrame(withdrawals))

    deposits = deposits_data['deposits_df'].to_dict('records')

    return render_template('deposits.html',
                          deposits=deposits,
                          withdrawals=withdrawals,
                          most_recent_scan=deposits_data['most_recent_scan'],
                          chart_data=deposits_data['chart_data'],
                          withdrawals_chart_data=withdrawals_chart_data,
                          mount_path=MOUNT_PATH)


@app.route('/')
def show_deposits_root():
    return show_deposits()

# Routes for both mount path and root to work with reverse proxy
if MOUNT_PATH:
    @app.route(f'{MOUNT_PATH}/')
    def show_deposits_mounted():
        return show_deposits()


def deposits_api():
    try:
        deposits_data = load_deposits_data()
    except CsvDataUnavailable as e:
        return api_error(e)

    deposits_df = deposits_data['deposits_df']

    status = request.args.get('status')
    if status:
        deposits_df = deposits_df[
            deposits_df['Status'].astype(str).str.lower() == status.strip().lower()
        ]

    contract_version = request.args.get('contract_version')
    if contract_version:
        deposits_df = deposits_df[
            deposits_df['Contract_Version'].astype(str).str.lower() == contract_version.strip().lower()
        ]

    limit = parse_limit()
    if limit:
        deposits_df = deposits_df.head(limit)
    else:
        deposits_df = deposits_df.head(0)

    response = jsonify({
        'data': records_for_api(deposits_df),
        'count': int(len(deposits_df)),
        'last_scan': deposits_data['most_recent_scan'],
    })
    return add_no_store(response)


def withdrawals_api():
    try:
        withdrawals_data = load_withdrawals_data()
    except CsvDataUnavailable as e:
        return api_error(e)

    withdrawals_df = withdrawals_data['withdrawals_df']

    claimed = bool_arg('claimed')
    if claimed is not None:
        withdrawals_df = withdrawals_df[
            withdrawals_df['Claimed'].fillna(False).astype(bool) == claimed
        ]

    limit = parse_limit()
    if limit:
        withdrawals_df = withdrawals_df.head(limit)
    else:
        withdrawals_df = withdrawals_df.head(0)

    response = jsonify({
        'data': records_for_api(withdrawals_df),
        'count': int(len(withdrawals_df)),
    })
    return add_no_store(response)


def summary_api():
    try:
        deposits_data = load_deposits_data()
        withdrawals_data = load_withdrawals_data()
    except CsvDataUnavailable as e:
        return api_error(e)

    response = jsonify(build_summary(deposits_data, withdrawals_data))
    return add_no_store(response)


def health_api():
    deposits_path = get_deposits_csv_path()
    withdrawals_path = get_withdrawals_csv_path()
    files = {
        'deposits_csv': {
            'path': deposits_path,
            'exists': os.path.exists(deposits_path),
        },
        'withdrawals_csv': {
            'path': withdrawals_path,
            'exists': os.path.exists(withdrawals_path),
        },
    }

    response = jsonify({
        'status': 'ok',
        'mount_path': MOUNT_PATH,
        'files': files,
    })
    return add_no_store(response)


app.add_url_rule('/api/v1/deposits', 'api_v1_deposits', deposits_api)
app.add_url_rule('/api/v1/withdrawals', 'api_v1_withdrawals', withdrawals_api)
app.add_url_rule('/api/v1/summary', 'api_v1_summary', summary_api)
app.add_url_rule('/api/v1/health', 'api_v1_health', health_api)
app.add_url_rule('/health', 'health', health_api)

if MOUNT_PATH:
    app.add_url_rule(f'{MOUNT_PATH}/api/v1/deposits', 'mounted_api_v1_deposits', deposits_api)
    app.add_url_rule(f'{MOUNT_PATH}/api/v1/withdrawals', 'mounted_api_v1_withdrawals', withdrawals_api)
    app.add_url_rule(f'{MOUNT_PATH}/api/v1/summary', 'mounted_api_v1_summary', summary_api)
    app.add_url_rule(f'{MOUNT_PATH}/api/v1/health', 'mounted_api_v1_health', health_api)
    app.add_url_rule(f'{MOUNT_PATH}/health', 'mounted_health', health_api)



# Add static file serving for mount path
if MOUNT_PATH:
    @app.route(f'{MOUNT_PATH}/static/<path:filename>')
    def mounted_static(filename):
        return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the Flask bridge monitoring app')
    parser.add_argument('--port', '-p', type=int, 
                       default=int(os.environ.get('FLASK_PORT', 5000)),
                       help='Port to run the Flask app on (default: 5000, can also be set via FLASK_PORT env var)')
    parser.add_argument('--host', type=str,
                       default=os.environ.get('FLASK_HOST', '127.0.0.1'),
                       help='Host to bind the Flask app to (default: 127.0.0.1, can also be set via FLASK_HOST env var)')
    parser.add_argument('--debug', action='store_true',
                       default=os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes'],
                       help='Run in debug mode (default: False, can also be set via FLASK_DEBUG env var)')
    
    args = parser.parse_args()
    
    print(f"Starting Flask app on {args.host}:{args.port}")
    print(f"Debug mode: {args.debug}")
    
    app.run(host=args.host, port=args.port, debug=args.debug) 