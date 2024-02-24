# FastAPI blog platform

Blog on FastAPI Python Framework with user authentication and authorization,
blog post management, comments, search and filters, categories and tags, user's dashboard etc.

[![FastAPI CI](https://github.com/sergey-vernyk/FastAPI-blog/actions/workflows/fastapi-ci-testing.yml/badge.svg?event=workflow_dispatch)](https://github.com/sergey-vernyk/FastAPI-blog/actions/workflows/fastapi-ci-testing.yml)
# Content 

 + [Deploy on Kubermetes local cluster (minikube)](#deploy-on-local-kubernetes-cluster-minikube)
   * [Structure of **kubernetes** directory](#structure-of-kubernetes-directory) 
   * [Create directories in minikube filesystem](#create-directories-in-minikube-filesystem)
   * [Configure PostgreSQL servers (with replication)](#configure-postgresql-servers-with-replication)
     * [Primary server](#primary-server)
     * [Standby servers](#standby-servers)
   * [Configure FastAPI application](#configure-fastapi-application)
   * [Configure Redis](#configure-redis)
   * [Configure Celery and Flower](#configure-celery-and-flower)
   * [Configure Nginx proxy](#configure-nginx-proxy)
 * [Run on a local computer](#run-on-a-local-computer)
   * [Configure Nginx](#configure-nginx)
     * [Config example](#config-example)
    * [Edit file `hosts`](#edit-file-hosts)
    * [Run PostgreSQL database](#run-postgresql-database)
    * [Install dependencies](#install-dependencies)
    * [Run server](#run-server)
    * [Run Redis](#run-redis)
    * [Run Celery with Flower](#run-celery-with-flower)

# [Deploy on local Kubernetes cluster (minikube)](#deploy-on-local-kubernetes-cluster-minikube)

### All info about installation tools such as *minikube* and *kubectl* you can find on the [Kubernetes documentation](https://kubernetes.io/docs/tasks/tools/) page.

### [Structure of **kubernetes** directory](#structure-of-kubernetes-directory)
After minikube and kubectl have been installed you can find all config `*.yaml` files in **kubernetes** directory.
|Directory                  |File                    |              Purpose  |
|--------------|-------------------------------------|-----------------------|
|config 	     |`'celery_worker_flower_config.yaml'` |Monitoring celery tasks.|
|		 	         |`'nginx_config.yaml'`				         |Main proxy server config file.|
|		 	         |`'postgres_standby_config.yaml'`	   |Content for `postgresql.conf` and `pg_hba.conf` files.|
|        	     |`'postgres_standby_init.yaml'`       |Contains bash script to make backup from primary server.
|		 	         |`'redis_config.yaml'`  			         |Contains redis config file content with necessary settings.
|deployments   |`'deployment_app.yaml'`			         |Config for deployment stateless FastAPI application in cluster and service for interactions with the application.
|			         |`'deployment_celery.yaml'`		       |Config for deployment application Celery worker in cluster. Service for interactions with worker.
|			         |`'deployment_nginx.yaml'`		         |Config for deployment in cluster proxy server for serving static files. Service for interactions with proxy. All requests go through the server.
|			         |`'deployment_redis.yaml'`			       |Config for deployment Redis in cluster. Redis used as broker and result backend for Celery worker.
|ingress	     |`'ingress_dashboard.yaml'`		       |Config for using standart Kubernetes dashboard through Nginx controller on HTTP port 80.
|statefulset   |`'stateful_postgres_primary.yaml'`   |Config for primary PostgreSQL server as stateful application. Used for both writing and reading to/from FastAPI application.
|			         |`'stateful_postgres_standby.yaml'`   |Config for standby server as stateful application. Used only in reading mode. Works in replication mode with primary database server.
|volumes	     |`'volume_app_claim.yaml'`			       |Config for define persistent volume claims PVC for preserve static files, log files and SSL certifacate files on local minikube storage.
|			         |`'volume_redis_claim.yaml'`		       |Config for define persistent volume claims PVC for preserve data for Redis server on local minikube storage.
|			         |`'volume_redis.yaml'`				         |Config for define persistent volume PV for Redis.
|			         |`'volumes_app.yaml'`				         |Config for define persistent volume PV for FastAPI application.
### [FastAPI secrets](#fastapi-secrets)
`secrets-app.yaml`

    apiVersion: v1
    kind: Secret
    metadata:
	  name: fastapi-secrets
    type: Opaque
    data:
      DATABASE_URL: base64 value
      ADMIN_EMAIL: base64 value
      SECRET_KEY: base64 value
      ALGORITHM: base64 value
      DATABASE_URL_TEST:  base64 value
      EMAIL_PASSWORD: base64 value
      EMAIL_HOST: base64 value
      EMAIL_FROM: base64 value
      SECRET_KEY_TOKEN_GENERATOR: base64 value
      CELERY_BROKER_URL_PROD: base64 value
      CELERY_BACKEND_URL_PROD: base64 value
      REDIS_CACHE_URL_PROD: base64 value
      AUTH: base64 value
      OAUTH2_KEY: base64 value
      OAUTH2_SECRET: base64 value
    stringData:
      ACCESS_TOKEN_EXPIRE_MINUTES: "10080"
      DEV_OR_PROD: "prod"
      EMAIL_PORT: "465"
      TOKEN_EXPIRED_TIMEOUT: "600"
      API_VERSION: "1"
      CELERY_BROKER_URL_DEV: ""
      CELERY_BACKEND_URL_DEV: ""
      REDIS_CACHE_URL_DEV: ""
      CELERY_TASK_ALWAYS_EAGER: "False"
      AUTH_PROVIDER: flower.views.auth.GithubLoginHandler
      OAUTH2_REDIRECT_URI: http://localhost:nodePort/login
      CERTNAME: cert.pem
      CERTKEY: cert-key.pem
      
### [PostgreSQL secrets](#postgresql-secrets)
`secrets_postgres.yaml`

    apiVersion: v1
    kind: Secret
    metadata:
	  name: postgres-secrets
    type: Opaque
    data:
      POSTGRES_USER: base64 value
      POSTGRES_DB: base64 value
      POSTGRES_PASSWORD: base64 value
      POSTGRES_REPLICA_PASSWORD: base64 value

## [Create directories in minikube filesystem](#create-directories-in-minikube-filesystem)
After minikube and kubectl have been installed you must create 7 directories in your minikube filesystem, create user and group **postgres**, change owner of several ot these directories and change created directories permissions. If you will not do this, you will get an error, because all persistent volumes PV have parameter `storageClassName` as `local-storage` , that means you must have created directories in your minikube cluster filesystem which match with `mountPath` paramater in your `*.yaml` files before pod(s) will be scheduled.

    sudo mkdir -p /vol/certs /vol/static/img/posts_images /vol/static/img/users_images /vol/logs /vol/pg-data-primary-0 /vol/pg-data-standby-0 /vol/pg-data-standby-1
    sudo addgroup -S -g 70 postgres
    sudo adduser -S -D -H -u 70 postgres -G postgres
    sudo chown postgres:postgres -R /vol/pg-data-primary-0 /vol/pg-data-standby-0 /vol/pg-data-standby-1
    sudo chown $USER:$USER -R /vol/static/img/posts_images /vol/static/img/users_images
    sudo chmod 700 -R /vol/pg-data-primary-0 /vol/pg-data-standby-0 /vol/pg-data-standby-1 /vol/logs /vol/certs

## [Configure PostgreSQL servers (with replication)](#configure-postgresql-servers-with-replication)
### [Primary server](#primary-server)
*We will configure 1 primary server and 2 standby servers.* 
Before you deployed primary PostgreSQL server you should [create](#postgresql-secrets) and apply file `secrets_postgres.yaml` as `kubectl apply -f secrets_postgres.yaml` in order to have all environment variables and secrets will be in your container.
After your **primary** server PostgreSQL has been started you must set it up to use it with standby servers in streaming replication mode. First of all you should create user for replication and several replication slots (number of slots depends on number of snadby servers), in our case we will create 2 slots:

#### [Creating slots](#creating-slots)

    psql -U <username-from-database_url-param> \
	     -d <dbname-from-database_url-param> \
	     -p <port-from-database_url-param>
	
	dbname=# create role replica_user with replication password '<password>' login;
	CREATE ROLE
	
	dbname=# select pg_create_physical_replication_slot('<slot_name1>');
	pg_create_physical_replication_slot 
	-------------------------------------
	(<slot_name1>,)
	(1 row)
	
	dbname=# select pg_create_physical_replication_slot('<slot_name2>');
	pg_create_physical_replication_slot
	-------------------------------------
	(<slot_name2>,)
	(1 rows)
	
	dbname=# select slot_name from pg_replication_slots;
	slot_name
	---------------
	<slot_name1>
	<slot_name2>
	(2 rows)

Then you should set following parameters in `postgresql.conf` file (by default this file is located in `/var/lib/postgresql/data` directory):

    listen_addresses = <your-primary-pod-ip>
    port = 5432 # or other
    password_encryption = md5
    wal_level = replica
    max_wal_senders = 3 # depend on your number of standby servers (taking in account primary server too)
    max_replication_slots = 3 # depend on your number of standby servers (taking in account primary server too)
Also you should add several parameters in `pg_hba.conf` file, which is also located  on `/var/lib/postgresql/data` by default.

    host    replication                 replica_user    	                <standby-db-pod-ip>/<mask>    md5
    host    <dbname-from-database_url>  <user-from-database_url>  		<app-pod-ip>/<mask>           trust
##### [Explaining](#explaining)
For instance record `<standby-db-pod-ip>/<mask>` should contains range of IP addresses (CIDR). In my case I used `10.244.3.0/24` which means that primary server (pod) able to communicate with all standby servers (pods) with IP address within `10.244.3.1` and `10.244.3.254`.

### [Standby servers](#standby-servers)
After you configured **primary** server to use it in streaming replication next you should also configure **standby** servers as well. In order to set up standby servers you have config `postgres_standby_config.yaml` file which includes appropriate configuration. But, you need change 2 lines related to `postgresql.conf` file:

    primary_conninfo = 'host=postgresql-db-stateful-primary-0.postgres-db-service.default.svc.cluster.local port=5432 user=replica_user require_auth=md5 password=<password>' # connection string to sending server
    primary_slot_name = '<slot_name>'      # replication slot on sending server
  
 where `password=<password>` you should replace with actual password in `md5` format and `primary_slot_name` you should replace with actual slot name. This you did [here](#creating-slots). For each standby server you must create own replica slot for streaming replication.
 
 And also you need to change line related to `pg_hba.conf` configuration:
 
    host 	 replication 	replica_user 	<primary-db-pod-ip>/<mask> 		md5

 Filling out line `<primary-db-pod-ip>/<mask>` explained [above](#explaining).

Once you have edited `postgres_standby_config.yaml` file you can apply this file as `kubectl apply -f postgres_standby_config.yaml`. Then you can apply `stateful_postgres_standby.yaml` file. And if all were done well, your standby servers should make backup from primary server and starts interact with primary server in replication streaming mode. In order to check this you can connect to primary server and do:

    dbname=# select usename,client_addr, sync_state from pg_stat_replication;
    usename      | client_addr    	     | sync_state 
    -------------+-----------------------+------------
    replica_user | <standby-db-ip-pod-1> | async
    replica_user | <standby-db-ip-pod-2> | async
    (2 rows)
    
  then connect to standby server and do:
  

    dbname=# select status, sender_host, sender_port, slot_name from pg_stat_wal_receiver;
    status     |                                         sender_host                            |sender_port |     slot_name     
    -----------+--------------------------------------------------------------------------------+------------+-------------------
    streaming  | postgresql-db-stateful-primary-0.postgres-db-service.default.svc.cluster.local |       5432 | blog_replica_slot
    (1 row)
  This means you successfully configured replication between primary and standby servers.
  
## [Configure FastAPI application](#configure-fastapi-application)
  Before apply `deployment_app.yaml` file you should [create](#fastapi-secrets) file with secrets content (`secrets-app.yaml`) and then apply it as `kubectl apply -f secrets_app.yaml`.  Further you have to create PV and PVC, which defined in files `volumes_app.yaml` and `volumes_app_claim.yaml` respectively.  You can accomplish this as `kubectl apply -f volumes_app.yaml -f volumes_app_claim.yaml`. Afterwards you can apply file `deployment_app.yaml` file and after a while application will be deployed on cluster with appropriate number of replicas defined in config file.
  
## [Configure Redis](#configure-redis)
Before you deployed Redis you should apply file `redis_config.yaml` as `kubectl apply -f redis_config.yaml` in order to create Redis config with appropriate data that will be use while starting Redis server. Further you have to create PV and PVC, which defined in files `volumes_redis.yaml` and `volumes_redis_claim.yaml` respectively.  You can do this as `kubectl apply -f volumes_redis.yaml -f volumes_redis_claim.yaml`.Once neccessary configs have been applied you can apply `deployment_redis.yaml` file to deploy Redis on within cluster.

## [Configure Celery and Flower](#configure-celery-and-flower)
Before you deployed Celery you should apply file `celery_worker_flower_config.yaml` as `kubectl apply -f celery_worker_flower_config.yaml` in order to have bash script that should consequently run Celery worker and monitoring tool Flower. Once config has been applied you can confidently apply `deployment_celery.yaml` file  as well to deploy Celery within cluster.

## [Configure Nginx proxy](#configure-nginx-proxy)
After FastAPI, Redis, Celery, PostgreSQL have been deployed succesfully, you can apply config `deployment_nginx.yaml` file as `kubectl apply -f deployment_nginx.yaml` to deploy Nginx proxy server.

# [Run on a local computer](#run-on-a-local-computer)
## [Configure Nginx](#configure-nginx)
FastAPI application might to run through proxy. This is provided by the framework itself. More detail at [link](https://fastapi.tiangolo.com/advanced/behind-a-proxy/?h=).

> In some situations, you might need to use a **proxy** server like Traefik or Nginx with a configuration that adds an extra path prefix that is not seen by your application.

Firstly clone repository to your computer `git clone https://github.com/sergey-vernyk/FastAPI-blog.git`.

### [Config example](#config-example)
You should set up Nginx as proxy server. Nginx config file `nginx.conf` might has following content to use with SSL certificate for develoment:

    http {
		include mime.types;

		upstream blog_fast_api {
			server 127.0.0.1:8000;
		}
		server {
			listen 			443 ssl;
			ssl_certificate		path/to/example.com.pem;
			ssl_certificate_key	path/to/example.com-key.pem;
			server_tokens 		off;
			server_name 		example.com;

			location /api/v1/ {
				proxy_pass 		https://blog_fast_api/;
				proxy_set_header 	HOST $host;
				proxy_set_header 	X-Forwarded-For $remote_addr;
				proxy_set_header 	X-Forwarded-Proto $scheme;
				proxy_set_header 	Upgrade $http_upgrade;
				proxy_redirect 		off;
				proxy_buffering 	off;
			}
			location /static/ {
				alias path/to/directory/static/;
			}
			types_hash_max_size 8192;
		}
You can generate cerificate with `mkcert` software. Detail info about installation on Windows, Linux and MacOS [here](https://github.com/FiloSottile/mkcert).

### [Edit file `hosts`](#edit-file-hosts)
In order to use `example.com` domain which should corresponds IP `127.0.0.1` or `localhost` you must append to `/etc/hosts` file (Linux) following line `127.0.0.1	example.com`. On Windows 10 file `hosts` is located on `C:\Windows\system32\drivers\etc`.

### [Run PostgreSQL database](#run-postgresql-database)
Before you run FastAPI server (uvicorn) you should make sure that your PostgreSQL server already run on particular port (in your case `5432`) and ready to receive connections. Also you can run PostgreSQL server in Docker container with published port `-p 5432:5432`.

### [Install dependencies](#install-dependencies)
Once you cloned application from Git repository then it's time to install dependencies for cloned project.
Before installing dependencies you should install `poetry` on your computer. [Instructions to install Poetry](https://python-poetry.org/docs/#installation). After `poetry` has been installed execute next commands in a terminal:

    cd FastAPI-blog/blog
    poetry install --no-root
    
**Note**:  All commands with `poetry` must be running within directory with `pyproject.toml` file, otherwise you will get an error `Poetry could not find a pyproject.toml file in <current_directory> or its parents`.

If proceess ended without any errors you can move on to the next step - run server.

### [Run server](#run-server)
If you already have certificate and nginx server is configured with appropriate paths to certificate file and key file then just run `uvicorn` server: 

    poetry run uvicorn main:app \
          --host 127.0.0.1 \
          --port 8000 \
          --reload \
          --ssl-certfile path/to/example.com.pem \
          --ssl-keyfile path/to/example.com-key.pem`
    
Open a browser and type: `https://example.com/api/v1/docs` and you can see the next result:

![Docs-API-page](https://drive.google.com/uc?export=download&id=1RxHSPkDzuj5W6HRlyjy17NCSR-khTVgg)

 ### [Run Redis](#run-redis)

You can install `redis-server` on your computer or use Docker to run `redis-server` on standard port `6379`.
Redis config you can find in `redis_config.yaml` at [link](https://github.com/sergey-vernyk/FastAPI-blog/blob/master/blog/kubernetes/configs/redis_config.yaml).

To run `redis-server` with custom config execute the next command `redis-server /path/to/config/redis.conf`.

 ### [Run Celery with Flower](#run-celery-with-flower)
 Once Redis server has been run you can run Celery and monitoring tool Flower using the following command sequence:
* In first terminal window:
	
       poetry run celery --app=celery_app.app worker --loglevel=INFO
       ....
       [tasks]
           . invalidate_cache
           . send_user_email
       ....
	    
* In second terminal window after succesfully start first command:
		
      poetry run celery --app=celery_app.app flower --port 5555
       ....
      [I 240208 21:22:03 command:177]
          Registered tasks:
                    [................
                    'invalidate_cache',
                    'send_user_email']
       ....

If you see output looks like above this means all works well.

In order to monitor Celery tasks open your favorite browser and go to `http://example.com:5555`.
 
