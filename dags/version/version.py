import os
import subprocess
import platform
import sys
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime


def get_git_commit():
    try:
        process = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return process.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def list_runtime_files(base_path="/", max_depth=2):
    """List files in the runtime environment with limited depth"""
    try:
        # Using find command with depth limitation for better performance
        cmd = f"find {base_path} -maxdepth {max_depth} -type f -name '*.py' | sort"
        process = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True
        )
        python_files = process.stdout.strip()

        # Also list key directories
        cmd = f"find {base_path} -maxdepth {max_depth} -type d | sort"
        process = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True
        )
        directories = process.stdout.strip()

        return {"python_files": python_files, "directories": directories}
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return {"error": str(e)}


def get_system_info():
    """Gather system information about the runtime environment"""
    info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "environment_variables": {
            k: v for k, v in os.environ.items() if "AIRFLOW" in k
        },
        "current_directory": os.getcwd(),
        "username": os.getenv("USER", "unknown"),
    }

    # Get installed packages
    try:
        process = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=True,
        )
        info["installed_packages"] = process.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        info["installed_packages"] = "Could not retrieve installed packages"

    return info


def print_runtime_info(**context):
    """Python callable to print runtime information"""
    runtime_files = list_runtime_files()
    system_info = get_system_info()

    print("=== AIRFLOW RUNTIME ENVIRONMENT ===")
    print("\n=== SYSTEM INFORMATION ===")
    for key, value in system_info.items():
        if key != "installed_packages" and key != "environment_variables":
            print(f"{key}: {value}")

    print("\n=== AIRFLOW ENVIRONMENT VARIABLES ===")
    for key, value in system_info.get("environment_variables", {}).items():
        print(f"{key}: {value}")

    # Save Python path for bash scripts
    context["ti"].xcom_push(key="python_path", value=sys.executable)

    print("\n=== RUNTIME DIRECTORIES (SAMPLE) ===")
    print(runtime_files.get("directories", "Could not list directories"))

    print("\n=== PYTHON FILES (SAMPLE) ===")
    print(runtime_files.get("python_files", "Could not list Python files"))

    return "Runtime information collected successfully"


GIT_COMMIT_HASH = get_git_commit()

with DAG(
    dag_id="my_dag_with_git_hash",
    start_date=datetime(2023, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["versioning", "runtime-discovery"],
    default_args={"owner": "airflow", "git_commit": GIT_COMMIT_HASH},
) as dag:
    # Log git version
    log_version_task = BashOperator(
        task_id="log_git_version",
        bash_command=f'echo "DAG Version (Git Commit): {GIT_COMMIT_HASH}"',
    )

    # Runtime environment discovery
    discover_runtime_task = PythonOperator(
        task_id="discover_runtime_environment",
        python_callable=print_runtime_info,
        provide_context=True,
    )

    # Get Python path to use in other tasks
    get_python_path = PythonOperator(
        task_id="get_python_path",
        python_callable=lambda **kwargs: sys.executable,
        do_xcom_push=True,
    )

    # List airflow-specific directories with fallbacks
    list_airflow_dirs = BashOperator(
        task_id="list_airflow_directories",
        bash_command="""
        echo "== AIRFLOW DIRECTORIES =="
        # Try multiple possible Airflow locations
        for dir in /usr/local/airflow /opt/airflow $AIRFLOW_HOME; do
            if [ -d "$dir" ]; then
                echo "Found Airflow directory: $dir"
                find "$dir" -maxdepth 2 -type d 2>/dev/null | sort
                break
            fi
        done
        
        # List locations where DAGs might be stored
        echo "== POSSIBLE DAG LOCATIONS =="
        find / -name "dags" -type d 2>/dev/null | head -10
        """,
    )

    # List all Python files in the DAGs folder with fallbacks
    list_dags_files = BashOperator(
        task_id="list_dags_files",
        bash_command="""
        echo "== DAG FILES =="
        # Try multiple possible DAG locations
        for dir in /usr/local/airflow/dags /opt/airflow/dags $AIRFLOW_HOME/dags; do
            if [ -d "$dir" ]; then
                echo "Found DAGs directory: $dir"
                find "$dir" -name "*.py" 2>/dev/null | sort
                break
            fi
        done
        """,
    )

    # Export runtime information to a file with reliable commands
    export_runtime_info = BashOperator(
        task_id="export_runtime_info",
        bash_command="""
        echo "Runtime Environment Info" > /tmp/airflow_runtime_info.txt
        
        # Use system Python or the one from task instance if available
        PYTHON_PATH="{{ task_instance.xcom_pull(task_ids='get_python_path') or '/usr/bin/python3' }}"
        if [ -x "$PYTHON_PATH" ]; then
            echo "Python: $($PYTHON_PATH --version 2>&1)" >> /tmp/airflow_runtime_info.txt
            echo "Python path: $PYTHON_PATH" >> /tmp/airflow_runtime_info.txt
        else
            echo "Python version: Could not determine (looking for $PYTHON_PATH)" >> /tmp/airflow_runtime_info.txt
            echo "Available Python executables:" >> /tmp/airflow_runtime_info.txt
            find / -name "python*" -type f -executable 2>/dev/null | grep -E 'bin/python[0-9.]*$' | head -5 >> /tmp/airflow_runtime_info.txt
        fi
        
        echo "System: $(uname -a 2>/dev/null || echo 'Command not available')" >> /tmp/airflow_runtime_info.txt
        
        # Try different disk usage commands
        if command -v df &> /dev/null; then
            echo "Disk Usage:" >> /tmp/airflow_runtime_info.txt
            df -h 2>/dev/null | grep -v tmpfs >> /tmp/airflow_runtime_info.txt
        else
            echo "Disk Usage: df command not available" >> /tmp/airflow_runtime_info.txt
        fi
        
        # Try different memory commands
        if command -v free &> /dev/null; then
            echo "Memory:" >> /tmp/airflow_runtime_info.txt
            free -h 2>/dev/null >> /tmp/airflow_runtime_info.txt
        elif [ -f "/proc/meminfo" ]; then
            echo "Memory:" >> /tmp/airflow_runtime_info.txt
            cat /proc/meminfo | head -5 >> /tmp/airflow_runtime_info.txt
        else
            echo "Memory: Could not determine" >> /tmp/airflow_runtime_info.txt
        fi
        
        # Airflow info
        echo "Airflow environment:" >> /tmp/airflow_runtime_info.txt
        env | grep -E 'AIRFLOW|AWS' >> /tmp/airflow_runtime_info.txt
        
        # List installed Python packages if pip is available
        if command -v pip3 &> /dev/null; then
            echo "Installed Python packages (top 10):" >> /tmp/airflow_runtime_info.txt
            pip3 freeze 2>/dev/null | sort | head -10 >> /tmp/airflow_runtime_info.txt
        fi

        # EC2 metadata if available (for MWAA running on EC2)
        if command -v curl &> /dev/null; then
            echo "EC2 Instance Metadata (if available):" >> /tmp/airflow_runtime_info.txt
            curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/instance-id >> /tmp/airflow_runtime_info.txt 2>/dev/null || echo "Not on EC2 or metadata not available" >> /tmp/airflow_runtime_info.txt
        fi
        
        echo "File created at $(date)" >> /tmp/airflow_runtime_info.txt
        cat /tmp/airflow_runtime_info.txt
        echo "Runtime info exported to /tmp/airflow_runtime_info.txt"
        """,
    )

    # Add a task to examine system paths
    examine_paths = BashOperator(
        task_id="examine_paths",
        bash_command="""
        echo "=== PATH ENVIRONMENT VARIABLE ===" > /tmp/airflow_paths.txt
        echo "$PATH" | tr ':' '\n' >> /tmp/airflow_paths.txt
        
        echo -e "\n=== EXECUTABLE LOCATIONS ===" >> /tmp/airflow_paths.txt
        for cmd in python python3 pip pip3 airflow aws; do
            echo -n "$cmd: " >> /tmp/airflow_paths.txt
            which $cmd 2>/dev/null >> /tmp/airflow_paths.txt || echo "not found" >> /tmp/airflow_paths.txt
        done
        
        echo -e "\n=== AVAILABLE PYTHON VERSIONS ===" >> /tmp/airflow_paths.txt
        find / -name "python*" -type f -executable 2>/dev/null | grep -E 'bin/python[0-9.]*$' | xargs -I{} bash -c '{} --version 2>&1 || echo "{} (no version)"' 2>/dev/null | head -5 >> /tmp/airflow_paths.txt
        
        cat /tmp/airflow_paths.txt
        """,
    )

    # Set task dependencies
    (
        log_version_task
        >> get_python_path
        >> discover_runtime_task
        >> [list_airflow_dirs, list_dags_files, examine_paths]
        >> export_runtime_info
    )
