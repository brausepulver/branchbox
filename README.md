# branchbox

Containerized development environments with git branches for isolated coding sessions.

## Installation

```bash
# With uv (recommended)
uv tool install branchbox

# With pipx
pipx install branchbox
```

## Usage

```bash
# Create environment from remote repo
branchbox https://github.com/user/repo.git feature-branch

# Create from local repo
branchbox ./my-project feature-branch

# Open VS Code in container
branchbox code repo.branch

# Launch Claude Code in container
branchbox claude repo.branch

# Run git commands interactively
branchbox commit repo.branch status
branchbox commit repo.branch add .
branchbox commit repo.branch commit -m "changes"

# Push changes to remote
branchbox push repo.branch

# Container management
branchbox ls
branchbox start repo.branch
branchbox stop repo.branch
branchbox rm repo.branch
```

Each command creates an isolated Docker container with your repository, branch, and development tools ready to go.
