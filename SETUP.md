# Cooperative OS — Setup & Deployment Guide

## Step 1: Create the Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) and create a new spreadsheet
2. Name it **Cooperative OS**
3. Copy the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_YOUR_SHEET_ID/edit
   ```
4. The app will auto-create all tabs (organizations, users, contributions, loans, repayments) on first run

---

## Step 2: Create a Google Service Account

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable these APIs:
   - **Google Sheets API**
   - **Google Drive API**
4. Go to **IAM & Admin → Service Accounts**
5. Click **Create Service Account**
   - Name: `cooperative-os`
   - Click **Done**
6. Click the service account → **Keys** tab → **Add Key → JSON**
7. Download the JSON file — keep it safe

---

## Step 3: Share the Sheet with the Service Account

1. Open the JSON file you downloaded
2. Copy the `client_email` value (looks like `cooperative-os@your-project.iam.gserviceaccount.com`)
3. Open your Google Sheet → **Share**
4. Paste that email and give it **Editor** access
5. Uncheck "Notify people" → Click **Share**

---

## Step 4: Configure Secrets

Create the file `.streamlit/secrets.toml` (copy from `secrets.toml.example`):

```toml
SHEET_ID = "paste-your-sheet-id-here"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "cooperative-os@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Paste in the values from your downloaded JSON file.

---

## Step 5: Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Step 6: Deploy to Streamlit Community Cloud

1. Push the project to a GitHub repo (public or private)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → connect your repo
4. Set **Main file path** to `app.py`
5. Click **Advanced settings → Secrets**
6. Paste the entire contents of your `secrets.toml` file
7. Click **Deploy**

---

## How It Works (User Flow)

### Cooperative Admin
1. Go to app → **Register Cooperative** tab
2. Fill in cooperative name, email, password
3. Receive a unique **Organization Code** (e.g. `COOP1234`)
4. Share that code with members via WhatsApp/SMS
5. Login → manage members, record contributions, approve loans

### Member
1. Get Organization Code from admin
2. Go to app → **Join as Member** tab
3. Enter the org code + personal details
4. Login → view savings, request loans, track history

---

## File Structure

```
cooperative_os/
├── app.py              # Entry point & routing
├── auth.py             # Login, signup, session
├── sheets.py           # All Google Sheets operations
├── admin.py            # Admin dashboard
├── member.py           # Member dashboard
├── requirements.txt
├── SETUP.md
└── .streamlit/
    └── secrets.toml    # Your credentials (never commit this)
```

---

