"""
Interactive script to configure your Intercom API access.
This will help you set up your .env file with the correct API token.
"""

import os
import sys
from pathlib import Path

def get_intercom_token():
    """Get Intercom access token from user."""
    print("🔑 Intercom API Token Setup")
    print("=" * 50)
    print()
    print("To get your Intercom access token:")
    print("1. Log into your Intercom workspace")
    print("2. Go to Settings → Integrations → Developer Hub")
    print("3. Create a new app or use an existing one")
    print("4. Copy the Access Token")
    print()
    
    while True:
        token = input("Enter your Intercom access token: ").strip()
        
        if not token:
            print("❌ Token cannot be empty. Please try again.")
            continue
            
        if token == "your_token_here":
            print("❌ Please replace 'your_token_here' with your actual token.")
            continue
            
        if len(token) < 20:
            print("❌ Token seems too short. Intercom tokens are usually longer.")
            retry = input("Continue anyway? (y/n): ").lower()
            if retry != 'y':
                continue
                
        return token

def create_env_file(token):
    """Create .env file with the provided token."""
    env_content = f"""# Intercom API Configuration
INTERCOM_ACCESS_TOKEN={token}
"""
    
    env_file = Path(".env")
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"✅ Created .env file with your token")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def test_connection(token):
    """Test the connection to Intercom API."""
    print("\n🧪 Testing connection to Intercom API...")
    
    try:
        # Add src to path
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        
        from intercom_client import IntercomClient
        
        client = IntercomClient(access_token=token)
        print("✅ Connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPossible issues:")
        print("1. Invalid access token")
        print("2. Token doesn't have conversation read permissions")
        print("3. Network connectivity issues")
        return False

def main():
    """Main configuration function."""
    print("🚀 Intercom Analysis Tool - API Configuration")
    print("=" * 60)
    print()
    
    # Check if .env already exists
    env_file = Path(".env")
    if env_file.exists():
        print("⚠️  .env file already exists.")
        overwrite = input("Do you want to reconfigure it? (y/n): ").lower()
        if overwrite != 'y':
            print("Configuration cancelled.")
            return
    
    # Get token from user
    token = get_intercom_token()
    
    # Create .env file
    if not create_env_file(token):
        return
    
    # Test connection
    if test_connection(token):
        print("\n🎉 Configuration complete!")
        print("\nNext steps:")
        print("1. Run: python test_setup.py  (to validate everything)")
        print("2. Run: python main.py --days 7 --max-pages 2  (for testing)")
        print("3. Run: python main.py  (for full analysis)")
    else:
        print("\n❌ Configuration failed. Please check your token and try again.")
        print("You can run this script again: python configure_api.py")

if __name__ == "__main__":
    main()


