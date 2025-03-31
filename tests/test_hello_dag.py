import datetime
from airflow.models import DagBag


def test_dag_loaded(dagbag):
    """Test that the DAG is loaded correctly"""
    dag = dagbag.get_dag(dag_id="my_dag_name")
    assert dagbag.import_errors == {}
    assert dag is not None
    assert len(dag.tasks) == 1


def test_dag_structure(dagbag):
    """Test the structure of the DAG"""
    dag = dagbag.get_dag(dag_id="my_dag_name")
    tasks = dag.tasks
    task_ids = [task.task_id for task in tasks]

    assert "print_system_info" in task_ids
    assert tasks[0].task_type == "PythonOperator"
