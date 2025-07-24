#!/usr/bin/env python
"""
Script to fix admin user role issue.
Run this script to assign SUPERADMIN role to the admin user.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User

def fix_admin_role():
    try:
        # Get the admin user
        admin_user = User.objects.get(username='admin')
        
        print(f"Current admin user role: '{admin_user.role}'")
        
        # Update the role to SUPERADMIN
        admin_user.role = User.Role.SUPERADMIN
        admin_user.save()
        
        print(f"✅ Successfully updated admin user role to: {admin_user.role}")
        
        # Verify the change
        admin_user.refresh_from_db()
        print(f"✅ Verified admin user role: {admin_user.role}")
        
    except User.DoesNotExist:
        print("❌ Admin user not found!")
        return False
    except Exception as e:
        print(f"❌ Error updating admin user: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Fixing admin user role...")
    success = fix_admin_role()
    if success:
        print("✅ Admin role fix completed successfully!")
    else:
        print("❌ Admin role fix failed!")
        sys.exit(1)