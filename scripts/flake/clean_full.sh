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
  "report.html"
  "report.json"
  "rules.log"
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

  # No additional processes to clean
fi

echo -e "\nCleanup complete. You can now run 'nix develop' for a fresh environment."