from django.urls import path, include
from django.views.generic import TemplateView

from . import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'resource_detail', views.ResourceDetailCustomViewSet)
router.register(r'adb_themes', views.ADBThemeCustomViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path(r'resource_list/', views.ResourceCustomListView.as_view()),
    path(r'adb_geospatdivision/region/', views.ADBGeospatdivisionRegionCustomListView.as_view()),
    path(r'adb_geospatdivision/country/', views.ADBGeospatdivisionCountryCustomListView.as_view()),
    path(r'adb_geospatdivision/subdivision/', views.ADBGeospatdivisionSubdivisionCustomListView.as_view()),
    path(r'geospatdivision_autocomplete/', views.ADBGeospatdivisionAutocomplete.as_view(), name='geospatdivision-autocomplete',),
    path(r'gdc_display/', TemplateView.as_view(template_name='gdc_catalog.html')),
]