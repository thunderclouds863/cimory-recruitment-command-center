# Hosting via GitHub + Streamlit Community Cloud

## Recommended production shape

```text
Private GitHub repository
        ↓
Streamlit Community Cloud
        ↓
External PostgreSQL database
```

Do **not** rely on the local SQLite file for production hosting. Local SQLite is useful for testing on your laptop, but Streamlit Community Cloud does not guarantee persistence of files written to the app's local filesystem.

## 1. Test locally first

From the project root:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The local development database is created automatically at:

```text
data/recruitment.db
```

## 2. Create an external PostgreSQL database

Use a hosted PostgreSQL provider. Copy the connection string. The app accepts either:

```text
postgresql://...
```

or:

```text
postgresql+psycopg://...
```

The application automatically switches `postgresql://` URLs to the psycopg v3 driver included in `requirements.txt`.

## 3. Create a PRIVATE GitHub repository

Because this system contains HR/recruitment data and the repository contains bootstrap account configuration, use a **private repository**.

Put the contents of this project directly in the repository root so the structure is:

```text
repo/
├── app.py
├── requirements.txt
├── core/
├── views/
├── exports/
├── templates/
└── .streamlit/
```

Do not commit:

```text
.streamlit/secrets.toml
.env
data/recruitment.db
```

The included `.gitignore` already excludes them.

## 4. Push to GitHub

Example commands:

```powershell
git init
git add .
git commit -m "Initial recruitment command center"
git branch -M main
git remote add origin YOUR_PRIVATE_GITHUB_REPOSITORY_URL
git push -u origin main
```

## 5. Connect GitHub to Streamlit Community Cloud

1. Sign in to Streamlit Community Cloud.
2. Connect/authorize your GitHub account.
3. If the repository is private, grant Streamlit permission to access the private repository.
4. Click **Create app**.
5. Choose the repository and branch `main`.
6. Set the entrypoint file to:

```text
app.py
```

## 6. Add Streamlit Secrets

Before deploying, open **Advanced settings / Secrets** and add:

```toml
APP_NAME = "Recruitment Command Center"
AUTH_MODE = "local"
DATABASE_URL = "postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require"
```

Never put the real PostgreSQL password into GitHub.

## 7. Deploy

Click **Deploy**. On first startup, the app will automatically:

- create database tables;
- create the 17 upload accounts;
- create the `admin` account;
- create an initial active Upload Cycle;
- create the 17 Upload Cycle member statuses.

## 8. First production checks

Login as Admin:

```text
Username: admin
Password: admin123
```

Check:

1. **Admin → Users** contains 17 upload accounts + Admin.
2. **Admin → Upload Monitor** shows 17 users in `Belum Mulai`.
3. Login with one upload user.
4. Upload one intentionally invalid file and confirm `0 record` is compiled.
5. Upload one valid file and confirm status becomes `Sedang Upload`.
6. Click `Done Uploading` and confirm Admin sees `Done`.
7. Upload a new file after Done and confirm status returns to `Sedang Upload` until Done is clicked again.

## 9. New weekly/monthly upload period

Admin opens:

```text
Admin → Upload Monitor → Admin action → Buka Cycle Baru
```

Example cycle name:

```text
Compile Week 34 - August 2026
```

A new cycle resets all 17 users to `Belum Mulai` without deleting previous upload history or Central Master data.

## Security notes

- Keep the GitHub repository private.
- Keep the Streamlit app private when handling real candidate/employee data.
- Use an external PostgreSQL database for persistent data.
- Ask users to change initial passwords after first login.
- Rotate the Admin password before real production use.
