#!/usr/bin/env python3
"""
Daily Props Fetcher - Run this script once per day at midnight
Cleans up old props and fetches fresh props for today and tomorrow
"""

import sys
import os
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db, Prop
import subprocess

def cleanup_old_props():
    """Remove props older than yesterday to keep database clean"""
    yesterday = date.today() - timedelta(days=1)
    
    with app.app_context():
        old_props = Prop.query.filter(Prop.date < yesterday).all()
        old_count = len(old_props)
        
        if old_count > 0:
            print(f"Removing {old_count} old props (before {yesterday})")
            for prop in old_props:
                db.session.delete(prop)
            db.session.commit()
            print(f"✓ Cleaned up {old_count} old props")
        else:
            print("No old props to clean up")

def fetch_fresh_props():
    """Fetch new props for today and tomorrow"""
    print("Fetching fresh props...")
    
    # Run the fetch_props.py script
    script_path = os.path.join(os.path.dirname(__file__), 'fetch_props.py')
    result = subprocess.run([sys.executable, script_path], 
                          capture_output=True, text=True, cwd=os.path.dirname(script_path))
    
    print("Fetch output:")
    print(result.stdout)
    
    if result.stderr:
        print("Fetch errors:")
        print(result.stderr)
    
    return result.returncode == 0

def main():
    """Main daily fetch routine"""
    print(f"=== Daily Props Fetch - {date.today()} ===")
    
    # Step 1: Clean up old props
    cleanup_old_props()
    
    # Step 2: Fetch fresh props
    success = fetch_fresh_props()
    
    if success:
        print("✓ Daily fetch completed successfully")
    else:
        print("✗ Daily fetch encountered errors")
        return 1
    
    return 0

if __name__ == "__main__":
    app = create_app()
    sys.exit(main()) 