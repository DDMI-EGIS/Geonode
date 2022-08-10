from rest_framework import serializers
from geonode.base.models import *

# ADB SPADE CUSTOM
class ADBGeospatdivisionRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ADBGeospatdivision
        fields = ['rcode','rname']

class ADBGeospatdivisionCountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ADBGeospatdivision
        fields = ['ccode','cname']

class ADBGeospatdivisionSubdivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ADBGeospatdivision
        fields = ['scode','sname']

class ADBThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ADBTheme
        fields = '__all__'

class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceBase
        fields = ['pk']

class ResourceDetailSerializer(serializers.ModelSerializer):
    adb_themes = ADBThemeSerializer(many=True)
    class Meta:
        model = ResourceBase
        fields = ['title', 'thumbnail_url' , 'detail_url', 'alternate', 'date', 'date_type', 'raw_data_quality_statement', 'raw_supplemental_information', 'raw_abstract', 'alternate', 'adb_geospatdivision', 'adb_themes', 'bbox_polygon','ll_bbox_polygon']