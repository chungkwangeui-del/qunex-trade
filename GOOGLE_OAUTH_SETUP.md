# Google OAuth Setup Guide

## Step 1: Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click "Select a project" → "New Project"
3. Name: "Qunex Trade" → Create

## Step 2: Enable Google OAuth

1. In the left menu: **APIs & Services** → **OAuth consent screen**
2. Select **External** → Create
3. Fill in:
   - App name: `Qunex Trade`
   - User support email: Your email
   - Developer contact: Your email
4. Click **Save and Continue** (skip optional scopes)
5. Add test users (your email) → **Save and Continue**

## Step 3: Create OAuth Client ID

1. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
2. Application type: **Web application**
3. Name: `Qunex Trade Web`
4. Authorized JavaScript origins:
   - `http://localhost:5000`
   - `https://qunex-trade.onrender.com`
5. Authorized redirect URIs:
   - `http://localhost:5000/auth/google/callback`
   - `https://qunex-trade.onrender.com/auth/google/callback`
6. Click **Create**

## Step 4: Copy Credentials

You'll see:
- **Client ID**: `123456789-abc...apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-xyz...`

## Step 5: Set Environment Variables

### For Local Development (.env file):
```bash
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```

### For Render Deployment:
1. Go to Render Dashboard
2. Select your service → Environment
3. Add:
   - `GOOGLE_CLIENT_ID` = your_client_id
   - `GOOGLE_CLIENT_SECRET` = your_client_secret
4. Save Changes

## Step 6: Test

1. Run locally: `python web/app.py`
2. Go to `http://localhost:5000/auth/login`
3. Click "Continue with Google"
4. Sign in with Google
5. You should be logged in!

## Notes

- Google will show "This app isn't verified" warning during development
- Click "Advanced" → "Go to Qunex Trade (unsafe)" to proceed
- For production, submit app for verification (optional)
