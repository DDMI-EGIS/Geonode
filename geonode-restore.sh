BACKUP_DATE=$1
DOMAIN_CURRENT="geonode.spade-staging.egis-eau-sas.fr"
DOMAIN_CURRENT_NOPT=$(echo $DOMAIN_CURRENT | sed 's/\.//g')
DOMAIN_MIGRATED_FROM=$2
DOMAIN_MIGRATED_FROM_NOPT=$(echo $DOMAIN_MIGRATED_FROM | sed 's/\.//g')
PGPASSWORD="postgres"
PGUSER="postgres"
PGHOST="db"

## Creating working folder
echo "Restoring geonode at timestamp $BACKUP_DATE"
echo "Creating working folder..."
rm -R $(pwd)/restores/restore_$(echo $BACKUP_DATE)
mkdir $(pwd)/restores/restore_$(echo $BACKUP_DATE)

## Extracting files into working folder...
echo "Extracting files into working folder..."
tar -xzvf $(pwd)/backups/backup_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_files.tar.gz -C $(pwd)/restores/restore_$(echo $BACKUP_DATE)

## Extracting database backup file into working folder...
echo "Extracting database backup file into working folder..."
tar -xzvf $(pwd)/backups/backup_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_db_geonode.tar.gz -C $(pwd)/restores/restore_$(echo $BACKUP_DATE)
tar -xzvf $(pwd)/backups/backup_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_db_geonode_data.tar.gz -C $(pwd)/restores/restore_$(echo $BACKUP_DATE)

## Migrating domain names
if [ $2 ]
then
  echo "Migrating domain names..."
  find $(pwd)/restores/restore_$(echo $BACKUP_DATE) -type f -exec sed -i "s/$DOMAIN_MIGRATED_FROM/$DOMAIN_CURRENT/g" {} \;
  find $(pwd)/restores/restore_$(echo $BACKUP_DATE) -type f -exec sed -i "s/$DOMAIN_MIGRATED_FROM_NOPT/$DOMAIN_CURRENT_NOPT/g" {} \;
fi

## Stopping geonode services in order to start restore...
echo "Stopping all geonode services in order to start restore..."
docker-compose down

## Running db restore...
docker-compose up -d db
echo "Running db restore..."
docker exec -i db4geonode dropdb -U postgres geonode
docker exec -i db4geonode dropdb -U postgres geonode_data
docker exec -i db4geonode createdb -U postgres geonode
docker exec -i db4geonode createdb -U postgres geonode_data
cat $(pwd)/restores/restore_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_db_geonode_data.sql | docker exec -i db4geonode psql -U postgres -d geonode_data
cat $(pwd)/restores/restore_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_db_geonode.sql | docker exec -i db4geonode psql -U postgres -d geonode

docker-compose down

## Restoring files
echo "Restoring files..."

## Folder gsdatadir
echo "Folder gsdatadir"
docker run \
  -v $(pwd)/restores/restore_$(echo $BACKUP_DATE)/geonode-gsdatadir:/backup-geonode-gsdatadir \
  -v geonode-gsdatadir:/restore-geonode-gsdatadir \
  -it \
  ubuntu  /bin/sh -c "rm -r /restore-geonode-gsdatadir/* ; cp -a /backup-geonode-gsdatadir/* /restore-geonode-gsdatadir/"

## Folder statics
echo "Folder statics"
docker run \
  -v $(pwd)/restores/restore_$(echo $BACKUP_DATE)/geonode-statics:/backup-geonode-statics \
  -v geonode-statics:/restore-geonode-statics \
  -it \
  ubuntu /bin/bash -c "rm -r /restore-geonode-statics/* ; cp -a /backup-geonode-statics/* /restore-geonode-statics/"


# Restarting geonode
echo "Restarting geonode..."
docker-compose up -d

## Fixing layer permissions
echo "Fixing layer permissions..."
docker exec -it django4geonode /bin/bash -c "python3 manage.py reassign_permissions"

# Cleaning retore files
echo "Cleaning retore files..."
rm -r $(pwd)/restores/backup_$(echo $BACKUP_DATE)
echo "Restore task finished."