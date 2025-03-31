import os
import subprocess
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Get the RPC URL (though not needed for keys list, we'll need it for other commands)
    rpc_url = os.getenv('LAYER_RPC_URL')
    
    try:
        # Execute the layerd keys list command
        result = subprocess.run(
            ['./layerd', 'keys', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Print the output
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"Error output: {e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main() 