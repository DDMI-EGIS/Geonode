# Useful for API
from .serializers import *
from rest_framework import viewsets, generics
from geonode.layers.models import *
from geonode.base.models import *

# permissions
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from geonode.base.api.permissions import (
    UserHasPerms,
)

# Tool to filter bbox
from geonode.base.bbox_utils import filter_bbox # filter_bbox(queryset, bbox) => BBOX as text "xmin,ymin,xmax,ymax"

class ResourceDetailCustomViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows to filter geo-spatial data catalogue results
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication, OAuth2Authentication]
    permission_classes = [IsAuthenticatedOrReadOnly, UserHasPerms]
    queryset = Dataset.objects.all()
    serializer_class = ResourceDetailSerializer

class ResourceCustomListView(generics.ListAPIView):
    serializer_class = ResourceSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication, OAuth2Authentication]
    permission_classes = [IsAuthenticatedOrReadOnly, UserHasPerms]

    # Adding filters
    def get_queryset(self):
        queryset = Dataset.objects.all()

        # GET parameters
        param_bbox = self.request.GET.get('bbox')
        param_categories = self.request.GET.get('categories')
        param_search = self.request.GET.get('search')
        param_regions= self.request.GET.get('regions')
        param_date_begin= self.request.GET.get('date_begin')
        param_date_end= self.request.GET.get('date_end')

        # BBOX filter
        if param_bbox  != None and param_search != '':
            queryset = filter_bbox(queryset,param_bbox)

        # Categories filter
        if param_categories != None and param_categories != '':
            param_categories = param_categories.split(',')
            queryset = queryset.filter(category__identifier__in = param_categories)
        
        # Research filter on "title"
        if param_search != None and param_search != '':
            param_search = param_search.split(' ')
            for keyword in param_search:
                queryset = queryset.filter(title__icontains=keyword)
        
        # Date filter
        if (param_date_begin != None and param_date_begin != '') and (param_date_end != None and param_date_end != '') :
            queryset = queryset.filter(date__gt=param_date_begin, date__lt=param_date_end)
        elif (param_date_begin != None and param_date_begin != ''):
            queryset = queryset.filter(date__gt=param_date_begin)
        elif (param_date_end != None and param_date_end != ''):
            queryset = queryset.filter(date__lt=param_date_end)

        # Region filter
        if param_regions != None and param_regions != '':
            param_regions = param_regions.split(',')
            print(param_regions)
            queryset = queryset.filter(regions__lft__gt=param_regions[0], regions__rght__lt=param_regions[1])
                
        return queryset.values('pk').distinct().order_by('title')
