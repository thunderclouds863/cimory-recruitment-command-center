# Hosting Step-by-Step

Use this project folder as the GitHub repository root. Do not upload the outer ZIP folder.

## Important files
- `app.py` = Streamlit entry point
- `requirements.txt` = dependencies
- `core/config.py` = reads `DATABASE_URL` from Streamlit Secrets / environment
- `core/db.py` = PostgreSQL/SQLite connection
- `.streamlit/config.toml` = Streamlit UI config
- `.streamlit/secrets.example.toml` = example only; never commit a real secrets file
- `.gitignore` = excludes `.env`, `.streamlit/secrets.toml`, and local SQLite database

## Local production-like test
1. Create `.streamlit/secrets.toml` by copying `.streamlit/secrets.example.toml`.
2. Replace `DATABASE_URL` with the direct Neon PostgreSQL connection string.
3. Run `streamlit run app.py`.
4. Login `admin` / `admin123` and verify Admin > Upload Monitor shows 17 users.

## GitHub
Create a PRIVATE empty repository. Do not initialize it with README/license/gitignore.
From this folder run:

```
git init -b main
git add .
git status
git commit -m "Initial Recruitment Command Center"
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

Make sure `.streamlit/secrets.toml` and `data/recruitment.db` are NOT listed in `git status` before commit.

## Streamlit Community Cloud
- Create app
- Existing app: Yes
- Repository: your private GitHub repo
- Branch: `main`
- Main file path: `app.py`
- Advanced settings > Secrets: paste the same values from local `.streamlit/secrets.toml`
- Choose the same Python version used locally
- Deploy
