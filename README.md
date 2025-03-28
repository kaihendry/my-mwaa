https://eu-west-2.console.aws.amazon.com/mwaa/home?region=eu-west-2#environments

# AWS Documentation

DAG code in S3
The Amazon S3 bucket where your DAGs and supporting files are stored must have Bucket Versioning and Block Public access enabled. To select your Amazon S3 bucket, enter the URI or choose Browse S3.

DAGs folder – To choose the folder that contains the DAGs on your Amazon S3 bucket, enter the URI or choose Browse S3 and select the DAGs folder on your Amazon S3 bucket. For example:

mybucketname/dags/
└ oracle.py
Plugins file - optional – If your DAGs depend on custom plugins to run, enter the URI or choose Browse S3 and select the plugins.zip on your Amazon S3 bucket. For example:

mybucketname/plugins.zip
└ env_var_plugin_oracle.py
└ instantclient_18_5/
Requirements file - optional – If your DAGs depend on other Python dependencies to run, enter the URI or choose Browse S3 and select the requirements.txt on your Amazon S3 bucket. Any Apache Airflow packages in your requirements.txt must contain the Airflow version. For example:

mybucketname/requirements.txt
cx_Oracle==the-library-version
apache-airflow[oracle]==your-apache-airflow-version
Startup script file - optional – A startup script is a shell (.sh) script that you host in your environment's Amazon S3 bucket similar to your DAGs, requirements, and plugins. Amazon MWAA runs this script during startup on every individual Apache Airflow component before installing requirements and initializing the Apache Airflow process. You can use this script to install Linux runtimes required by your workflows, manage environment variables, and pass access tokens for custom repositories to requirements.txt. To specify a startup script, choose Browse S3 and select the script file on your Amazon S3 bucket, or enter the Amazon S3 URI.

The following is an example of a startup script that checks the MWAA_AIRFLOW_COMPONENT environment variable to install the libaio runtime on the scheduler and workers, but not on the web server.

#!/bin/sh

if [[ "${MWAA_AIRFLOW_COMPONENT}" != "webserver" ]]
then
     sudo yum -y install libaio
fi