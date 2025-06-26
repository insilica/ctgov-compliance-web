#!/usr/bin/env bash

# Progress bar function
progress_bar() {
  local current=$1
  local total=$2
  local width=50  # Width of the progress bar
  local percentage=$((current * 100 / total))
  local completed=$((width * current / total))
  local remaining=$((width - completed))
  
  printf "\rProgress: ["
  printf "%${completed}s" | tr ' ' '#'
  printf "%${remaining}s" | tr ' ' '-'
  printf "] %d%% (%d/%d files)" "$percentage" "$current" "$total"
}

# List of files and directories to delete
targets=(
  ".postgres"
  ".venv"
  "build"
  "ctgov_compliance_web.egg-info"
  ".env"
  "blazegraph.jar"
  ".blazegraph.pid"
  "blazegraph.jnl"
  "report.html"
  "report.json"
  "rules.log"
  # Add Nix-specific cleanup targets
  ".direnv"
  ".envrc"
  "result"
  "result-*"
  # Redis files
  "dump.rdb"
  # Python cache files
  "**/__pycache__"
  "**/*.pyc"
  "**/*.pyo"
  "**/*.pyd"
  ".pytest_cache"
  # AWS temporary files
  ".aws-profile"
  ".aws/credentials"
  ".aws/config"
)

# Function to count total files to be deleted
count_total_files() {
  local total=0
  for target in "${targets[@]}"; do
    if [[ "$target" == *"*"* ]]; then
      # Count files matching glob pattern
      local count
      count=$(find . -path "$target" -type f | wc -l)
      total=$((total + count))
    elif [ -e "$target" ] || [ -L "$target" ]; then
      if [ -d "$target" ]; then
        # Count files in directory
        local count
        count=$(find "$target" -type f | wc -l)
        total=$((total + count))
      else
        # Single file
        total=$((total + 1))
      fi
    fi
  done
  echo "$total"
}

# Function to safely delete a target
delete_target() {
  local target=$1
  local current_count=$2
  local total_count=$3
  
  if [ -e "$target" ] || [ -L "$target" ]; then  # Added -L to check for symlinks
    echo -e "\nDeleting: $target"
    rm -rf "$target"
    progress_bar "$current_count" "$total_count"
  fi
}

# Clean Nix store references
clean_nix_references() {
  echo -e "\nCleaning Nix store references..."
  if command -v nix &> /dev/null; then
    # Only clean up the current profile's generations
    if [ -n "$NIX_PROFILE" ]; then
      nix-env --profile "$NIX_PROFILE" --delete-generations old
    fi
    
    # Clean up only the user's profile
    nix-collect-garbage --delete-old
  fi
}

echo "Calculating total files to clean..."
total_files=$(count_total_files)
echo "Found $total_files files to clean"
current_file=0

# Loop through each target and delete it
for target in "${targets[@]}"; do
  # Handle glob patterns
  if [[ "$target" == *"*"* ]]; then
    # Use find for glob patterns
    while IFS= read -r -d '' file; do
      current_file=$((current_file + 1))
      delete_target "$file" "$current_file" "$total_files"
    done < <(find . -path "$target" -print0)
  else
    if [ -e "$target" ] || [ -L "$target" ]; then
      current_file=$((current_file + 1))
      delete_target "$target" "$current_file" "$total_files"
    fi
  fi
done

# Clean Nix store
clean_nix_references

echo -e "\n\nCleaning up processes..."

# Check if lsof is available
if ! command -v lsof >/dev/null 2>&1; then
  echo "Warning: lsof not found, skipping process cleanup"
else
  # Find and kill Postgres listening on port 5464
  echo "Checking for Postgres processes on port 5464..."
  PIDS=$(lsof -t -i :5464 -sTCP:LISTEN -a -c postgres 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    PROCESS=$(lsof -i :5464 -sTCP:LISTEN -a -c postgres | head -n 2)
    echo "Killing Postgres processes on port 5464 with PID $PIDS: "
    echo "$PROCESS"
    if kill $PIDS 2>/dev/null; then
      for pid in $PIDS; do
        while kill -0 $pid 2>/dev/null; do
          echo "Waiting for Postgres process $pid to terminate..."
          sleep 1
        done
      done
      echo "Postgres processes terminated successfully"
    else
      echo "Failed to kill Postgres processes"
    fi
  else
    echo "No Postgres processes found on port 5464"
  fi

  # Find and kill Java process listening on port 9999
  echo "Checking for Java processes on port 9999..."
  JAVA_PIDS=$(lsof -t -i :9999 -sTCP:LISTEN -a -c java 2>/dev/null || true)
  if [ -n "$JAVA_PIDS" ]; then
    JAVA_PROCESS=$(lsof -i :9999 -sTCP:LISTEN -a -c java | head -n 2)
    echo "Killing Java processes on port 9999 with PID $JAVA_PIDS:"
    echo -e "Full entry info:\n$JAVA_PROCESS"
    if kill $JAVA_PIDS 2>/dev/null; then
      for pid in $JAVA_PIDS; do
        while kill -0 $pid 2>/dev/null; do
          echo "Waiting for Java process $pid to terminate..."
          sleep 1
        done
      done
      echo "Java processes terminated successfully"
    else
      echo "Failed to kill Java processes"
    fi
  else
    echo "No Java processes found on port 9999"
  fi
fi

# Find and kill Redis server if running
echo "Checking for Redis server processes..."
if command -v pgrep >/dev/null 2>&1; then
  REDIS_PIDS=$(pgrep redis-server 2>/dev/null || true)
  if [ -n "$REDIS_PIDS" ]; then
    echo "Killing Redis server processes with PID $REDIS_PIDS"
    if kill $REDIS_PIDS 2>/dev/null; then
      for pid in $REDIS_PIDS; do
        while kill -0 $pid 2>/dev/null; do
          echo "Waiting for Redis process $pid to terminate..."
          sleep 1
        done
      done
      echo "Redis processes terminated successfully"
    else
      echo "Failed to kill Redis processes"
    fi
  else
    echo "No Redis server processes found"
  fi
else
  echo "Warning: pgrep not found, skipping Redis cleanup"
fi

echo -e "\nCleanup complete. You can now run 'nix develop' for a fresh environment."