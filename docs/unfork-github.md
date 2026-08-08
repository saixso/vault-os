# Drop the GitHub "forked from" badge

Repo content can be fully vault-os branded in git. The GitHub UI line
`forked from AgriciDaniel/claude-obsidian` is **metadata on GitHub's side**.
It does not go away by editing README. You must recreate the repo as a
non-fork (or ask GitHub Support to detach).

## Fast path (recommended): new non-fork repo with the same history

Requires a working `gh auth login`.

```bash
cd ~/Documents/vault-os

# 1. Rename the current fork so the name is free
gh repo rename vault-os-fork --yes

# 2. Create a fresh NON-fork repo with the original name
gh repo create saixso/vault-os --public --description "Persistent compounding Obsidian wiki vault for AI agents" --homepage "https://github.com/saixso/vault-os"

# 3. Point origin at the new repo and push everything
git remote set-url origin https://github.com/saixso/vault-os.git
git push -u origin --all
git push origin --tags

# 4. Clear About fields (no AgriciDaniel blog URL)
gh repo edit saixso/vault-os \
  --description "Persistent compounding Obsidian wiki vault for AI agents. Claude Code + Cursor plugin." \
  --homepage "https://github.com/saixso/vault-os"

# 5. Optional: archive or delete saixso/vault-os-fork once you confirm the new repo
# gh repo archive saixso/vault-os-fork --yes
```

After this, the page should show **no** "forked from" line and **no**
"N commits ahead / behind AgriciDaniel/claude-obsidian".

## Soft path (keeps the fork badge)

If you only update About for now:

```bash
gh repo edit saixso/vault-os \
  --description "Persistent compounding Obsidian wiki vault for AI agents. Claude Code + Cursor plugin." \
  --homepage "https://github.com/saixso/vault-os"
```

That removes the AgriciDaniel blog link from the sidebar, but the fork
banner and sync-fork UI remain until you recreate or detach.
