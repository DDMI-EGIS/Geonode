from django.http import HttpResponse

# Useful for API
from .serializers import *
from rest_framework import viewsets, generics
from rest_framework.response import Response
from geonode.layers.models import *
from geonode.base.models import *

# Filters
from rest_framework.filters import SearchFilter
from django_filters import rest_framework as django_filters

# Tool to filter bbox
from geonode.base.bbox_utils import filter_bbox # filter_bbox(queryset, bbox) => BBOX as text "xmin,ymin,xmax,ymax"

# Autocomplete
from dal import autocomplete

# OR condition
from django.db.models import Q

class ResourceDetailCustomViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows to filter geo-spatial data catalogue results
    """
    queryset = Dataset.objects.all()
    serializer_class = ResourceDetailSerializer

class ResourceCustomListView(generics.ListAPIView):
    serializer_class = ResourceSerializer

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

        # ADB theme filter
        if param_categories != None and param_categories != '':
            param_categories = param_categories.split(',')
            queryset = queryset.filter(category__identifier__in = param_categories)
        
        # Research filter on "title"
        if param_search != None and param_search != '':
            param_search = param_search.split(' ')
            for keyword in param_search:
                queryset = queryset.filter(title__icontains=keyword)
        
        # date
        if (param_date_begin != None and param_date_begin != '') and (param_date_end != None and param_date_end != '') :
            queryset = queryset.filter(date__gt=param_date_begin, date__lt=param_date_end)
        elif (param_date_begin != None and param_date_begin != ''):
            queryset = queryset.filter(date__gt=param_date_begin)
        elif (param_date_end != None and param_date_end != ''):
            queryset = queryset.filter(date__lt=param_date_end)

        # Region
        if param_regions != None and param_regions != '':
            param_regions = param_regions.split(',')
            print(param_regions)
            queryset = queryset.filter(regions__lft__gt=param_regions[0], regions__rght__lt=param_regions[1])
                
        return queryset.values('pk').distinct().order_by('title')

class ADBGeospatdivisionRegionCustomListView(generics.ListAPIView):
    serializer_class = ADBGeospatdivisionRegionSerializer

    # Adding filters
    def get_queryset(self):
        # General queryset
        queryset = ADBGeospatdivision.objects.values('rname','rcode').distinct('rname','rcode')
        return queryset


class ADBGeospatdivisionCountryCustomListView(generics.ListAPIView):
    serializer_class = ADBGeospatdivisionCountrySerializer

    # Adding filters
    def get_queryset(self):
        # General queryset
        queryset = ADBGeospatdivision.objects.all()
        # GET parameter
        param_filter = self.request.GET.get('filter')
        # Condition for filter
        if param_filter != None and param_filter != '':
            queryset = ADBGeospatdivision.objects.filter(rcode=param_filter).values('cname','ccode').distinct('cname','ccode')
        else:
            queryset = ADBGeospatdivision.objects.values('cname','ccode').distinct('cname','ccode')
            
        return queryset

class ADBGeospatdivisionSubdivisionCustomListView(generics.ListAPIView):
    serializer_class = ADBGeospatdivisionSubdivisionSerializer

    # Adding filters
    def get_queryset(self):
        # General queryset
        queryset = ADBGeospatdivision.objects.all()
        # GET parameter
        param_filter = self.request.GET.get('filter')
        # Condition for filter
        if param_filter != None and param_filter != '':
            queryset = ADBGeospatdivision.objects.filter(ccode=param_filter).values('sname','scode').distinct('sname','scode')
        else:
            queryset = ADBGeospatdivision.objects.values('sname','scode').distinct('sname','scode')
            
        return queryset

class ADBThemeCustomViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows to filter geo-spatial data catalogue results
    """
    queryset = ADBTheme.objects.all().order_by('index')
    serializer_class = ADBThemeSerializer


class ADBGeospatdivisionAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return ADBGeospatdivision.objects.none()

        qs = ADBGeospatdivision.objects.all()

        if self.q:
            param_search = self.q.split(' ')
            for keyword in param_search:
                qs = qs.filter( Q(rname__icontains=keyword) | Q(cname__icontains=keyword) | Q(sname__icontains=keyword)).order_by('rname', 'cname', 'sname')

        return qs