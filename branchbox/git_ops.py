"""
ClaudeBr Git Operations
"""

import subprocess
from pathlib import Path


class GitOperations:
    def get_current_branch(self, repo_path):
        """Get current branch of a local repository"""
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            return branch if branch else "main"  # fallback for detached HEAD
        except subprocess.CalledProcessError:
            return "main"  # fallback
    
    def is_git_repository(self, path):
        """Check if a path is a git repository"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=path,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_remote_url(self, repo_path):
        """Get the remote URL of a local repository"""
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def has_uncommitted_changes(self, repo_path):
        """Check if repository has uncommitted changes"""
        try:
            # Check for staged changes
            result = subprocess.run(
                ['git', 'diff', '--cached', '--quiet'],
                cwd=repo_path,
                capture_output=True
            )
            if result.returncode != 0:
                return True
            
            # Check for unstaged changes
            result = subprocess.run(
                ['git', 'diff', '--quiet'],
                cwd=repo_path,
                capture_output=True
            )
            if result.returncode != 0:
                return True
            
            # Check for untracked files
            result = subprocess.run(
                ['git', 'ls-files', '--others', '--exclude-standard'],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                return True
            
            return False
        except subprocess.CalledProcessError:
            return False
    
    def push_changes(self, container, repo_dir="/workspace/repo"):
        """Push changes from container back to remote"""
        # TODO: Implement proper push-back logic
        # This will involve:
        # 1. Check if there are changes to push
        # 2. Add and commit changes if needed
        # 3. Push to remote origin
        # 4. Handle conflicts and merge issues
        pass
