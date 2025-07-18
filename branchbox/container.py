"""
branchbox Container Management
"""

import os
import subprocess
from pathlib import Path
import docker
import io
from urllib.parse import urlunparse
from contextlib import contextmanager
import hashlib
import time
import re
import sys

from .git_ops import GitOperations
from .utils import get_repo_name, is_remote_repo, get_logger


class ContainerManager:
    def __init__(self):
        self.logger = get_logger()
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            raise Exception(f"Could not connect to Docker. Make sure Docker is running. Details: {e}")

        self.container_prefix = "branchbox"
        self.base_image = "ubuntu:22.04"
        self.workspace_dir = "/workspace"
        self.git_ops = GitOperations()

    def _get_container_name(self, repo_name, branch_name):
        """Generate a consistent container name"""
        # Clean up names to be Docker-compatible
        repo_clean = repo_name.replace('/', '-').replace('-', '-').lower()
        branch_clean = branch_name.replace('/', '-').replace('-', '-').lower()
        return f"{self.container_prefix}-{repo_clean}-{branch_clean}"

    def _resolve_container_name(self, name):
        """Resolve container name by adding prefix if needed"""
        if name.startswith(self.container_prefix):
            return name
        return f"{self.container_prefix}-{name}"

    @contextmanager
    def _container_running(self, container_name):
        """Context manager to ensure container is running, restore state afterwards"""
        resolved_name = self._resolve_container_name(container_name)
        try:
            container = self.docker_client.containers.get(resolved_name)
        except docker.errors.NotFound:
            raise Exception(f"Container {resolved_name} not found.")

        # Remember initial state
        was_stopped = container.status != 'running'

        # Start container if needed
        if was_stopped:
            self.logger.info(f"Starting container {resolved_name}...")
            container.start()

        try:
            yield container, resolved_name
        finally:
            # Restore original state
            if was_stopped:
                self.logger.debug(f"Stopping container {resolved_name}...")
                container.stop()

    def _get_dockerfile_hash(self, dockerfile_path):
        """Get SHA256 hash of Dockerfile content"""
        return hashlib.sha256(dockerfile_path.read_bytes()).hexdigest()

    def _needs_rebuild(self, dockerfile_path, image_tag):
        """Check if image needs rebuilding based on Dockerfile changes"""
        try:
            # Get current Dockerfile hash
            current_hash = self._get_dockerfile_hash(dockerfile_path)

            # Try to get existing image
            image = self.docker_client.images.get(image_tag)

            # Check if image has our hash label
            image_hash = image.labels.get('branchbox.dockerfile_hash', '')

            if image_hash != current_hash:
                self.logger.debug(f"Dockerfile changed (hash: {current_hash[:12]}...)")
                return True, current_hash

            return False, current_hash

        except docker.errors.ImageNotFound:
            return True, self._get_dockerfile_hash(dockerfile_path)

    def _build_image(self):
        """Build the base development image if it doesn't exist or Dockerfile changed"""
        image_tag = f"{self.container_prefix}-base:latest"

        dockerfile_path = Path(__file__).parent / "Dockerfile"
        if not dockerfile_path.exists():
            raise Exception(f"Dockerfile not found at {dockerfile_path}")

        # Check if rebuild is needed
        needs_rebuild, dockerfile_hash = self._needs_rebuild(dockerfile_path, image_tag)

        if not needs_rebuild:
            self.logger.debug(f"Using existing image: {image_tag}")
            return image_tag

        self.logger.info(f"Building base image: {image_tag}")
        dockerfile_content = dockerfile_path.read_text()

        dockerfile_fileobj = io.BytesIO(dockerfile_content.encode('utf-8'))

        # Build with labels including Dockerfile hash
        labels = {
            'branchbox.dockerfile_hash': dockerfile_hash,
            'branchbox.build_timestamp': str(int(time.time()))
        }

        logs = self.docker_client.api.build(
            fileobj=dockerfile_fileobj,
            tag=image_tag,
            labels=labels,
            rm=True,
            decode=True
        )

        for log in logs:
            if 'stream' in log:
                self.logger.info(log['stream'].rstrip())
            elif 'error' in log:
                self.logger.error(f"ERROR: {log['error']}")
                raise Exception(f"Build failed: {log['error']}")

        self.logger.debug(f"Successfully built image: {image_tag}")
        return image_tag

    def _stream_command_output(self, exec_result):
        """Stream command output handling ANSI escape codes and progress bars"""
        # ANSI escape sequence patterns
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        carriage_return_pattern = re.compile(r'\r(?!\n)')

        current_line = ""
        last_logged_line = ""

        for chunk in exec_result.output:
            if isinstance(chunk, bytes):
                text = chunk.decode('utf-8', errors='ignore')

                for char in text:
                    if char == '\r':
                        # Carriage return - prepare to overwrite current line
                        current_line = ""
                    elif char == '\n':
                        # Newline - finalize current line and log it
                        if current_line.strip():
                            clean_line = ansi_escape.sub('', current_line).strip()
                            if clean_line and clean_line != last_logged_line:
                                self.logger.info(f"  {clean_line}")
                                last_logged_line = clean_line
                        current_line = ""
                    else:
                        current_line += char

        # Log any remaining content
        if current_line.strip():
            clean_line = ansi_escape.sub('', current_line).strip()
            if clean_line and clean_line != last_logged_line:
                self.logger.info(f"  {clean_line}")
        
        # Return the exit code (available after consuming the stream)
        return exec_result.exit_code

    def _prepare_volumes(self, repo_path_or_url, is_remote):
        """Prepare volume mounts for the container"""
        volumes = {}

        # Mount SSH keys for git authentication
        ssh_dir = Path.home() / '.ssh'
        if ssh_dir.exists():
            volumes[str(ssh_dir)] = {'bind': '/home/developer/.ssh', 'mode': 'ro'}

        # Mount git config
        git_config = Path.home() / '.gitconfig'
        if git_config.exists():
            volumes[str(git_config)] = {'bind': '/home/developer/.gitconfig', 'mode': 'ro'}

        # Mount Claude config directory
        claude_dir = Path.home() / '.claude'
        if claude_dir.exists():
            volumes[str(claude_dir)] = {'bind': '/home/developer/.claude', 'mode': 'rw'}

        # Mount local repository
        if not is_remote:
            repo_path = Path(repo_path_or_url).resolve()
            if not repo_path.exists():
                raise Exception(f"Local repository path does not exist: {repo_path}")
            volumes[str(repo_path)] = {'bind': '/host-repo', 'mode': 'rw'}

        return volumes

    def _prepare_environment(self):
        """Prepare environment variables for the container"""
        environment = {}

        # Pass through API key if available
        if 'ANTHROPIC_API_KEY' in os.environ:
            environment['ANTHROPIC_API_KEY'] = os.environ['ANTHROPIC_API_KEY']

        return environment

    def create(self, repo_path_or_url, branch_name=None):
        """Create a new development container"""
        repo_name = get_repo_name(repo_path_or_url)
        is_remote = is_remote_repo(repo_path_or_url)

        # Determine branch name
        if not branch_name:
            if is_remote:
                branch_name = "main"  # default for remote repos
            else:
                branch_name = self.git_ops.get_current_branch(repo_path_or_url)

        container_name = self._get_container_name(repo_name, branch_name)

        # Check if container already exists
        try:
            existing = self.docker_client.containers.get(container_name)
            self.logger.info(f"Container {container_name} already exists!")

            # Start container if it's stopped
            if existing.status != 'running':
                self.logger.info(f"Starting existing container {container_name}...")
                existing.start()

            # Open VS Code for existing container
            self._open_vscode(container_name)
            return
        except docker.errors.NotFound:
            pass

        self.logger.info(f"Creating container {container_name}.")
        self.logger.debug(f"Repository: {repo_path_or_url}")
        self.logger.debug(f"Branch: {branch_name}")

        # Build base image
        image_tag = self._build_image()

        # Prepare volumes and environment
        volumes = self._prepare_volumes(repo_path_or_url, is_remote)
        environment = self._prepare_environment()

        # Create and start container
        try:
            container = self.docker_client.containers.run(
                image_tag,
                name=container_name,
                volumes=volumes,
                environment=environment,
                working_dir=self.workspace_dir,
                stdin_open=True,
                tty=True,
                detach=True,
                labels={
                    'branchbox.repo_url': repo_path_or_url,
                    'branchbox.branch_name': branch_name,
                    'branchbox.repo_name': repo_name,
                    'branchbox.is_remote': str(is_remote)
                }
            )

            self.logger.debug(f"Container {container_name} created successfully!")

            # Set up the repository inside the container
            self._setup_repo_in_container(container, repo_path_or_url, branch_name, is_remote)

            # Open VS Code
            self._open_vscode(container_name)

        except Exception as e:
            self.logger.debug(f"Error creating container: {e}")
            raise

    def _install_dependencies(self, container):
        """Detect common lock / manifest files and install dependencies."""
        self.logger.info("Installing dependencies...")

        install_cmds = [
            # Python
            ('requirements.txt', 'pip install -r requirements.txt'),
            ('pyproject.toml', 'uv sync'),
            # JavaScript
            ('package-lock.json', 'npm ci'),
            ('yarn.lock',         'yarn install --immutable'),
            ('pnpm-lock.yaml',    'pnpm install --frozen-lockfile'),
        ]

        for filename, cmd in install_cmds:
            repo_file = f"{self.workspace_dir}/repo/{filename}"
            self.logger.debug(f"Looking for {filename}…")

            # test-for-file and run install in separate steps for clearer logs
            if container.exec_run(f"test -f {repo_file}", user="developer").exit_code != 0:
                self.logger.debug(f"{filename} not found.")
                continue

            self.logger.info(f"{filename} found. Running {cmd}.")

            # Stream command output in real-time with ANSI handling
            exec_result = container.exec_run(
                f"bash -lc '{cmd}'",
                user="developer",
                workdir=f"{self.workspace_dir}/repo",
                stream=True
            )

            # Handle streaming output with progress bar overwrites and get exit code
            exit_code = self._stream_command_output(exec_result)

            if not exit_code or exit_code == 0:
                self.logger.debug(f"Installed dependencies via {filename} successfully.")
            else:
                self.logger.error(f"Dependency installation failed using {filename} (exit code: {exit_code})")
                raise Exception(f"Dependency installation failed ({filename})")

    def _setup_repo_in_container(self, container, repo_path_or_url, branch_name, is_remote):
        """Set up the git repository inside the container"""
        if is_remote:
            # Clone the remote repository
            self.logger.info("Cloning repository...")
            clone_cmd = f"git clone {repo_path_or_url} {self.workspace_dir}/repo"
            result = container.exec_run(clone_cmd, user='developer')
            if result.exit_code != 0:
                raise Exception(f"Error cloning repository: {result.output.decode()}")

            # Switch to the desired branch
            if branch_name != "main":
                self.logger.debug(f"Switching to branch: {branch_name}")
                branch_cmd = f"git checkout -b {branch_name} || git checkout {branch_name}"
                container.exec_run(branch_cmd, user='developer', workdir=f"{self.workspace_dir}/repo")
        else:
            self.logger.info("Cloning repository...")
            git_safe_dir_cmd = f"sudo git config --system --add safe.directory '*'"
            container.exec_run(git_safe_dir_cmd, user='developer')

            # Clone from the mounted read-only repository
            clone_cmd = f"git clone /host-repo {self.workspace_dir}/repo"
            result = container.exec_run(clone_cmd, user='developer')
            if result.exit_code != 0:
                raise Exception(f"Error cloning repository: {result.output.decode()}")

            # Create and switch to new branch
            self.logger.debug(f"Creating branch: {branch_name}")
            branch_cmd = f"git checkout -b {branch_name}"
            container.exec_run(branch_cmd, user='developer', workdir=f"{self.workspace_dir}/repo")

        self._install_dependencies(container)

    def _generate_vscode_folder_uri(self, container_name: str):
        """Generate a VS Code folder URI for the container"""
        return urlunparse(('vscode-remote', f'attached-container+{container_name.encode().hex()}', f'{self.workspace_dir}/repo', '', '', ''))

    def _open_vscode(self, container_name):
        """Open VS Code and attach to the container"""
        folder_uri = self._generate_vscode_folder_uri(container_name)

        try:
            self.logger.debug("Launching VSCode...")
            cmd = ['code', '--folder-uri', folder_uri]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self.logger.warning(f"Could not open VS Code automatically: {e}")

    def list_containers(self):
        """List all branchbox containers"""
        try:
            containers = self.docker_client.containers.list(
                all=True,
                filters={'label': 'branchbox.repo_name'}
            )

            if not containers:
                self.logger.debug("No branchbox containers found.")
                return

            print(f"{'Name':<35} {'Repository':<25} {'Branch':<20} {'Status':<10}")
            print("-" * 90)

            for container in containers:
                labels = container.labels
                repo_name = labels.get('branchbox.repo_name', 'unknown')
                branch = labels.get('branchbox.branch_name', 'unknown')
                status = container.status

                print(f"{container.name:<35} {repo_name:<25} {branch:<20} {status:<10}")

        except Exception as e:
            raise Exception(f"Error listing containers: {e}")

    def attach_claude(self, container_name):
        """Start container and attach Claude Code"""
        resolved_name = self._resolve_container_name(container_name)
        try:
            container = self.docker_client.containers.get(resolved_name)

            # Start container if it's stopped
            if container.status != 'running':
                self.logger.info(f"Starting container {resolved_name}...")
                container.start()

            self.logger.debug(f"Launching Claude Code...")
            self.logger.debug("Use /exit to quit Claude Code and detach from the container.")

            try:
                # Use docker exec to start Claude Code in interactive mode
                cmd = [
                    'docker', 'exec', '-it',
                    '-w', f'{self.workspace_dir}/repo',
                    '-u', 'developer',
                    resolved_name,
                    'bash', '-lc', 'claude'
                ]
                subprocess.run(cmd)
            except KeyboardInterrupt:
                self.logger.debug(f"\nDetached from {resolved_name}")

        except docker.errors.NotFound:
            raise Exception(f"Container {resolved_name} not found.")
        except Exception as e:
            raise Exception(f"Error attaching to container: {e}")

    def attach_vscode(self, container_name):
        """Start container and open VS Code"""
        resolved_name = self._resolve_container_name(container_name)
        try:
            container = self.docker_client.containers.get(resolved_name)

            # Start container if it's stopped
            if container.status != 'running':
                self.logger.info(f"Starting container {resolved_name}...")
                container.start()

            self._open_vscode(resolved_name)

        except docker.errors.NotFound:
            raise Exception(f"Container {resolved_name} not found.")
        except Exception as e:
            raise Exception(f"Error opening VS Code: {e}")

    def start_container(self, container_name):
        """Start a container"""
        resolved_name = self._resolve_container_name(container_name)
        try:
            container = self.docker_client.containers.get(resolved_name)

            if container.status == 'running':
                self.logger.debug(f"Container {resolved_name} is already running")
            else:
                self.logger.debug(f"Starting container {resolved_name}...")
                container.start()
                self.logger.debug(f"Container {resolved_name} started")

        except docker.errors.NotFound:
            raise Exception(f"Container {resolved_name} not found.")
        except Exception as e:
            raise Exception(f"Error starting container: {e}")

    def stop_container(self, container_name):
        """Stop a container"""
        resolved_name = self._resolve_container_name(container_name)
        try:
            container = self.docker_client.containers.get(resolved_name)

            if container.status != 'running':
                self.logger.debug(f"Container {resolved_name} is not running")
            else:
                self.logger.debug(f"Stopping container {resolved_name}...")
                container.stop()
                self.logger.debug(f"Container {resolved_name} stopped")

        except docker.errors.NotFound:
            raise Exception(f"Container {resolved_name} not found.")
        except Exception as e:
            raise Exception(f"Error stopping container: {e}")

    def remove(self, container_name):
        """Remove a container (with confirmation)"""
        resolved_name = self._resolve_container_name(container_name)
        try:
            container = self.docker_client.containers.get(resolved_name)

            # Get container info
            labels = container.labels
            repo_url = labels.get('branchbox.repo_url', 'unknown')
            branch = labels.get('branchbox.branch_name', 'unknown')
            is_remote = labels.get('branchbox.is_remote', 'false') == 'true'

            self.logger.debug(f"Container: {resolved_name}")
            self.logger.debug(f"Repository: {repo_url}")
            self.logger.debug(f"Branch: {branch}")

            # Confirm removal
            confirm = input("Do you want to remove this container? [y/N]: ")
            if confirm.lower() != 'y':
                self.logger.debug("Cancelled.")
                return

            # Remove container
            if container.status == 'running':
                container.stop()
            container.remove()

            self.logger.debug(f"Container {resolved_name} removed successfully.")

        except docker.errors.NotFound:
            raise Exception(f"Container {resolved_name} not found.")
        except Exception as e:
            raise Exception(f"Error removing container: {e}")

    def push(self, container_name):
        """Push repository changes to remote"""
        with self._container_running(container_name) as (container, resolved_name):
            # Get current branch
            branch_cmd = f"cd {self.workspace_dir}/repo && git branch --show-current"
            result = container.exec_run(branch_cmd, user='developer')
            if result.exit_code != 0:
                raise Exception(f"Error getting current branch: {result.output.decode()}")

            current_branch = result.output.decode().strip()
            self.logger.debug(f"Current branch: {current_branch}")

            # Add all changes
            add_cmd = f"cd {self.workspace_dir}/repo && git add ."
            result = container.exec_run(add_cmd, user='developer')
            if result.exit_code != 0:
                raise Exception(f"Error adding changes: {result.output.decode()}")

            # Check if there are changes to commit
            status_cmd = f"cd {self.workspace_dir}/repo && git status --porcelain"
            result = container.exec_run(status_cmd, user='developer')
            if result.exit_code != 0:
                raise Exception(f"Error checking status: {result.output.decode()}")

            changes = result.output.decode().strip()
            if changes:
                # Commit changes
                commit_msg = f"Auto-commit from branchbox container {resolved_name}"
                commit_cmd = f"cd {self.workspace_dir}/repo && git commit -m '{commit_msg}'"
                result = container.exec_run(commit_cmd, user='developer')
                if result.exit_code != 0:
                    self.logger.debug(f"Commit output: {result.output.decode()}")
                else:
                    self.logger.debug("Changes committed successfully")
            else:
                self.logger.debug("No changes to commit")

            # Push to remote
            push_cmd = f"cd {self.workspace_dir}/repo && git push origin {current_branch}"
            result = container.exec_run(push_cmd, user='developer')
            if result.exit_code != 0:
                raise Exception(f"Error pushing to remote: {result.output.decode()}")

            self.logger.debug(f"Successfully pushed {current_branch} to remote")

    def git(self, container_name, git_args):
        """Run git commands in container with interactive terminal"""
        with self._container_running(container_name) as (container, resolved_name):
            # Build git command
            git_cmd = ['git'] + git_args if git_args else ['git', 'status']

            # Run git command in interactive terminal
            try:
                cmd = [
                    'docker', 'exec', '-it',
                    '-w', f'{self.workspace_dir}/repo',
                    resolved_name
                ] + git_cmd
                subprocess.run(cmd)
            except KeyboardInterrupt:
                self.logger.debug("\nGit command interrupted")
