"""
branchbox Utility Functions
"""

import logging
from pathlib import Path
from urllib.parse import urlparse


def setup_logging(verbose=False):
    log_level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger('branchbox')
    logger.setLevel(log_level)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def get_logger():
    return logging.getLogger('branchbox')


def get_repo_name(repo_path_or_url):
    """Extract repository name from path or URL"""
    if is_remote_repo(repo_path_or_url):
        # Remote URL
        if repo_path_or_url.startswith('git@'):
            # Handle git@ URLs like git@github.com:user/repo.git
            return repo_path_or_url.split('/')[-1].replace('.git', '')
        else:
            # Handle https:// URLs
            parsed = urlparse(repo_path_or_url)
            if parsed.path:
                return Path(parsed.path).stem.replace('.git', '')
            else:
                return repo_path_or_url.split('/')[-1].replace('.git', '')
    else:
        # Local path
        return Path(repo_path_or_url).resolve().name


def is_remote_repo(repo_path_or_url):
    """Check if this is a remote repository URL"""
    return repo_path_or_url.startswith(('http://', 'https://', 'git@'))


def sanitize_name(name):
    """Sanitize a name for use in Docker container names"""
    # Replace problematic characters with hyphens
    sanitized = name.replace('/', '-').replace('.', '-').replace('_', '-')
    # Remove multiple consecutive hyphens
    while '--' in sanitized:
        sanitized = sanitized.replace('--', '-')
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    # Convert to lowercase
    return sanitized.lower()


def format_table_row(columns, widths):
    """Format a table row with proper column widths"""
    formatted = []
    for col, width in zip(columns, widths):
        formatted.append(f"{str(col):<{width}}")
    return " ".join(formatted)


def confirm_action(message, default=False):
    """Ask user for confirmation"""
    suffix = " [Y/n]: " if default else " [y/N]: "
    response = input(message + suffix).strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes']
