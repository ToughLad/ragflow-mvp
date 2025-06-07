# Google OAuth Setup Guide for RAGFlow MVP

This guide will help you set up Google OAuth authentication for your RAGFlow MVP system.

## Prerequisites

You need a Google Cloud Project with the Gmail and Google Drive APIs enabled.

## Step 1: Create Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your **Project ID**

## Step 2: Enable Required APIs

1. In the Google Cloud Console, go to **APIs & Services > Library**
2. Search for and enable:
   - **Gmail API**
   - **Google Drive API**

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **+ CREATE CREDENTIALS > OAuth client ID**
3. Choose **Web application**
4. Configure the OAuth client:
   - **Name**: `RAGFlow MVP`
   - **Authorized JavaScript origins**:
     - `http://localhost:8080` (for frontend)
     - `http://localhost:8000` (for backend)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/auth/callback`

5. Click **Create**
6. **Download the JSON file** or copy the Client ID and Client Secret

## Step 4: Configure Environment Variables

Create or update your `.env` file with the OAuth credentials:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_PROJECT_ID=your_project_id_here

# Gmail inboxes to process (comma-separated)
GMAIL_INBOXES=storesnproduction@ivc-valves.com,hr.ivcvalves@gmail.com,umesh.jadhav@ivc-valves.com,arpatil@ivc-valves.com,exports@ivc-valves.com,sumit.basu@ivc-valves.com,hr@ivc-valves.com

# Google Drive folder IDs
ATTACHMENT_FOLDER_ID=1dEjEogfE3WlHypaY8vuaWiBeZjjuVTGV
DOCUMENTS_FOLDER_ID=1oas1TEtW26ZNvW2jekk6Y8R2Hb85IUmn

# Database settings
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpass
POSTGRES_DB=ragdb
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# LLM Configuration
LLM_MODEL=mistral:7b-instruct-v0.3
LLM_TEMPERATURE=0.2
LLM_TOP_K=20
LLM_TOP_P=0.7

# Daily digest settings
DIGEST_RECIPIENT=tony@ivc-valves.com
DIGEST_TIME=08:00

# SMTP settings (for sending digest emails)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_FROM_EMAIL=rag-system@ivc-valves.com
```

## Step 5: Test Authentication

1. Start your RAGFlow MVP system:
   ```bash
   docker-compose up -d
   ```

2. Open the frontend: http://localhost:8080

3. Go to the **Authentication** tab

4. Click **Authenticate** next to each Gmail inbox

5. Complete the OAuth flow for each inbox:
   - You'll be redirected to Google
   - Sign in with the appropriate account
   - Grant permissions for Gmail and Drive access
   - The popup window will close automatically

6. Verify all inboxes show as "Authenticated"

7. Click **Start Email Processing** to begin ingestion

## Step 6: Verify Setup

Check that everything is working:

1. **Authentication Status**: All inboxes should show green "Authenticated" status
2. **Email Processing**: POST to `/ingest/emails` should work without errors
3. **Search**: Try searching in the Search tab
4. **Daily Digest**: Check the scheduler status

## Troubleshooting

### Common Issues

#### 1. "redirect_uri_mismatch" Error
- **Problem**: The redirect URI doesn't match what's configured in Google Cloud Console
- **Solution**: Make sure you added `http://localhost:8000/auth/callback` to authorized redirect URIs

#### 2. "invalid_client" Error
- **Problem**: Client ID or secret is incorrect
- **Solution**: Double-check your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env

#### 3. "access_denied" Error
- **Problem**: User denied permissions or account doesn't have access
- **Solution**: 
  - Make sure the Gmail account has access to the inbox
  - Try using the actual inbox owner's Google account
  - For @ivc-valves.com addresses, ensure the user has access

#### 4. Authentication Works but Email Fetching Fails
- **Problem**: Token might not have the right scopes
- **Solution**: 
  - Re-authenticate the inbox
  - Check that both Gmail and Drive APIs are enabled
  - Verify the user has access to the specific Gmail inbox

#### 5. Multiple Users Need Access
- **Problem**: Each user needs to authenticate their own inbox
- **Solution**: Each person should authenticate their own email address through the interface

### Debug Mode

To debug authentication issues:

1. Check the browser developer console for errors
2. Check backend logs: `docker-compose logs backend`
3. Test individual endpoints:
   ```bash
   # Check auth status
   curl http://localhost:8000/api/auth/status?email=user@example.com
   
   # Check inbox list
   curl http://localhost:8000/api/inbox/list
   ```

### Domain-Wide Delegation (Advanced)

For enterprise setups where you want to access all company emails without individual authentication:

1. Create a **Service Account** in Google Cloud Console
2. Enable **Domain-wide delegation**
3. Add the service account to Google Workspace Admin Console
4. Configure the service account JSON file path in your deployment

This is more complex but allows accessing all company emails with a single service account.

## Security Notes

- OAuth tokens are encrypted before storage in the database
- Each inbox requires separate authentication for security
- Tokens are automatically refreshed when needed
- Use HTTPS in production environments
- Consider using Google Workspace service accounts for production

## Next Steps

Once authentication is working:

1. Test email ingestion: POST `/ingest/emails`
2. Test document processing: POST `/api/documents/upload`
3. Configure daily digest schedule
4. Set up monitoring and alerts
5. Consider setting up HTTPS for production use 