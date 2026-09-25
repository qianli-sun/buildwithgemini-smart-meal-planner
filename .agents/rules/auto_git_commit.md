# Auto Git Commit & Backup Rule

- **Context**: The developer workstation access is ephemeral and expires 24 hours after the training event ends. The user needs continuous automatic backups to their personal GitHub repository to avoid losing any progress.
- **Rule**: Whenever any code changes, new tools, bugfixes, or feature updates are implemented in the project, automatically stage, commit, and push the latest updates to GitHub:
  ```bash
  git add -A
  git commit -m "<concise descriptive message of the change>"
  git push origin main
  ```
- **Execution**: Run this command immediately after verifying the change, without waiting for the user to prompt for a commit.
