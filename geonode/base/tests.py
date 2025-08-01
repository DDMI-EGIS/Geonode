#########################################################################
#
# Copyright (C) 2016 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

import json
import logging
import os
import requests
from PIL import Image
from io import BytesIO
from uuid import uuid4
from unittest.mock import patch, Mock
from guardian.shortcuts import assign_perm

from django.db.utils import IntegrityError, OperationalError
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib.gis.geos import Polygon, GEOSGeometry
from django.template import Template, Context
from django.contrib.auth import get_user_model
from geonode.storage.manager import storage_manager
from django.test import Client, TestCase, override_settings, SimpleTestCase
from django.shortcuts import reverse
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import CommandError

from geonode.base.populate_test_data import create_single_dataset
from geonode.maps.models import Map
from geonode.resource.utils import KeywordHandler
from geonode.thumbs import utils as thumb_utils
from geonode.base import enumerations
from geonode.layers.models import Dataset
from geonode.services.models import Service
from geonode.documents.models import Document
from geonode.tests.base import GeoNodeBaseTestSupport
from geonode.base.templatetags.base_tags import display_change_perms_button
from geonode.base.utils import OwnerRightsRequestViewUtils
from geonode.base.models import (
    HierarchicalKeyword,
    ResourceBase,
    MenuPlaceholder,
    Menu,
    MenuItem,
    Configuration,
    Region,
    TopicCategory,
    Thesaurus,
    ThesaurusKeyword,
    generate_thesaurus_reference,
)
from geonode.base.middleware import ReadOnlyMiddleware, MaintenanceMiddleware
from geonode.base.templatetags.base_tags import get_visibile_resources, facets
from geonode.base.templatetags.thesaurus import (
    get_name_translation,
    get_thesaurus_localized_label,
    get_thesaurus_translation_by_id,
    get_unique_thesaurus_set,
    get_thesaurus_title,
    get_thesaurus_date,
)
from geonode.base.templatetags.user_messages import show_notification
from geonode import geoserver
from geonode.decorators import on_ogc_backend
from geonode.resource.manager import resource_manager

test_image = Image.new("RGBA", size=(50, 50), color=(155, 0, 0))


class ThumbnailTests(GeoNodeBaseTestSupport):
    def setUp(self):
        super().setUp()
        self.rb = ResourceBase.objects.create(uuid=str(uuid4()), owner=get_user_model().objects.get(username="admin"))

    def tearDown(self):
        super().tearDown()

    def test_initial_behavior(self):
        """
        Tests that an empty resource has a missing image as null.
        """
        self.assertFalse(self.rb.has_thumbnail())
        missing = self.rb.get_thumbnail_url()
        self.assertIsNone(missing)

    def test_empty_image(self):
        """
        Tests that an empty image does not change the current resource thumbnail.
        """
        current = self.rb.get_thumbnail_url()
        self.rb.save_thumbnail("test-thumb", None)
        self.assertEqual(current, self.rb.get_thumbnail_url())

    @patch("PIL.Image.open", return_value=test_image)
    def test_monochromatic_image(self, image):
        """
        Tests that an monochromatic image does not change the current resource thumbnail.
        """
        filename = "test-thumb"

        current = self.rb.get_thumbnail_url()
        self.rb.save_thumbnail(filename, image)
        self.assertEqual(current, self.rb.get_thumbnail_url())

        # cleanup: remove saved thumbnail
        thumb_utils.remove_thumbs(filename)
        self.assertFalse(thumb_utils.thumb_exists(filename))

    @patch("PIL.Image.open", return_value=test_image)
    def test_thumb_utils_methods(self, image):
        """
        Bunch of tests on thumb_utils helpers.
        """
        filename = "test-thumb"
        upload_path = thumb_utils.thumb_path(filename)
        self.assertEqual(upload_path, os.path.join(settings.THUMBNAIL_LOCATION, filename))
        thumb_utils.remove_thumbs(filename)
        self.assertFalse(thumb_utils.thumb_exists(filename))
        f = BytesIO(test_image.tobytes())
        f.name = filename
        storage_manager.save(upload_path, File(f))
        self.assertTrue(thumb_utils.thumb_exists(filename))
        self.assertEqual(thumb_utils.thumb_size(upload_path), 10000)

        # cleanup: remove saved thumbnail
        thumb_utils.remove_thumbs(filename)
        self.assertFalse(thumb_utils.thumb_exists(filename))


class TestThumbnailUrl(GeoNodeBaseTestSupport):
    def setUp(self):
        super().setUp()
        f = BytesIO(test_image.tobytes())
        f.name = "test_image.jpeg"


class TestCreationOfMissingMetadataAuthorsOrPOC(ThumbnailTests):
    def test_add_missing_metadata_author_or_poc(self):
        """
        Test that calling add_missing_metadata_author_or_poc resource method sets
        a missing metadata_author and/or point of contact (poc) to resource owner
        """
        user, _ = get_user_model().objects.get_or_create(username="zlatan_i")

        self.rb.owner = user
        self.rb.add_missing_metadata_author_or_poc()
        self.assertTrue("zlatan_i" in [author.username for author in self.rb.metadata_author])
        self.assertTrue("zlatan_i" in [author.username for author in self.rb.poc])


class TestCreationOfContactRolesByDifferentInputTypes(ThumbnailTests):
    """
    Test that contact roles can be set as people profile
    """

    def test_set_contact_role_as_people_profile(self):
        user, _ = get_user_model().objects.get_or_create(username="zlatan_i")

        self.rb.owner = user
        self.rb.metadata_author = user
        self.rb.poc = user
        self.rb.publisher = user
        self.rb.custodian = user
        self.rb.distributor = user
        self.rb.resource_user = user
        self.rb.resource_provider = user
        self.rb.originator = user
        self.rb.principal_investigator = user
        self.rb.processor = user

        self.assertTrue("zlatan_i" in [cr.username for cr in self.rb.metadata_author])
        self.assertTrue("zlatan_i" in [cr.username for cr in self.rb.poc])
        self.assertTrue("zlatan_i" in [cr.username for cr in self.rb.publisher])
        self.assertTrue("zlatan_i" in [cr.username for cr in self.rb.custodian])
        self.assertTrue("zlatan_i" in [cr.username for cr in self.rb.distributor])
        self.assertTrue("zlatan_i" in [cr.username for cr in self.rb.resource_user])
        self.assertTrue("zlatan_i" in [cr.username for cr in self.rb.resource_provider])
        self.assertTrue("zlatan_i" in [cr.username for cr in self.rb.originator])
        self.assertTrue("zlatan_i" in [cr.username for cr in self.rb.principal_investigator])
        self.assertTrue("zlatan_i" in [cr.username for cr in self.rb.processor])

    """
    Test that contact roles can be set as list of people profiles
    """

    def test_set_contact_role_as_list_of_people(self):
        user, _ = get_user_model().objects.get_or_create(username="zlatan_i")
        user2, _ = get_user_model().objects.get_or_create(username="sven_z")

        profile_list = [user, user2]

        self.rb.owner = user
        self.rb.metadata_author = profile_list
        self.rb.poc = profile_list
        self.rb.publisher = profile_list
        self.rb.custodian = profile_list
        self.rb.distributor = profile_list
        self.rb.resource_user = profile_list
        self.rb.resource_provider = profile_list
        self.rb.originator = profile_list
        self.rb.principal_investigator = profile_list
        self.rb.processor = profile_list

        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.metadata_author])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.poc])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.publisher])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.custodian])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.distributor])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.resource_user])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.resource_provider])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.originator])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.principal_investigator])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.processor])

    """
    Test that contact roles can be set as queryset
    """

    def test_set_contact_role_as_queryset(self):
        user, _ = get_user_model().objects.get_or_create(username="zlatan_i")
        user2, _ = get_user_model().objects.get_or_create(username="sven_z")

        query = get_user_model().objects.filter(username__in=["zlatan_i", "sven_z"])

        self.rb.owner = user
        self.rb.metadata_author = query
        self.rb.poc = query
        self.rb.publisher = query
        self.rb.custodian = query
        self.rb.distributor = query
        self.rb.resource_user = query
        self.rb.resource_provider = query
        self.rb.originator = query
        self.rb.principal_investigator = query
        self.rb.processor = query

        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.metadata_author])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.poc])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.publisher])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.custodian])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.distributor])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.resource_user])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.resource_provider])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.originator])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.principal_investigator])
        self.assertTrue("zlatan_i" and "sven_z" in [cr.username for cr in self.rb.processor])


class RenderMenuTagTest(GeoNodeBaseTestSupport):
    """
    Test class for render_menu and render_top_menu custom tags of base_tags
    """

    def setUp(self):
        super().setUp()
        self.placeholder_0 = MenuPlaceholder.objects.create(name="test_menu_placeholder_0")
        self.placeholder_1 = MenuPlaceholder.objects.create(name="test_unicode_äöü_menu_placeholder_1")
        self.menu_0_0 = Menu.objects.create(title="test_menu_0_0", order=0, placeholder=self.placeholder_0)
        self.menu_0_1 = Menu.objects.create(title="test_menu_0_1", order=1, placeholder=self.placeholder_0)
        self.menu_1_0 = Menu.objects.create(title="test_unicode_äöü_menu_1_0", order=0, placeholder=self.placeholder_1)
        self.menu_item_0_0_0 = MenuItem.objects.create(
            title="test_menu_item_0_0_0", order=0, blank_target=False, url="/about", menu=self.menu_0_0
        )
        self.menu_item_0_0_1 = MenuItem.objects.create(
            title="test_menu_item_0_0_1", order=1, blank_target=False, url="/about", menu=self.menu_0_0
        )
        self.menu_item_0_1_0 = MenuItem.objects.create(
            title="test_menu_item_0_1_0", order=0, blank_target=False, url="/about", menu=self.menu_0_1
        )
        self.menu_item_0_1_1 = MenuItem.objects.create(
            title="test_menu_item_0_1_1", order=1, blank_target=False, url="/about", menu=self.menu_0_1
        )
        self.menu_item_0_1_2 = MenuItem.objects.create(
            title="test_menu_item_0_1_2", order=2, blank_target=False, url="/about", menu=self.menu_0_1
        )
        self.menu_item_1_0_0 = MenuItem.objects.create(
            title="test_unicode_äöü_menu_item_1_0_0", order=0, blank_target=False, url="/about", menu=self.menu_1_0
        )
        self.menu_item_1_0_1 = MenuItem.objects.create(
            title="test_unicode_äöü_menu_item_1_0_1", order=1, blank_target=False, url="/about", menu=self.menu_1_0
        )

    def test_get_menu_placeholder_0(self):
        template = Template("{% load base_tags %} {% get_menu 'test_menu_placeholder_0' %}")
        rendered = template.render(Context({}))
        # menu_placeholder_0
        # first menu with ascii chars
        self.assertIn(
            self.menu_0_0.title, rendered, f'Expected "{self.menu_0_0.title}" string in the rendered template'
        )
        self.assertIn(
            self.menu_item_0_0_0.title,
            rendered,
            f'Expected "{self.menu_item_0_0_0.title}" string in the rendered template',
        )
        self.assertIn(
            self.menu_item_0_0_1.title,
            rendered,
            f'Expected "{self.menu_item_0_0_1.title}" string in the rendered template',
        )
        # second menu
        self.assertIn(
            self.menu_0_1.title, rendered, f'Expected "{self.menu_0_1.title}" string in the rendered template'
        )
        self.assertIn(
            self.menu_item_0_1_0.title,
            rendered,
            f'Expected "{self.menu_item_0_1_0.title}" string in the rendered template',
        )
        self.assertIn(
            self.menu_item_0_1_1.title,
            rendered,
            f'Expected "{self.menu_item_0_1_1.title}" string in the rendered template',
        )
        self.assertIn(
            self.menu_item_0_1_2.title,
            rendered,
            f'Expected "{self.menu_item_0_1_2.title}" string in the rendered template',
        )
        # menu_placeholder_1
        # first menu
        # unicode
        self.assertNotIn(
            self.menu_1_0.title, rendered, f'No "{self.menu_1_0.title}" string expected in the rendered template'
        )
        self.assertNotIn(
            self.menu_item_1_0_0.title,
            rendered,
            f'No "{self.menu_item_1_0_0.title}" string expected in the rendered template',
        )
        self.assertNotIn(
            self.menu_item_1_0_1.title,
            rendered,
            f'No "{self.menu_item_1_0_1.title}" string expected in the rendered template',
        )

    def test_get_menu_placeholder_1(self):
        template = Template("{% load base_tags %} {% get_menu 'test_unicode_äöü_menu_placeholder_1' %}")
        rendered = template.render(Context({}))
        # menu_placeholder_0
        # first menu
        self.assertNotIn(
            self.menu_0_0.title, rendered, f'No "{self.menu_0_0.title}" string expected in the rendered template'
        )
        self.assertNotIn(
            self.menu_item_0_0_0.title,
            rendered,
            f'No "{self.menu_item_0_0_0.title}" string expected in the rendered template',
        )
        self.assertNotIn(
            self.menu_item_0_0_1.title,
            rendered,
            f'No "{self.menu_item_0_0_1.title}" string expected in the rendered template',
        )
        # second menu
        self.assertNotIn(
            self.menu_0_1.title, rendered, f'No "{self.menu_0_1.title}" string expected in the rendered template'
        )
        self.assertNotIn(
            self.menu_item_0_1_0.title,
            rendered,
            f'No "{self.menu_item_0_1_0.title}" string expected in the rendered template',
        )
        self.assertNotIn(
            self.menu_item_0_1_1.title,
            rendered,
            f'No "{self.menu_item_0_1_1.title}" string expected in the rendered template',
        )
        self.assertNotIn(
            self.menu_item_0_1_2.title,
            rendered,
            f'No "{self.menu_item_0_1_2.title}" string expected in the rendered template',
        )
        # menu_placeholder_1
        # first menu
        # unicode
        self.assertIn(
            self.menu_1_0.title, rendered, f'Expected "{self.menu_1_0.title}" string in the rendered template'
        )
        self.assertIn(
            self.menu_item_1_0_0.title,
            rendered,
            f'Expected "{self.menu_item_1_0_0.title}" string in the rendered template',
        )
        self.assertIn(
            self.menu_item_1_0_1.title,
            rendered,
            f'Expected "{self.menu_item_1_0_1.title}" string in the rendered template',
        )

    def test_render_nav_menu_placeholder_0(self):
        template = Template("{% load base_tags %} {% render_nav_menu 'test_menu_placeholder_0' %}")
        rendered = template.render(Context({}))
        # menu_placeholder_0
        # first menu
        self.assertIn(
            self.menu_0_0.title, rendered, f'Expected "{self.menu_0_0.title}" string in the rendered template'
        )
        self.assertIn(
            self.menu_item_0_0_0.title,
            rendered,
            f'Expected "{self.menu_item_0_0_0.title}" string in the rendered template',
        )
        self.assertIn(
            self.menu_item_0_0_1.title,
            rendered,
            f'Expected "{self.menu_item_0_0_1.title}" string in the rendered template',
        )
        # second menu
        self.assertIn(
            self.menu_0_1.title, rendered, f'Expected "{self.menu_0_1.title}" string in the rendered template'
        )
        self.assertIn(
            self.menu_item_0_1_0.title,
            rendered,
            f'Expected "{self.menu_item_0_1_0.title}" string in the rendered template',
        )
        self.assertIn(
            self.menu_item_0_1_1.title,
            rendered,
            f'Expected "{self.menu_item_0_1_1.title}" string in the rendered template',
        )
        self.assertIn(
            self.menu_item_0_1_2.title,
            rendered,
            f'Expected "{self.menu_item_0_1_2.title}" string in the rendered template',
        )
        # menu_placeholder_1
        # first menu
        # unicode
        self.assertNotIn(
            self.menu_1_0.title, rendered, f'No "{self.menu_1_0.title}" string expected in the rendered template'
        )
        self.assertNotIn(
            self.menu_item_1_0_0.title,
            rendered,
            f'No "{self.menu_item_1_0_0.title}" string expected in the rendered template',
        )
        self.assertNotIn(
            self.menu_item_1_0_1.title,
            rendered,
            f'No "{self.menu_item_1_0_1.title}" string expected in the rendered template',
        )

    def test_render_nav_menu_placeholder_1(self):
        template = Template("{% load base_tags %} {% render_nav_menu 'test_unicode_äöü_menu_placeholder_1' %}")
        rendered = template.render(Context({}))
        # menu_placeholder_0
        # first menu
        self.assertNotIn(
            self.menu_0_0.title, rendered, f'No "{self.menu_0_0.title}" string expected in the rendered template'
        )
        self.assertNotIn(
            self.menu_item_0_0_0.title,
            rendered,
            f'No "{self.menu_item_0_0_0.title}" string expected in the rendered template',
        )
        self.assertNotIn(
            self.menu_item_0_0_1.title,
            rendered,
            f'No "{self.menu_item_0_0_1.title}" string expected in the rendered template',
        )
        # second menu
        self.assertNotIn(
            self.menu_0_1.title, rendered, f'No "{self.menu_0_1.title}" string expected in the rendered template'
        )
        self.assertNotIn(
            self.menu_item_0_1_0.title,
            rendered,
            f'No "{self.menu_item_0_1_0.title}" string expected in the rendered template',
        )
        self.assertNotIn(
            self.menu_item_0_1_1.title,
            rendered,
            f'No "{self.menu_item_0_1_1.title}" string expected in the rendered template',
        )
        self.assertNotIn(
            self.menu_item_0_1_2.title,
            rendered,
            f'No "{self.menu_item_0_1_2.title}" string expected in the rendered template',
        )
        # menu_placeholder_1
        # first menu
        # unicode
        self.assertIn(
            self.menu_1_0.title, rendered, f'Expected "{self.menu_1_0.title}" string in the rendered template'
        )
        self.assertIn(
            self.menu_item_1_0_0.title,
            rendered,
            f'Expected "{self.menu_item_1_0_0.title}" string in the rendered template',
        )
        self.assertIn(
            self.menu_item_1_0_1.title,
            rendered,
            f'Expected "{self.menu_item_1_0_1.title}" string in the rendered template',
        )


class DeleteResourcesCommandTests(GeoNodeBaseTestSupport):
    def test_delete_resources_no_arguments(self):
        args = []
        kwargs = {}

        with self.assertRaises(CommandError) as exception:
            call_command("delete_resources", *args, **kwargs)

        self.assertIn(
            "No configuration provided", exception.exception.args[0], '"No configuration" exception expected.'
        )

    def test_delete_resources_too_many_arguments(self):
        args = []
        kwargs = {"config_path": "/example/config.txt", "map_filters": "*"}

        with self.assertRaises(CommandError) as exception:
            call_command("delete_resources", *args, **kwargs)

        self.assertIn(
            "Too many configuration options provided",
            exception.exception.args[0],
            '"Too many configuration options provided" exception expected.',
        )

    def test_delete_resource_config_file_not_existing(self):
        args = []
        kwargs = {"config_path": "/example/config.json"}

        with self.assertRaises(CommandError) as exception:
            call_command("delete_resources", *args, **kwargs)

        self.assertIn(
            "Specified configuration file does not exist",
            exception.exception.args[0],
            '"Specified configuration file does not exist" exception expected.',
        )

    def test_delete_resource_config_file_empty(self):
        # create an empty config file
        config_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "delete_resources_config.json")
        open(config_file_path, "a").close()

        args = []
        kwargs = {"config_path": config_file_path}

        with self.assertRaises(CommandError) as exception:
            call_command("delete_resources", *args, **kwargs)

        self.assertIn(
            "Specified configuration file is empty",
            exception.exception.args[0],
            '"Specified configuration file is empty" exception expected.',
        )

        # delete the config file
        os.remove(config_file_path)


class ConfigurationTest(GeoNodeBaseTestSupport):
    @on_ogc_backend(geoserver.BACKEND_PACKAGE)
    def test_read_only_whitelist(self):
        web_client = Client()

        # set read-only flag
        config = Configuration.load()
        config.read_only = True
        config.maintenance = False
        config.save()

        # post to whitelisted URLs as AnonymousUser
        for url_name in ReadOnlyMiddleware.WHITELISTED_URL_NAMES:
            if url_name == "login":
                response = web_client.post(reverse("admin:login"))
            elif url_name == "logout":
                response = web_client.post(reverse("admin:logout"))
            else:
                response = web_client.post(reverse(url_name))

            self.assertNotEqual(response.status_code, 405, "Whitelisted URL is not available.")

    def test_read_only_casual_user_privileges(self):
        web_client = Client()
        url_name = "autocomplete_region"

        # set read-only flag
        config = Configuration.load()
        config.read_only = True
        config.maintenance = False
        config.save()

        # get user
        user, _ = get_user_model().objects.get_or_create(username="user1")
        web_client.force_login(user)

        # post not whitelisted URL as superuser
        response = web_client.post(reverse(url_name))

        self.assertEqual(response.status_code, 405, "User is allowed to post to forbidden URL")

    def test_maintenance_whitelist(self):
        web_client = Client()

        # set read-only flag
        config = Configuration.load()
        config.read_only = False
        config.maintenance = True
        config.save()

        # post to whitelisted URLs as AnonymousUser
        for url_name in MaintenanceMiddleware.WHITELISTED_URL_NAMES:
            if url_name == "login":
                response = web_client.get(reverse("admin:login"))
            elif url_name == "logout":
                response = web_client.get(reverse("admin:logout"))
            elif url_name == "index":
                # url needed in the middleware only for admin panel login redirection
                continue
            else:
                response = web_client.get(reverse(url_name))

            self.assertNotEqual(response.status_code, 503, "Whitelisted URL is not available.")

    def test_maintenance_false(self):
        web_client = Client()

        # set read-only flag
        config = Configuration.load()
        config.read_only = False
        config.maintenance = False
        config.save()

        # post not whitelisted URL as superuser
        response = web_client.get("/")

        self.assertNotEqual(response.status_code, 503, "User is allowed to get index page")

    def test_maintenance_true(self):
        web_client = Client()

        # set read-only flag
        config = Configuration.load()
        config.read_only = False
        config.maintenance = True
        config.save()

        # post not whitelisted URL as superuser
        response = web_client.get("/")

        self.assertEqual(response.status_code, 503, "User is allowed to get index page")

    @patch.dict(os.environ, {"FORCE_READ_ONLY_MODE": "True"})
    def test_readonly_overwrite_by_env(self):
        config = Configuration.load()
        self.assertTrue(config.read_only)

    @patch.dict(os.environ, {"FORCE_READ_ONLY_MODE": "False"})
    def test_readonly_is_not_overwrite_by_env(self):
        # will take the value from the db
        config = Configuration.load()
        self.assertFalse(config.read_only)


class TestOwnerRightsRequestUtils(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(username="test", email="test@test.com")
        self.admin = User.objects.create(username="admin", email="test@test.com", is_superuser=True)
        self.d = Document.objects.create(uuid=str(uuid4()), owner=self.user, title="test", is_approved=True)
        self.la = Dataset.objects.create(uuid=str(uuid4()), owner=self.user, title="test", is_approved=True)
        self.s = Service.objects.create(uuid=str(uuid4()), owner=self.user, title="test", is_approved=True)
        self.m = Map.objects.create(uuid=str(uuid4()), owner=self.user, title="test", is_approved=True)

    def test_get_concrete_resource(self):
        self.assertTrue(
            isinstance(OwnerRightsRequestViewUtils.get_resource(ResourceBase.objects.get(pk=self.d.id)), Document)
        )

        self.assertTrue(
            isinstance(OwnerRightsRequestViewUtils.get_resource(ResourceBase.objects.get(pk=self.la.id)), Dataset)
        )

        self.assertTrue(
            isinstance(OwnerRightsRequestViewUtils.get_resource(ResourceBase.objects.get(pk=self.s.id)), Service)
        )

        self.assertTrue(
            isinstance(OwnerRightsRequestViewUtils.get_resource(ResourceBase.objects.get(pk=self.m.id)), Map)
        )

    @override_settings(ADMIN_MODERATE_UPLOADS=True)
    def test_msg_recipients_admin_mode(self):
        users_count = 1
        self.assertEqual(users_count, OwnerRightsRequestViewUtils.get_message_recipients(self.user).count())

    @override_settings(ADMIN_MODERATE_UPLOADS=False)
    def test_msg_recipients_workflow_off(self):
        users_count = 0
        self.assertEqual(users_count, OwnerRightsRequestViewUtils.get_message_recipients(self.user).count())

    @override_settings(ADMIN_MODERATE_UPLOADS=True)
    def test_display_change_perms_button_tag_moderated(self):
        admin_perms = display_change_perms_button(self.la, self.admin, {})
        user_perms = display_change_perms_button(self.la, self.user, {})
        self.assertTrue(admin_perms)
        self.assertFalse(user_perms)

    @override_settings(ADMIN_MODERATE_UPLOADS=False)
    def test_display_change_perms_button_tag_standard(self):
        admin_perms = display_change_perms_button(self.la, self.admin, {})
        user_perms = display_change_perms_button(self.la, self.user, {})
        self.assertTrue(admin_perms)
        self.assertTrue(user_perms)


class TestGetVisibleResource(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="mikel_arteta")
        self.category = TopicCategory.objects.create(identifier="biota")
        self.rb = ResourceBase.objects.create(uuid=str(uuid4()), category=self.category, owner=self.user)

    def test_category_data_not_shown_for_missing_resourcebase_permissions(self):
        """
        Test that a user without view permissions of a resource base does not see
        ISO category format data of the ISO category
        """
        categories = get_visibile_resources(self.user)
        self.assertEqual(categories["iso_formats"].count(), 0)

    def test_category_data_shown_for_with_resourcebase_permissions(self):
        """
        Test that a user with view permissions of a resource base can see
        ISO format data of the ISO category
        """
        assign_perm("view_resourcebase", self.user, self.rb)
        categories = get_visibile_resources(self.user)
        self.assertEqual(categories["iso_formats"].count(), 1)

    def test_visible_notifications(self):
        """
        Test that a standard user won't be able to show ADMINS_ONLY_NOTICE_TYPES
        """
        self.assertFalse(show_notification("monitoring_alert", self.user))
        self.assertTrue(show_notification("request_download_resourcebase", self.user))

    def test_extent_filter_crossing_dateline(self):
        from .bbox_utils import filter_bbox

        _ll = None
        try:
            bbox = [166.06619, -22.40043, 172.09202, -13.03425]
            _ll = Dataset.objects.create(
                uuid=str(uuid4()),
                owner=self.user,
                name="test_extent_filter_crossing_dateline",
                title="test_extent_filter_crossing_dateline",
                alternate="geonode:test_extent_filter_crossing_dateline",
                is_approved=True,
                is_published=True,
                ll_bbox_polygon=Polygon.from_bbox(bbox),
            )
            self.assertListEqual(list(_ll.ll_bbox_polygon.extent), bbox, _ll.ll_bbox_polygon.extent)
            self.assertTrue(Dataset.objects.filter(title=_ll.title).exists(), Dataset.objects.all())
            _qs = filter_bbox(
                Dataset.objects.all(), "-180.0000,-39.7790,-164.2456,9.2702,134.0552,-39.7790,180.0000,9.2702"
            )
            self.assertTrue(_qs.filter(title=_ll.title), Dataset.objects.all() | _qs.all())
        finally:
            if _ll:
                _ll.delete()


class TestHtmlTagRemoval(SimpleTestCase):
    def test_not_tags_in_attribute(self):
        attribute_target_value = "This is not a templated text"
        r = ResourceBase()
        filtered_value = r._remove_html_tags(attribute_target_value)
        self.assertEqual(attribute_target_value, filtered_value)

    def test_simple_tags_in_attribute(self):
        tagged_value = "<p>This is not a templated text<p>"
        attribute_target_value = "This is not a templated text"
        r = ResourceBase()
        filtered_value = r._remove_html_tags(tagged_value)
        self.assertEqual(filtered_value, attribute_target_value)

    def test_complex_tags_in_attribute(self):
        tagged_value = """<p style="display:none;" id="test">This is not a templated text<p>
        <div class="test_css">Something in &iacute;container</div> <p>&pound;682m</p>"""
        attribute_target_value = """This is not a templated text         Something in ícontainer £682m"""
        r = ResourceBase()
        filtered_value = r._remove_html_tags(tagged_value)
        self.assertEqual(filtered_value, attribute_target_value)

    def test_converted_html_in_tags_with_char_references(self):
        tagged_value = """<p>&lt;p&gt;Abstract value &amp; some text&lt;/p&gt;</p>"""
        attribute_target_value = """Abstract value & some text"""
        r = ResourceBase()
        filtered_value = r._remove_html_tags(tagged_value)
        self.assertEqual(filtered_value, attribute_target_value)

    def test_converted_html_in_tags_with_with_multiple_tags(self):
        tagged_value = """<p><p><p><p>Abstract value &amp; some text</p></p></p></p>"""
        attribute_target_value = """Abstract value & some text"""
        r = ResourceBase()
        filtered_value = r._remove_html_tags(tagged_value)
        self.assertEqual(filtered_value, attribute_target_value)


class TestTagThesaurus(TestCase):
    #  loading test thesausurs
    fixtures = ["test_thesaurus.json"]

    def setUp(self):
        self.sut = Thesaurus(
            identifier="foo_name",
            title="GEMET - INSPIRE themes, version 1.0",
            date="2018-05-23T10:25:56",
            description="GEMET - INSPIRE themes, version 1.0",
            slug="",
            about="http://inspire.ec.europa.eu/theme",
        )
        self.tkeywords = ThesaurusKeyword.objects.all()

    def test_get_unique_thesaurus_list(self):
        actual = get_unique_thesaurus_set(self.tkeywords)
        self.assertSetEqual({1, 3}, actual)

    def test_get_thesaurus_title(self):
        tid = self.__get_last_thesaurus().id
        actual = get_thesaurus_title(tid)
        self.assertEqual(self.sut.title, actual)

    def test_get_thesaurus_date(self):
        tid = self.__get_last_thesaurus().id
        actual = get_thesaurus_date(tid)
        self.assertEqual(self.sut.date, actual)

    def test_get_name_translation_raise_exception_if_identifier_does_not_exists(self):
        with self.assertRaises(ObjectDoesNotExist):
            get_name_translation("foo_indentifier")

    @patch("geonode.base.templatetags.thesaurus.get_language")
    def test_get_name_translation_return_thesauro_title_if_label_for_selected_language_does_not_exists(self, lang):
        lang.return_value = "ke"
        actual = get_name_translation("inspire-theme")
        expected = "GEMET - INSPIRE themes, version 1.0"
        self.assertEqual(expected, actual)

    @patch("geonode.base.templatetags.thesaurus.get_language")
    def test_get_thesaurus_translation_by_id(self, lang):
        lang.return_value = "it"
        actual = get_thesaurus_translation_by_id(1)
        expected = "Tema GEMET - INSPIRE, versione 1.0"
        self.assertEqual(expected, actual)

    @patch("geonode.base.templatetags.thesaurus.get_language")
    def test_get_thesaurus_localized_label(self, lang):
        lang.return_value = "de"
        keyword = ThesaurusKeyword.objects.get(id=1)
        actual = get_thesaurus_localized_label(keyword)
        expected = "Adressen"
        self.assertEqual(expected, actual)

    @patch("geonode.base.templatetags.thesaurus.get_language")
    def test_get_name_translation_return_label_title_if_label_for_selected_language_exists(self, lang):
        lang.return_value = "it"
        actual = get_name_translation("inspire-theme")
        expected = "Tema GEMET - INSPIRE, versione 1.0"
        self.assertEqual(expected, actual)

    @staticmethod
    def __get_last_thesaurus():
        return Thesaurus.objects.all().order_by("id")[0]


class TestFacets(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test", email="test@test.com")
        Dataset.objects.update_or_create(
            name="test_boxes_vector",
            defaults=dict(
                uuid=str(uuid4()),
                owner=self.user,
                title="test_boxes",
                abstract="nothing",
                subtype="vector",
                is_approved=True,
            ),
        )
        Dataset.objects.update_or_create(
            name="test_1_vector",
            defaults=dict(
                uuid=str(uuid4()),
                owner=self.user,
                title="test_1",
                abstract="contains boxes",
                subtype="vector",
                is_approved=True,
            ),
        )
        Dataset.objects.update_or_create(
            name="test_2_vector",
            defaults=dict(
                uuid=str(uuid4()),
                owner=self.user,
                title="test_2",
                purpose="contains boxes",
                subtype="vector",
                is_approved=True,
            ),
        )
        Dataset.objects.update_or_create(
            name="test_3_vector",
            defaults=dict(uuid=str(uuid4()), owner=self.user, title="test_3", subtype="vector", is_approved=True),
        )
        Dataset.objects.update_or_create(
            name="test_boxes_vector",
            defaults=dict(
                uuid=str(uuid4()),
                owner=self.user,
                title="test_boxes",
                abstract="nothing",
                subtype="vector",
                is_approved=True,
            ),
        )
        Dataset.objects.update_or_create(
            name="test_1_raster",
            defaults=dict(
                uuid=str(uuid4()),
                owner=self.user,
                title="test_1",
                abstract="contains boxes",
                subtype="raster",
                is_approved=True,
            ),
        )
        Dataset.objects.update_or_create(
            name="test_2_raster",
            defaults=dict(
                uuid=str(uuid4()),
                owner=self.user,
                title="test_2",
                purpose="contains boxes",
                subtype="raster",
                is_approved=True,
            ),
        )
        Dataset.objects.update_or_create(
            name="test_boxes_raster",
            defaults=dict(uuid=str(uuid4()), owner=self.user, title="test_boxes", subtype="raster", is_approved=True),
        )

        self.request_mock = Mock(spec=requests.Request, GET=Mock())

    def test_facets_filter_datasets_returns_correctly(self):
        for _l in Dataset.objects.all():
            _l.set_default_permissions()
            _l.clear_dirty_state()
            _l.set_processing_state(enumerations.STATE_PROCESSED)
        self.request_mock.GET.get.side_effect = lambda key, self: {
            "title__icontains": "boxes",
            "abstract__icontains": "boxes",
            "purpose__icontains": "boxes",
            "date__gte": None,
            "date__range": None,
            "date__lte": None,
            "extent": None,
        }.get(key)
        self.request_mock.GET.getlist.return_value = None
        self.request_mock.user = self.user
        results = facets({"request": self.request_mock})
        self.assertEqual(results["vector"], 3)
        self.assertEqual(results["raster"], 3)


class TestGenerateThesaurusReference(TestCase):
    fixtures = ["test_thesaurus.json"]

    def setUp(self):
        self.site_url = settings.SITEURL if hasattr(settings, "SITEURL") else "http://localhost"

    """
    If the keyword.about does not exists, the url created will have a prefix and a specifier:
    as prefix:
        - use the Keyword's thesaurus.about URI if it exists,
        - otherwise use as prefix the geonode site URL composed with some thesaurus info: f'{settings.SITEURL}/thesaurus/{thesaurus.identifier}'
    as specifier:
        - we may use the ThesaurusKeyword.alt_label if it exists, otherwise its id

    So the final about field value will be composed as f'{prefix}#{specifier}'
    """

    def test_should_return_keyword_url(self):
        expected = "http://inspire.ec.europa.eu/theme/ad"
        keyword = ThesaurusKeyword.objects.get(id=1)
        actual = generate_thesaurus_reference(keyword)
        keyword.refresh_from_db()
        """
        Check if the expected about has been created and that the instance is correctly updated
        """
        self.assertEqual(expected, actual)
        self.assertEqual(expected, keyword.about)

    def test_should_return_as_url_thesaurus_about_and_keyword_alt_label(self):
        expected = "http://inspire.ec.europa.eu/theme#foo_keyword"
        keyword = ThesaurusKeyword.objects.get(alt_label="foo_keyword")
        actual = generate_thesaurus_reference(keyword)
        keyword.refresh_from_db()
        """
        Check if the expected about has been created and that the instance is correctly updated
        """
        self.assertEqual(expected, actual)
        self.assertEqual(expected, keyword.about)

    def test_should_return_as_url_thesaurus_about_and_keyword_id(self):
        expected = "http://inspire.ec.europa.eu/theme#37"
        keyword = ThesaurusKeyword.objects.get(id=37)
        actual = generate_thesaurus_reference(keyword)
        keyword.refresh_from_db()
        """
        Check if the expected about has been created and that the instance is correctly updated
        """
        self.assertEqual(expected, actual)
        self.assertEqual(expected, keyword.about)

    def test_should_return_as_url_site_url_and_keyword_label(self):
        expected = f"{self.site_url}/thesaurus/no-about-thesauro#bar_keyword"
        keyword = ThesaurusKeyword.objects.get(id=39)
        actual = generate_thesaurus_reference(keyword)
        keyword.refresh_from_db()
        """
        Check if the expected about has been created and that the instance is correctly updated
        """
        self.assertEqual(expected, actual)
        self.assertEqual(expected, keyword.about)

    def test_should_return_as_url_site_url_and_keyword_id(self):
        expected = f"{self.site_url}/thesaurus/no-about-thesauro#38"
        keyword = ThesaurusKeyword.objects.get(id=38)
        actual = generate_thesaurus_reference(keyword)
        keyword.refresh_from_db()
        """
        Check if the expected about has been created and that the instance is correctly updated
        """
        self.assertEqual(expected, actual)
        self.assertEqual(expected, keyword.about)


class TestHandleMetadataKeyword(TestCase):
    fixtures = ["test_thesaurus.json"]

    def setUp(self):
        self.keyword = [
            {
                "keywords": ["features", "test_dataset"],
                "thesaurus": {"date": None, "datetype": None, "title": None},
                "type": "theme",
            },
            {
                "keywords": ["no conditions to access and use"],
                "thesaurus": {
                    "date": "2020-10-30T16:58:34",
                    "datetype": "publication",
                    "title": "Test for ordering",
                },
                "type": None,
            },
            {
                "keywords": ["ad", "af"],
                "thesaurus": {
                    "date": "2008-06-01",
                    "datetype": "publication",
                    "title": "GEMET - INSPIRE themes, version 1.0",
                },
                "type": None,
            },
            {"keywords": ["Global"], "thesaurus": {"date": None, "datetype": None, "title": None}, "type": "place"},
        ]
        self.dataset = create_single_dataset("keyword-handler")
        self.sut = KeywordHandler(instance=self.dataset, keywords=self.keyword)

    def test_return_empty_if_keywords_is_an_empty_list(self):
        setattr(self.sut, "keywords", [])
        keyword, thesaurus_keyword = self.sut.handle_metadata_keywords()
        self.assertListEqual([], keyword)
        self.assertListEqual([], thesaurus_keyword)

    def test_should_return_the_expected_keyword_extracted_from_raw_and_the_thesaurus_keyword(self):
        keyword, thesaurus_keyword = self.sut.handle_metadata_keywords()
        self.assertSetEqual({"features", "test_dataset", "no conditions to access and use"}, set(keyword))
        self.assertListEqual(["ad", "af"], [x.alt_label for x in thesaurus_keyword])

    def test_should_assign_correclty_the_keyword_to_the_dataset_object(self):
        self.sut.set_keywords()
        current_keywords = [keyword.name for keyword in self.dataset.keywords.all()]
        current_tkeyword = [t.alt_label for t in self.dataset.tkeywords.all()]
        self.assertSetEqual({"features", "test_dataset", "no conditions to access and use"}, set(current_keywords))
        self.assertSetEqual({"ad", "af"}, set(current_tkeyword))

    def test_is_thesaurus_available_should_return_queryset_with_existing_thesaurus(self):
        keyword = "ad"
        thesaurus = {"title": "GEMET - INSPIRE themes, version 1.0"}
        actual = self.sut.is_thesaurus_available(thesaurus, keyword)
        self.assertEqual(1, len(actual))

    def test_is_thesaurus_available_should_return_empty_queryset_for_non_existing_thesaurus(self):
        keyword = "ad"
        thesaurus = {"title": "Random Thesaurus Title"}
        actual = self.sut.is_thesaurus_available(thesaurus, keyword)
        self.assertEqual(0, len(actual))


class Test_HierarchicalTagManager(GeoNodeBaseTestSupport):
    def setUp(self) -> None:
        self.sut = create_single_dataset(name="dataset_for_keyword")
        self.keyword = HierarchicalKeyword.objects.create(name="test_kw", slug="test_kw", depth=1)
        self.keyword.save()

    def tearDown(self) -> None:
        self.sut.keywords.remove(self.keyword)

    def test_keyword_are_correctly_saved(self):
        self.assertFalse(self.sut.keywords.exists())
        self.sut.keywords.add(self.keyword)
        self.assertTrue(self.sut.keywords.exists())

    @patch("django.db.models.query.QuerySet._fetch_all")
    def test_keyword_raise_integrity_error(self, keyword_fetch_method):
        keyword_fetch_method.side_effect = IntegrityError()
        logger = logging.getLogger("geonode.base.models")
        with self.assertLogs(logger, level="WARNING") as _log:
            self.sut.keywords.add(self.keyword)
        self.assertIn("The keyword provided already exists", [x.message for x in _log.records])

    @patch("geonode.base.models.HierarchicalKeyword.add_root")
    def test_keyword_raise_db_error(self, add_root_mocked):
        add_root_mocked.side_effect = OperationalError()
        logger = logging.getLogger("geonode.base.models")
        with self.assertLogs(logger) as _log:
            self.sut.keywords.add("keyword2")
        self.assertIn(
            "Error during the keyword creation for keyword: keyword2",
            [x.message for x in _log.records],
        )


class TestRegions(GeoNodeBaseTestSupport):
    def setUp(self):
        self.dataset_inside_region = GEOSGeometry(
            "POLYGON ((-4.01799226543944599 57.18451093931114571, 8.89409253052255622 56.91828238681708285, \
            9.29343535926363984 47.73339732577194638, -3.75176371294537603 48.13274015451304422,   \
            -4.01799226543944599 57.18451093931114571))",
            srid=4326,
        )

        self.dataset_overlapping_region = GEOSGeometry(
            "POLYGON ((15.28357779038003628 33.6232840435866791, 28.19566258634203848 33.35705549109261625, \
            28.5950054150831221 24.17217043004747978, 15.54980634287410624 24.57151325878857762, \
            15.28357779038003628 33.6232840435866791))",
            srid=4326,
        )

        self.dataset_outside_region = GEOSGeometry(
            "POLYGON ((-3.75176371294537603 23.10725622007123548, 9.16032108301662618 22.84102766757717262, \
            9.5596639117577098 13.65614260653203615, -3.48553516045130607 14.05548543527313399, \
            -3.75176371294537603 23.10725622007123548))",
            srid=4326,
        )

    def test_region_assignment_for_extent(self):
        region = Region.objects.get(code="EUR")

        self.assertTrue(
            region.is_assignable_to_geom(self.dataset_inside_region), "Extent inside a region shouldn't be assigned"
        )
        self.assertTrue(
            region.is_assignable_to_geom(self.dataset_overlapping_region),
            "Extent overlapping a region should be assigned",
        )
        self.assertFalse(
            region.is_assignable_to_geom(self.dataset_outside_region), "Extent outside a region should be assigned"
        )

    @override_settings(METADATA_STORERS=["geonode.resource.regions_storer.spatial_predicate_region_assignor"])
    def test_regions_are_assigned_if_handler_is_used(self):
        dataset = resource_manager.create(
            None,
            resource_type=Dataset,
            defaults=dict(owner=get_user_model().objects.first(), title="test_region_dataset", is_approved=True),
        )
        self.assertTrue(dataset.regions.exists())
        self.assertEqual(1, dataset.regions.count())
        self.assertEqual("Global", dataset.regions.first().name)


class LinkedResourcesTest(GeoNodeBaseTestSupport):
    def test_autocomplete_linked_resource(self):
        d = []
        try:
            user, _ = get_user_model().objects.get_or_create(username="admin")

            for t in ("dataset1", "dataset2", "other"):
                d.append(ResourceBase.objects.create(title=t, owner=user, is_approved=True, is_published=True))

            web_client = Client()
            web_client.force_login(user)
            url_name = "autocomplete_linked_resource"

            # get all resources
            response = web_client.get(reverse(url_name))
            rjson = response.json()

            self.assertEqual(response.status_code, 200, "Can not get autocomplete API")
            self.assertIn("results", rjson, "Can not find results")
            self.assertEqual(len(rjson["results"]), 3, "Unexpected results count")

            # filter by title
            response = web_client.get(
                reverse(url_name),
                data={
                    "q": "dataset",
                },
            )
            rjson = response.json()
            self.assertEqual(len(rjson["results"]), 2, "Unexpected results count")

            # filter by title, exclude
            response = web_client.get(
                reverse(url_name), data={"q": "dataset", "forward": json.dumps({"exclude": d[0].id})}
            )
            rjson = response.json()
            self.assertEqual(len(rjson["results"]), 1, "Unexpected results count")

        finally:
            for _ in d:
                _.delete()


class TestResourceBaseViewSetQueryset(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_user = get_user_model().objects.create_user(
            username="test_queryset_user", email="test@example.com", password="testpass123"
        )

        cls.admin_user = get_user_model().objects.create_user(
            username="admin_queryset_user", email="admin@example.com", password="adminpass123", is_staff=True
        )

        cls.test_resources = []
        for i in range(5):
            resource = ResourceBase.objects.create(
                title=f"test_resource_queryset_{i}",
                uuid=str(uuid4()),
                owner=cls.test_user if i % 2 == 0 else cls.admin_user,
                abstract=f"Test resource {i} for queryset",
                subtype="vector",
                is_approved=True,
                is_published=True,
            )
            cls.test_resources.append(resource)

    def test_original_queryset_vs_optimized_queryset(self):
        """Test that original and optimized querysets return the same results"""

        original_queryset = ResourceBase.objects.all().order_by("-created")

        optimized_queryset = ResourceBase.objects.select_related("owner").order_by("-created")

        original_list = list(original_queryset)
        optimized_list = list(optimized_queryset)

        self.assertEqual(len(original_list), len(optimized_list))

        self.assertEqual(original_list, optimized_list)

        original_pks = [obj.pk for obj in original_list]
        optimized_pks = [obj.pk for obj in optimized_list]
        self.assertEqual(original_pks, optimized_pks)
