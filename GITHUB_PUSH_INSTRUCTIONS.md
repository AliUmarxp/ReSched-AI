# GitHub Push Instructions

This folder is GitHub-ready, but this machine currently does not expose `git`
or `gh` in the command line environment available to Codex.

## Option 1: GitHub Desktop

1. Open GitHub Desktop.
2. Choose **File -> Add local repository**.
3. Select:
   `C:\Users\ahmad\Desktop\ReSched-AI-Final`
4. If asked, create a repository.
5. Commit all files with:
   `Initial commit: ReSched AI CCP project`
6. Publish repository to GitHub.

## Option 2: Command Line

After installing Git and logging into GitHub:

```powershell
cd C:\Users\ahmad\Desktop\ReSched-AI-Final
git init
git add .
git commit -m "Initial commit: ReSched AI CCP project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ReSched-AI.git
git push -u origin main
```

If you use GitHub CLI:

```powershell
cd C:\Users\ahmad\Desktop\ReSched-AI-Final
git init
git add .
git commit -m "Initial commit: ReSched AI CCP project"
gh repo create ReSched-AI --private --source=. --remote=origin --push
```

## Included

- FastAPI backend
- React frontend
- SQLite-backed local data layer
- Extracted JSON/CSV demo dataset
- Final presentation
- Final Word report
- README, LICENSE, requirements, and project notes

## Ignored

- `.venv/`
- `__pycache__/`
- local SQLite database files
- generated timetable ZIP files
- raw `imports/` source documents
