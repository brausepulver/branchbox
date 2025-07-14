FROM ubuntu:24.04
SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
   git \
   curl \
   wget \
   vim \
   nano \
   build-essential \
   python3 \
   python3-pip \
   sudo \
   openssh-client \
   ca-certificates \
   gnupg \
   lsb-release \
   && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash developer && \
   usermod -aG sudo developer && \
   echo 'developer ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

ENV NVM_DIR=/usr/local/nvm
RUN mkdir -p $NVM_DIR && \
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && \
   source $NVM_DIR/nvm.sh && \
   nvm install --lts && \
   nvm use --lts && \
   nvm alias default lts/*

RUN echo 'export NVM_DIR="/usr/local/nvm"' >> /etc/bash.bashrc && \
   echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> /etc/bash.bashrc && \
   echo '[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"' >> /etc/bash.bashrc

WORKDIR /workspace
RUN chown developer:developer /workspace

USER developer

RUN git config --global init.defaultBranch main

RUN echo 'export NVM_DIR="/usr/local/nvm"' >> ~/.bashrc && \
   echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> ~/.bashrc && \
   echo '[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"' >> ~/.bashrc

CMD ["/bin/bash"]
