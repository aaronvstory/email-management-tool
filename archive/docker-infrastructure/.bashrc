#!/bin/bash
# Bash configuration for Email Management Tool container

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# Set the prompt
export PS1='\[\033[01;32m\]\u@email-tool\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '

# History settings
HISTCONTROL=ignoreboth
HISTSIZE=10000
HISTFILESIZE=20000
shopt -s histappend

# Check window size after each command
shopt -s checkwinsize

# Enable color support
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias dir='dir --color=auto'
    alias vdir='vdir --color=auto'
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# Aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias cls='clear'
alias python='python3'
alias pip='pip3'
alias runserver='python simple_app.py'
alias startapp='python simple_app.py'

# Environment variables
export FLASK_APP=simple_app.py
export FLASK_ENV=development
export FLASK_DEBUG=1
export PYTHONPATH=/workspace:$PYTHONPATH
export TERM=xterm-256color

# Function to show current git branch
parse_git_branch() {
    git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}

# Enhanced prompt with git branch
export PS1='\[\033[01;32m\]\u@email-tool\[\033[00m\]:\[\033[01;34m\]\w\[\033[01;31m\]$(parse_git_branch)\[\033[00m\]\$ '

# Navigate to workspace on startup
cd /workspace 2>/dev/null || cd /

# Enable programmable completion
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

# Welcome message (only show once)
if [ -z "$CONTAINER_WELCOMED" ]; then
    export CONTAINER_WELCOMED=1
    echo "================================================"
    echo "  Email Management Tool - Development Container"
    echo "================================================"
    echo ""
    echo "Python: $(python3 --version 2>&1)"
    echo "Working directory: $(pwd)"
    echo ""
    echo "Quick commands:"
    echo "  runserver    - Start the Flask application"
    echo "  startapp     - Alternative to start Flask"
    echo "  pytest       - Run tests"
    echo ""
    echo "Web interface available at: http://localhost:5000"
    echo "================================================"
fi