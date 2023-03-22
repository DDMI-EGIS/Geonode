# GDC: Geo-spatial data catalogue
GDC is a handy interface for geonode dataset browsing. It allow the use to filter and display datasets on a single page application.

## Install


1. Add `'geonode.gdc'` to your `setting.py` file by pasting these lines at the end of the file:

    ```
    # django-geonode-gdc app import
    INSTALLED_APPS += ('geonode.gdc',)
    ```

2. Include the gdc URLconf in your project (here, main geonode's django folder) `urls.py` by pasting these lines at the end of the file:

    ```
    # django-geonode-gdc API endpoints
    urlpatterns += [  
        path('api/spade/', include('geonode.api_spade.urls')),
    ]
    ```

3. Add 2 attributes inside `class TopicCategory` inside `/geonode/base/models.py`: 

    ```
    # Required for GDC
    position_index = models.IntegerField(verbose_name='Position index',null=True, blank=True)
    icon_img = models.FileField(verbose_name='Image icon',null=True, blank=True)
    ```

4. Run migrations `python manage.py makemigrations && python manage.py migrate`

5. Rebuild geonode application (if you are using docker: `docker-compose build`)

6. Start the geonode server (if you are using docker: `docker-compose up -d`)

7. Visit http://example.com/gdc/ to participate in the poll.
