from django.core.management.base import BaseCommand, CommandError
from geonode.base.models import ResourceBase
from geonode.security.views import _perms_info_json
import traceback, sys

class Command(BaseCommand):
    help = "Reassign permission for all resources (usefull after layer update)"

    def handle(self, *args, **options):
        ResourceBaseList = ResourceBase.objects.all()
        for resource in ResourceBaseList:
            try:
                print("Reassign permissions to %s" % resource )
                permission_spec = _perms_info_json(resource)
                resource.set_permissions(permission_spec, True)
            except Exception:
                print("Error reassigning permissions to %s" % resource )
                print(traceback.format_exc())
                print(sys.exc_info()[2])