# Development Environment Auto-Authentication

## Overview
This document tracks the implementation of automatic user authentication for development environments in the CTGov Compliance Web application.

## Objective
When `ENVIRONMENT=dev` or `ENVIRONMENT=preview`, automatically authenticate users as a default test user without requiring manual login, while preserving normal authentication flow for other environments.

## Default Test User Credentials
- **Username**: user1@example.com
- **Password**: password

## Implementation Log

### Phase 1: Environment-Based Auto-Login
- [x] Add environment detection in app initialization
- [x] Create auto-login middleware/before_request handler
- [x] Define default test user configuration

### Phase 2: Modify Authentication Flow
- [x] Update User class for dev mode support
- [x] Implement auto-authentication logic
- [x] Add User.get_by_email() method if needed

### Phase 3: Route Handling
- [x] Implement conditional route protection
- [x] Preserve manual auth routes functionality
- [x] Test auto-authentication flow

### Phase 4: Testing and Documentation
- [x] Test auto-authentication behavior
- [x] Test fallback to normal authentication
- [x] Verify production safety

## Changes Made

### Files Modified
- `web/__init__.py` - App initialization and environment detection
  - Added `ENVIRONMENT` config from environment variable
  - Added `before_request` handler for auto-authentication
  - Auto-authentication logic for dev environment only
  - Skips auth routes and already authenticated users
  - Graceful fallback on errors

- `web/auth.py` - User class and authentication logic
  - Added `User.get_by_email()` static method
  - Enables lookup of users by email address for auto-authentication

### Environment Variables
- `ENVIRONMENT=dev` - Enables auto-authentication mode for local development
- `ENVIRONMENT=preview` - Enables auto-authentication mode for preview deployments

## Testing Notes
- Auto-authentication only works when `ENVIRONMENT=dev` or `ENVIRONMENT=preview`
- Normal authentication preserved for all other environments (especially `prod`)
- Manual login/logout still functional in dev/preview modes
- Tested with custom test script - all functionality verified
- Routes that skip auto-authentication: login, register, logout, reset_request, reset_password, health

## Usage Instructions

### To Enable Auto-Authentication
Set the environment variable before starting the application:
```bash
# For local development
export ENVIRONMENT=dev
flask run --host 0.0.0.0 --port 6525

# For preview deployments (single PR testing)
export ENVIRONMENT=preview
flask run --host 0.0.0.0 --port 6525
```

### To Disable Auto-Authentication
Either unset the environment variable or set it to production:
```bash
export ENVIRONMENT=prod
# or
unset ENVIRONMENT
```

### Environment Flow
`preview` (single PR) → `dev` (main branch) → `prod` (tagged release)

### Default Test User
When auto-authentication is enabled, users will be automatically logged in as:
- **Email**: user1@example.com
- **Password**: password (not needed for auto-login)

Note: This user must exist in the database/mock data for auto-authentication to work. The user is automatically created by the `scripts/init_mock_data.py` script.

## Example Usage

```bash
# 1. Set up the database with mock data (if not already done)
python3 scripts/init_mock_data.py

# 2. Enable auto-authentication (choose environment)
export ENVIRONMENT=dev      # For local development
# OR
export ENVIRONMENT=preview  # For preview deployments

# 3. Start the application
flask run --host 0.0.0.0 --port 6525

# 4. Visit any protected route - you'll be automatically logged in as user1@example.com
# For example: http://localhost:6525/
```

The application will automatically log you in when you visit any protected route. You can still manually log out and log in as different users by visiting `/logout` and `/login`.

## Implementation Details

### Auto-Authentication Flow
1. Before each request, the `auto_authenticate_dev_user()` function is called
2. Checks if `ENVIRONMENT` is set to `dev` or `preview`
3. Skips auto-auth for auth-related routes and health check
4. Skips if user is already authenticated
5. Attempts to load `user1@example.com` from database
6. If user found, automatically logs them in using `login_user()`
7. Logs authentication events for debugging
8. Gracefully falls back to normal auth on any errors

### Code Changes Summary
- **User.get_by_email()**: New static method for email-based user lookup
- **before_request handler**: Auto-authentication middleware
- **Environment detection**: Reads `ENVIRONMENT` variable in app config
- **Error handling**: Graceful fallback if auto-auth fails

### Compatibility with Existing Systems
- **Mock Data Integration**: Works seamlessly with `scripts/init_mock_data.py`
- **No Database Changes**: Uses existing user table structure
- **Preserved Authentication**: All existing auth routes work normally
- **Non-Intrusive**: Only adds functionality, doesn't modify existing behavior

## Security Considerations
- Auto-authentication is development/testing-only (`dev` and `preview` environments)
- Production deployments should use `ENVIRONMENT=prod` or leave unset
- Real authentication system remains unchanged for production
- Auto-authentication has comprehensive error handling
- No sensitive data logged (only email addresses for debugging)

## Summary

The development environment auto-authentication feature has been successfully implemented with the following key benefits:

✅ **Developer Experience**: No need to manually log in during development  
✅ **Production Safety**: Only works when `ENVIRONMENT=dev` or `ENVIRONMENT=preview` is set  
✅ **Backward Compatibility**: All existing authentication flows preserved  
✅ **Error Handling**: Graceful fallback to normal authentication on failures  
✅ **Testing Verified**: All functionality tested and working correctly  

The implementation is minimal, non-intrusive, and maintains the security and functionality of the production authentication system while significantly improving the development workflow. 