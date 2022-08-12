BACKUP_DATE=$(date +%s)

# Saving files
echo "Timestamp: $(echo $BACKUP_DATE)"
echo "Saving files..."

mkdir $(pwd)/backups/backup_$(echo $BACKUP_DATE)

docker run -it \
  -v geonode-statics:/backup_data/geonode-statics \
  -v geonode-gsdatadir:/backup_data/geonode-gsdatadir \
  -v $(pwd)/backups/backup_$(echo $BACKUP_DATE):/backup ubuntu tar cfz /backup/backup_$(echo $BACKUP_DATE)_files.tar.gz -C /backup_data .

echo "Saving files finished"

# Saving databases
echo "Saving databases..."

echo "geonode"
docker exec db4geonode pg_dump -U postgres -Fp -c geonode > $(pwd)/backups/backup_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_db_geonode.sql

echo "geonode_data"
docker exec db4geonode pg_dump -U postgres -Fp -c geonode_data > $(pwd)/backups/backup_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_db_geonode_data.sql

echo "Compressing databases..."

echo "geonode"
tar czf $(pwd)/backups/backup_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_db_geonode.tar.gz  -C $(pwd)/backups/backup_$(echo $BACKUP_DATE) ./backup_$(echo $BACKUP_DATE)_db_geonode.sql
rm $(pwd)/backups/backup_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_db_geonode.sql

echo "geonode_data"
tar czf $(pwd)/backups/backup_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_db_geonode_data.tar.gz  -C $(pwd)/backups/backup_$(echo $BACKUP_DATE) ./backup_$(echo $BACKUP_DATE)_db_geonode_data.sql
rm $(pwd)/backups/backup_$(echo $BACKUP_DATE)/backup_$(echo $BACKUP_DATE)_db_geonode_data.sql

echo "Saving databases finished."