# XS-Leaks: How affected are browsers and the web?

This repository contains the code for the master thesis `XS-Leaks: How affected are browsers and the web?`.
The thesis is split into two parts `test browser framework` and `does-it-leak pipeline`.
The code for the first part is fully contained in this repository. For the second part two additonal repositories need to be cloned with the following final folder structure and folder names:
- thesiscode
    - main (this repo)
    - [cookiehunter](https://projects.cispa.saarland/c01jara/cookiehunter)
    - [node-crawler](https://projects.cispa.saarland/c01jara/node-crawler)

## Installation

First follow the installation instructions here. For the `does-it-leak pipeline` then follow the instructions in the other two repositories.
The following was tested with Ubuntu 18.04. For other operating systems changes might be necessary.
- First run the installation script: `bash install.sh && source ~/.bashrc && nvm install 14 && nvm use 14`
- Configure postgres:
```
sudo su - postgres

psql
CREATE DATABASE xsleaks;
CREATE USER xsuser WITH PASSWORD '<replace with your secret password!>';
ALTER ROLE xsuser SET client_encoding TO 'utf8';
ALTER ROLE xsuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE xsuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE xsleaks TO xsuser;
\q
exit
```
- Run `cp .env.example .env` and then modify `.env` to set postgres password and other settings
- Setup pipenv and django in all repositories:
    - `source .env && pipenv install && cd automator && pipenv install && cd ../leaker-service && pipenv install && pipenv run python manage.py migrate && cd ../leaky-service && pipenv install && pipenv run python manage.py migrate && cd ../db-server && pipenv install && pipenv run python manage.py migrate && cd ../analysis && pipenv install && cd .. && pipenv run python crawler/db_filer/manage.py migrate && cd crawler && npm install && cd ..`
    - Apply two quickfixes:
        - Open `cd automator && vim $(pipenv --venv)/lib/python3.9/site-packages/selenium/webdriver/remote/webdriver.py` and change line 1008: add 'None' to the list or simply remove the line (https://github.com/SeleniumHQ/selenium/issues/9746)
        - Open `cd analysis && vim $(pipenv --venv)/lib/python3.9/site-packages/h2o/h2o.py` and `cd automator && vim $(pipenv --venv)/lib/python3.9/site-packages/h2o/h2o.py`. Comment out line 2253 `print(mojo_estimator)` in `def import_mojo(mojo_path)` in both files 

## Run Test Browser Framework

- Start docker with correct parameters: `sudo systemctl stop docker & sudo dockerd --config-file=docker-daemon.json`
- For the following open several terminals (e.g., with tmux)
- Start the automator backed: `source .env && cd automator/browsers && docker-compose up`
    - Visit http://172.17.0.1:4444/ui/index.html#/ to check if it is running
    - Optionally start a second grid: `source .env && cd automator/browsers && docker-compose -f docker-compose-copy.yml up`
    - Optionally start the watchdog service to kill old docker containers
- Start the echo application: 
    - `source .env && cd leaky-service && export VENV=$(pipenv --venv)`
    - create the url_dict: `pipenv run python url_creator.py create`
    - Start the service: `pipenv run python manage.py runserver 0.0.0.0:8000`
    - Save the dict to the db (warning this will take several minutes): http://172.17.0.1:8000/leaks/save_dict/
    - Stop the service and start the service with this command: `pipenv run uwsgi --ini uwsgi.ini`
    - Visit http://172.17.0.1:8000/leaks/info_url/1/ to check if it worked
- Start the database backed server:
    - `source .env && cd db-server && export VENV=$(pipenv --venv)`
    - Start the service: `pipenv run uwsgi --ini uwsgi.ini`
- Start the attack-page generator:
    - `source .env && cd leaker-service && export VENV=$(pipenv --venv)`
    - Start the service: `pipenv run uwsgi --ini uwsgi.ini`
    - Visit http://172.17.0.1:8001/apg/iframe/?url=https://wikipedia.org to check if it works. If the title contains `Information success` both the apg and the database backend work
- Finally, we can run the actual program:
    - Check that all parameters in `.env` are correct
    - To cover the complete test space run: `./run_server.sh 0 194000 1000 http://localhost:4444/wd/hub` and 5 minutes later (only with the second grid): `./run_server.sh 194000 388000 1000 http://localhost:4544/wd/hub`
    - For testing run: `source .env && cd automator && pipenv run python test_browsers.py local_grid 0 10 http://localhost:4444/wd/hub`
- Monitoring and logs:
    - Visit the grid overview pages: http://172.17.0.1:4444/ui/index.html#/ and http://172.17.0.1:4544/ui/index.html#/
    - Use uwsgitop: `pipenv run uwsgitop http://127.0.0.1:300X` (X=0: echo application, X=1: attack-page generator, X=2: db-server)
    - Logs for the browser are in `/tmp/dil/`

## Run the does-it-leak pipeline

- The db-server and the attack-page generator from above have to be running
- Stop/start docker as above but start the automator with this command: `source .env && cd automator/browsers && docker-compose -f docker-compose-dil.yml up`
- Start services necessary for celery:
    - broker: `docker run -d -p 5672:5672 rabbitmq`
    - cache: `docker run -d -p 6379:6379 redis`
- Follow the setup and installation procedures in the [node-crawler]( https://projects.cispa.saarland/c01jara/node-crawler) repository
- Start all celery services:
    - db-filer, responsible for saving data to the database: 
        - Run `pipenv shell`, then `cd crawler/db_filer`
        - Run `watchmedo auto-restart --directory=./ --pattern='*.py' --recursive -- celery -A main worker --loglevel=INFO --concurrency 30`
    - node-starter, responsible for starting the node-crawlers:
        - Run `pipenv shell`, then `cd crawler`
        - Run `watchmedo auto-restart --directory=./ --pattern='*.py' --recursive -- celery -A start_node worker --loglevel=INFO -n celery2@%h --concurrency 1`
    - dyn-confirmator, responsible for the dynamic confirmation:
        - Run `source .env && cd automator && export VENV=$(pipenv --venv) && pipenv shell`
        - Run ` watchmedo auto-restart --directory=./ --pattern='*.py' --recursive -- celery -A does_it_leak worker --loglevel=INFO -n celery3@%h --concurrency 30 -Ofair`
- Test websites:
    - Test (or own website):
        - Run `pipenv run python crawler/test_crawl.py`
        - For own website update the file with the correct URL and valid cookies
    - Use selenium IDE exports:
        - Record login scripts using selenium IDE and export them as `test_selenium.py`
        - Go to the automator folder: `cd automator`
        - Convert the scripts: `pipenv run python parse_scripts.py --input test_selenium.py --output test_secret.py`
        - Run the login script: `pipenv run pytest -s test_secret.py`
    - Use cookiehunter:
        - Follow the instructions in the cookiehunter repo
        - Then run `pipenv run python launcher.py --use_tranco True --t_start 0 --t_end 1000 --retry 2 --counter 1`
- Monitoring and logs:
    - Run `pipenv run celery flower` and visit http://localhost:5555/ for celery monitoring
    - Logs for node-crawler are at `/tmp/node-crawler/`
    - Logs for the dynamic confirmator are at `/tmp/dil/`



## Data analysis

- Run `cd analysis && pipenv run jupyter lab`
- Analysis files for both parts



## More information on the different services

### [leaky-service](/leaky-service/README.md)
- Available at `http://172.17.0.1:8000/` and `https://172.17.0.1:44300/`
- echo app
- leaky app

### [leaker-service](/leaker-service/README.md)
- Available at `http://172.17.0.1:8001/`
- Attack page generator

### [db-server](/db-server/README.md)
- Available at `http://172.17.0.1:8002/`
- Saves results in a postgres database

### [automator](/automator/README.md)
- Selenium automate scripts
- Selenium grid4 in docker (available at `http://172.17.0.1:4444/ui/index.html#/`)

### [analysis](/analysis/README.md)
- Python/Pandas analyses scripts
- Other helper scripts to make sense of the data
