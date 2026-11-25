from datetime import datetime, timedelta

from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="coffee_shop_daily",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,

    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=1),
    },
):

    load_products = BashOperator(
        task_id="load_products",
        bash_command="cd /opt/airflow/project && python load_dimensions.py products",
    )

    load_stores = BashOperator(
        task_id="load_stores",
        bash_command="cd /opt/airflow/project && python load_dimensions.py stores",
    )

    load_customers = BashOperator(
        task_id="load_customers",
        bash_command="cd /opt/airflow/project && python load_dimensions.py customers",
    )

    load_dates = BashOperator(
        task_id="load_dates",
        bash_command="cd /opt/airflow/project && python load_dimensions.py dates",
    )

    load_facts = BashOperator(
        task_id="load_facts",
        bash_command="cd /opt/airflow/project && python load_facts.py",
    )

    analysis = BashOperator(
        task_id="analysis",
        bash_command="cd /opt/airflow/project && python analysis.py",
    )

    export_report = BashOperator(
        task_id="export_report",
        bash_command="cd /opt/airflow/project && python export_report.py {{ ds }}",
    )

    dbt_build = BashOperator(
            task_id="dbt_build",
            bash_command="cd /opt/airflow/project/coffee_dbt && dbt build",
    )

    [load_products, load_stores, load_customers, load_dates] >> load_facts >> dbt_build >> [analysis, export_report]