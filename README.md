# branchbox

Small tool to launch isolated containers for Claude Code at light speed.

Automatically:
- Creates a container
- Installs tools, dependencies & Claude Code
- Clones your repo
- Creates a branch (without touching your original repo)
- Opens VSCode

## Installation

```bash
# With uv
uv tool install git@github.com:brausepulver/branchbox.git

# With pipx
pipx install git@github.com:brausepulver/branchbox.git
```

## Usage

```bash
# Create container from local repo
branchbox create ./my-project feature-branch

# Create from remote repo
branchbox create https://github.com/user/repo.git feature-branch

# Open VS Code in container
branchbox code repo-branch

# Launch Claude Code in container
branchbox claude repo-branch

# Run git commands
branchbox git repo-branch status
branchbox git repo-branch add .
branchbox git repo-branch commit -m "changes"

# Sync changes back to local repo or remote
branchbox push repo-branch

# Container management
branchbox ls
branchbox start repo-branch
branchbox stop repo-branch
branchbox rm repo-branch
```

Containers are named branchbox-repo-branch. Branchbox also accepts repo-branch format.
