#!/usr/bin/env python3
"""
Database Status Checker

Check if the database has been populated with mock data.
"""

import os
import sys
import pathlib

# Add the project root to the Python path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from web.backend.repositories.db import is_data_populated, query


def main():
    print("🔍 Checking database status...\n")
    
    try:
        # Check if data is populated
        populated = is_data_populated()
        
        if populated:
            print("✅ Database has been populated with mock data!")
            
            # Get statistics
            try:
                org_count = query("SELECT COUNT(*) as count FROM organization", fetchone=True)['count']
                user_count = query("SELECT COUNT(*) as count FROM ctgov_user", fetchone=True)['count']
                trial_count = query("SELECT COUNT(*) as count FROM trial", fetchone=True)['count']
                
                print(f"\n📊 Database Statistics:")
                print(f"   • Organizations: {org_count:,}")
                print(f"   • Users: {user_count:,}")
                print(f"   • Trials: {trial_count:,}")
                
                # Check population timestamp
                pop_info = query("SELECT populated_at, version FROM data_population_flag ORDER BY populated_at DESC LIMIT 1", fetchone=True)
                if pop_info:
                    print(f"   • Populated at: {pop_info['populated_at']}")
                    print(f"   • Data version: {pop_info['version']}")
                
            except Exception as e:
                print(f"⚠️  Could not get detailed statistics: {e}")
                
        else:
            print("❌ Database has not been populated with mock data yet.")
            print("\n💡 To populate the database:")
            print("   • For local development: python scripts/init_mock_data.py")
            print("   • For cloud database: Run the 'Initialize Cloud Database' GitHub Action")
        
        print(f"\n🔗 Database connection:")
        print(f"   • Host: {os.environ.get('DB_HOST', 'localhost')}")
        print(f"   • Port: {os.environ.get('DB_PORT', '5464')}")
        print(f"   • Database: {os.environ.get('DB_NAME', 'ctgov-web')}")
        print(f"   • User: {os.environ.get('DB_USER', 'postgres')}")
        
    except Exception as e:
        print(f"❌ Error checking database status: {e}")
        print("\n💡 Make sure:")
        print("   • Database is running and accessible")
        print("   • Environment variables are set correctly")
        print("   • Database schema has been migrated")
        sys.exit(1)


if __name__ == "__main__":
    main() 