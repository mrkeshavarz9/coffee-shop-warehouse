from datetime import datetime

from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="coffee_shop_daily",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,
):

    load_dimensions = BashOperator(
        task_id="load_dimensions",
        bash_command="cd /opt/airflow/project && python load_dimensions.py",
    )

    load_facts = BashOperator(
        task_id="load_facts",
        bash_command="cd /opt/airflow/project && python load_facts.py",
    )

    analysis = BashOperator(
        task_id="analysis",
        bash_command="cd /opt/airflow/project && python analysis.py",
    )

    load_dimensions >> load_facts >> analysis