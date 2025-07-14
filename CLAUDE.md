# Claude Branch - Containerized Development with Claude Code

Claude Branch (`claude-branch`) is a tool that creates isolated, containerized development environments for working with git branches, specifically designed to integrate with Claude Code and VS Code Remote Development.

## Core Concept

The tool solves the problem of needing to work on multiple git branches simultaneously while keeping development environments completely isolated. Instead of using git worktrees directly on the host filesystem, Claude Branch creates Docker containers that act as temporary, isolated workspaces.

## Complete Workflow

### 1. Container Creation
```bash
# From remote repository
claude-branch https://github.com/user/awesome-project.git feature-auth

# From local repository  
claude-branch ./my-project hotfix-bug-123

# Default branch (current branch for local, 'main' for remote)
claude-branch https://github.com/user/project.git
```

**What happens:**
1. **Container Creation**: Spins up Ubuntu container with development tools
2. **Repository Setup**: 
   - **Remote repos**: Clones directly into container workspace
   - **Local repos**: Mounts host repo as read-only, copies to workspace
3. **Branch Management**: Creates new branch or switches to existing branch
4. **Credential Mounting**: Mounts SSH keys, git config, and Claude config
5. **Interactive Shell**: Drops you into bash in the repository directory

### 2. Development Environment

**Inside the container you get:**
- **Isolated Git Repository**: Full copy in `/workspace/repo`
- **Your Branch**: Already checked out and ready for work
- **Development Tools**: vim, nano, build tools, Node.js, Python
- **Git Authentication**: Your SSH keys and git config mounted read-only
- **Claude Code**: Installed and authenticated with your API key
- **VS Code Integration**: Container configured for Remote-Containers extension

**Key Features:**
- **Zero Host Pollution**: No changes to your host filesystem
- **Multiple Parallel Environments**: Work on different branches simultaneously
- **Credential Inheritance**: Seamlessly use your existing git and Claude credentials
- **Persistent Sessions**: Containers stay running until explicitly removed

### 3. VS Code Integration

**Automatic VS Code Setup:**
- Container includes `.devcontainer.json` configuration
- VS Code Remote-Containers extension can connect automatically  
- Full IDE experience with IntelliSense, debugging, extensions
- File changes sync between VS Code and Claude Code

**Usage:**
```bash
# VS Code will detect the dev container and offer to reopen
code .  # (from within attached container)

# Or connect remotely from host
# VS Code -> Remote-Containers -> Attach to Running Container
```

### 4. Claude Code Integration

**Installation & Authentication:**
- Claude Code installed automatically in container
- `ANTHROPIC_API_KEY` passed through from host environment
- `.claude` directory mounted for persistent configuration
- Ready to use immediately after container creation

**Workflow:**
```bash
# Inside container
claude-code  # Start interactive session
# Your existing Claude Code settings and auth carry over
```

### 5. Container Management

**List all environments:**
```bash
claude-branch ls
# Shows: Name, Repository, Branch, Status
```

**Attach to existing container:**
```bash
claude-branch attach claude-branch-project-feature-auth
# Reconnects to existing environment, starts container if stopped
```

**Remove environment:**
```bash
claude-branch rm claude-branch-project-feature-auth
# Prompts for confirmation
# TODO: Automatically pushes changes back to remote
```

## Technical Implementation

### Container Architecture
- **Base Image**: Ubuntu 22.04 with development essentials
- **User Setup**: Non-root `developer` user with sudo access
- **Working Directory**: `/workspace/repo` (your git repository)
- **Naming**: `claude-branch-{repo-name}-{branch-name}`

### Volume Mounts
- **SSH Keys**: `~/.ssh` → `/home/developer/.ssh` (read-only)
- **Git Config**: `~/.gitconfig` → `/home/developer/.gitconfig` (read-only)  
- **Claude Config**: `~/.claude` → `/home/developer/.claude` (read-write)
- **Local Repos**: `{repo-path}` → `/host-repo` (read-only, then copied)

### Branch Strategy
- **Local Repositories**: Creates new branch from current branch
- **Remote Repositories**: Creates new branch from main/default branch
- **Existing Branches**: Switches to existing branch if it exists
- **Isolation**: Each container works on exactly one branch

## Use Cases

### 1. Feature Development
```bash
# Start working on new feature
claude-branch https://github.com/company/app.git feature-user-dashboard

# Inside container: develop, commit, test with Claude Code
# Container keeps all changes isolated

# When done: push changes and remove container
```

### 2. Code Review / PR Testing
```bash
# Test a pull request without affecting your main work
claude-branch https://github.com/company/app.git pr-branch-name

# Review code, test changes, leave feedback
# Remove container when done - no cleanup needed
```

### 3. Bug Fixes
```bash
# Urgent hotfix without stopping current feature work
claude-branch ./my-project hotfix-security-issue

# Fix bug in isolation while feature work continues in parallel
# Both environments completely separate
```

### 4. Experimentation
```bash
# Try out new architecture ideas
claude-branch ./project experimental-refactor

# Safe to break things - completely isolated from main work
# Delete container when experiment is done
```

### 5. Multiple Client Projects
```bash
# Switch between client projects seamlessly
claude-branch https://github.com/client-a/project.git feature-x
claude-branch https://github.com/client-b/project.git feature-y

# Each has its own environment, dependencies, configurations
# No conflicts or cross-contamination
```

## TODO

### Automatic Push-Back
- **Smart Commit**: Auto-commit changes when removing container
- **Remote Push**: Automatically push branch to remote origin
- **Conflict Resolution**: Handle merge conflicts gracefully
- **Draft PRs**: Option to create draft pull request automatically

### Enhanced VS Code Integration
- **Auto-Open**: Automatically open VS Code when creating container
- **Extension Sync**: Sync VS Code extensions between containers
- **Settings Inheritance**: Copy VS Code settings from host

### Claude Code Enhancements
- **Session Persistence**: Resume Claude Code conversations across container restarts
- **Project Context**: Automatically provide project context to Claude
- **Workflow Integration**: Claude Code shortcuts for common git operations

### Advanced Features
- **Template Support**: Pre-configured container templates for different project types
- **Resource Limits**: Configure CPU/memory limits per container
- **Network Isolation**: Control container network access
- **Backup/Restore**: Snapshot and restore container states
