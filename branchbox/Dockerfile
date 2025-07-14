# Base image
FROM ubuntu:24.04
SHELL ["/bin/bash", "-c"]

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV NVM_DIR=/usr/local/nvm

# Install base packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl wget vim nano build-essential python3 python3-pip pipx sudo \
    openssh-client ca-certificates gnupg lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Node (nvm), JS package managers, Claude Code, and uv
RUN mkdir -p "$NVM_DIR"; \
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash; \
    . "$NVM_DIR/nvm.sh"; \
    nvm install --lts; \
    nvm alias default lts/*; \
    npm install -g npm@latest yarn pnpm @anthropic-ai/claude-code; \
    NODE_BIN_DIR="$NVM_DIR/versions/node/$(ls -v $NVM_DIR/versions/node | tail -1)/bin"; \
    ln -s "$NODE_BIN_DIR/node"   /usr/local/bin/node; \
    ln -s "$NODE_BIN_DIR/npm"    /usr/local/bin/npm; \
    ln -s "$NODE_BIN_DIR/npx"    /usr/local/bin/npx; \
    ln -s "$NODE_BIN_DIR/claude" /usr/local/bin/claude; \
    ln -s "$NODE_BIN_DIR/yarn"   /usr/local/bin/yarn; \
    ln -s "$NODE_BIN_DIR/pnpm"   /usr/local/bin/pnpm;

# Make nvm available in interactive shells
RUN echo 'export NVM_DIR="/usr/local/nvm"' > /etc/profile.d/nvm.sh && \
    echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"' >> /etc/profile.d/nvm.sh

# Create non-root developer user
RUN useradd -m -s /bin/bash developer && \
    usermod -aG sudo developer && \
    echo 'developer ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Set workspace
WORKDIR /workspace
RUN chown developer:developer /workspace

# Switch to developer user
USER developer

# Install uv
RUN pipx ensurepath && pipx install uv

# Git configuration
RUN git config --global init.defaultBranch main

# Default command
CMD ["/bin/bash"]
