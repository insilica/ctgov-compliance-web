#!/usr/bin/env bash

# List of files and directories to delete (excluding Postgres data)
targets=(
  ".venv"
  "build"
  "ctgov_compliance_web.egg-info"
  ".env"
  ".postgres"
  "report.html"
  "report.json"
  "rules.log"
  # Add Nix-specific cleanup targets
  ".direnv"
  ".envrc"
  "result"
  "result-*"
  # Python cache files
  "**/__pycache__"
  "**/*.pyc"
  "**/*.pyo"
  "**/*.pyd"
  ".pytest_cache"
)

# Function to count total files to be deleted
count_total_files() {
  local total=0
  for target in "${targets[@]}"; do
    if [[ "$target" == *"*"* ]]; then
      # Count files matching glob pattern
      total=$((total + $(find . -path "$target" -type f 2>/dev/null | wc -l 2>/dev/null)))
    elif [ -e "$target" ] || [ -L "$target" ]; then
      if [ -d "$target" ]; then
        # Count files in directory
        total=$((total + $(find "$target" -type f 2>/dev/null | wc -l 2>/dev/null)))
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
  
  if [ -e "$target" ] || [ -L "$target" ]; then  # Added -L to check for symlinks
    echo -e "\nDeleting: $target"
    if ! rm -rf "$target" 2>/dev/null; then
      echo "Permission denied, trying with sudo..."
      sudo rm -rf "$target"
    fi
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
    done < <(find . -path "$target" -print0 2>/dev/null)
  else
    if [ -e "$target" ] || [ -L "$target" ]; then
      current_file=$((current_file + 1))
      delete_target "$target" "$current_file" "$total_files"
    fi
  fi
 done

echo -e "\n\nCleaning up processes..."

# Find and kill Postgres listening on port 5464
PIDS=$(lsof -t -i :5464 -sTCP:LISTEN -a -c postgres)
PROCESS=$(lsof -i :5464 -sTCP:LISTEN -a -c postgres | head -n 2)
if [ -n "$PIDS" ]; then
  echo "Killing Postgres processes on port 5464 with PID $PIDS: "
  echo "$PROCESS"
  kill $PIDS
  for pid in $PIDS; do
    while kill -0 $pid 2>/dev/null; do
      echo "Waiting for Postgres process $pid to terminate..."
      sleep 1
    done
  done
else
  echo "No Postgres processes found on port 5464"
fi

# No additional processes to clean

echo -e "\nCleanup complete. You can now run 'nix develop' for a fresh environment." 