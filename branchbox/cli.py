#!/usr/bin/env python3
"""
branchbox CLI - Command line interface
"""

import argparse
import sys
from .container import ContainerManager
from .utils import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description='branchbox - Containerized development environments with git branches',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  branchbox https://github.com/user/repo.git feature   # Create from remote repo
  branchbox ./my-project feature-branch                # Create from local repo
  branchbox code repo.feature                          # Open VSCode
  branchbox claude repo.feature                        # Open claude-code
  branchbox git repo.feature status                    # Run git commands
  branchbox push repo.feature                          # Push to remote
  branchbox ls                                         # List
  branchbox start/stop/rm repo.feature                 # Manage containers
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command (hidden from help since it's the default)
    create_parser = subparsers.add_parser('create', help=argparse.SUPPRESS)
    create_parser.add_argument('repo', help='Repository URL or local path')
    create_parser.add_argument('branch', nargs='?', help='Branch name (optional)')
    
    # List command
    list_parser = subparsers.add_parser('ls', help='List all containers')
    
    # Claude command
    claude_parser = subparsers.add_parser('claude', help='Open claude-code in container')
    claude_parser.add_argument('container', help='Container name')
    
    # Remove command
    remove_parser = subparsers.add_parser('rm', help='Remove a container')
    remove_parser.add_argument('container', help='Container name')
    
    # Push command
    push_parser = subparsers.add_parser('push', help='Push repository changes to remote')
    push_parser.add_argument('container', help='Container name')

    # Git command
    git_parser = subparsers.add_parser('git', help='Run git commands in container')
    git_parser.add_argument('container', help='Container name')
    git_parser.add_argument('args', nargs='*', help='Arguments to pass to git')

    # Code command
    code_parser = subparsers.add_parser('code', help='Start container and open VS Code')
    code_parser.add_argument('container', help='Container name')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start a container')
    start_parser.add_argument('container', help='Container name')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop a container')
    stop_parser.add_argument('container', help='Container name')
    
    # Help command
    help_parser = subparsers.add_parser('help', help='Show this help message')
    
    try:
        args, unknown = parser.parse_known_args()
    except SystemExit:
        # If parsing fails, show help
        parser.print_help()
        return
    
    logger = setup_logging(args.verbose)
    
    if not args.command or args.command == 'help':
        parser.print_help()
        return
    
    # Initialize container manager
    try:
        container_manager = ContainerManager()
    except Exception as e:
        logger.debug(f"Error initializing branchbox: {e}")
        sys.exit(1)
    
    # Execute commands
    try:
        if args.command == 'create':
            container_manager.create(args.repo, getattr(args, 'branch', None))
        elif args.command == 'ls':
            container_manager.list_containers()
        elif args.command == 'claude':
            container_manager.attach_claude(args.container)
        elif args.command == 'code':
            container_manager.attach_vscode(args.container)
        elif args.command == 'rm':
            container_manager.remove(args.container)
        elif args.command == 'push':
            container_manager.push(args.container)
        elif args.command == 'git':
            container_manager.git(args.container, getattr(args, 'args', []))
        elif args.command == 'start':
            container_manager.start_container(args.container)
        elif args.command == 'stop':
            container_manager.stop_container(args.container)
    except KeyboardInterrupt:
        logger.debug("\nOperation cancelled.")
    except Exception as e:
        logger.debug(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
