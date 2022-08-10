## How to deploy

Theses steps allow to display on the server.

1. Clone repo to server
2. Search and replace `.env` file
    * replace ```localhost``` by ```example.com``` (```example.com``` should be the domain name of the targeted server)
    * set HTTP_HOST empty
    * change HTTPS_HOST to ```https://example.com```
    * change SITEURL to ```https://example.com```


3. Run (see next section)

## How to run
### Production mode
Start the server using:
```
    docker-compose up
```
The server startup is quite long, wait for `DJANGO ENTRYPOINT FINISHED` in the docker logs.

### Development mode
Start the server using:
```
docker-compose --project-name geonode -f docker-compose.yml -f .devcontainer/docker-compose.yml up -d
```
The server startup is quite long, wait for `DJANGO ENTRYPOINT FINISHED` in the docker logs.

If Django source code is not stable, the devlopment environment won't start

When the container has started, run the following to start the dev server:
```
docker exec -it django4geonode bash -c "python manage.py runserver 0.0.0.0:8000"
```

Bash can also be accessed running this command:
```
docker exec -it django4geonode  bash
```

From there, django commands (using manage.py) can be ran.

# Contribution guide

## GIT Commits

The commit corresponding to the creation of the release must contain only the changes related to the release and the creation of the file. It is imperative that the commit contains the description of the added features.

The following prefixes should be used:
* feat: A new feature
* fix: A bug fix
* docs: Documentation only changes
* style: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
* refactor: A code change that neither fixes a bug nor adds a feature
* perf: A code change that improves performance
* test: Adding missing or correcting existing tests
* chore: Changes to the build process or auxiliary tools and libraries such as documentation generation
