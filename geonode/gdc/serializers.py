from rest_framework import serializers
from geonode.base.models import *

class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceBase
        fields = ['pk']

class ResourceDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceBase
        fields = ['title', 'thumbnail_url' , 'detail_url', 'alternate', 'date', 'date_type', 'raw_data_quality_statement', 'raw_supplemental_information', 'raw_abstract', 'alternate', 'regions', 'category', 'bbox_polygon','ll_bbox_polygon']