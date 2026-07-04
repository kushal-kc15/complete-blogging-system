from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from blogs.models import Blog, Category, Contact
from dashboard.forms import AddUserForm, EditUserForm


class DashboardSecurityTests(TestCase):
    def setUp(self):
        self.ordinary_user = User.objects.create_user(
            username='reader', password='test-password'
        )
        self.staff_user = User.objects.create_user(
            username='editor', password='test-password', is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@example.com',
            password='test-password'
        )
        self.category = Category.objects.create(name='Security')
        self.post = Blog.objects.create(
            title='Test post', slug='test-post', category=self.category,
            author=self.staff_user, short_description='Description',
            blog_body='<p>Body</p>', status='published'
        )
        self.message = Contact.objects.create(
            name='Sender', email='sender@example.com', subject='Private',
            message='Private message'
        )

    def test_anonymous_user_cannot_access_dashboard(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('dashboard')}"
        )

    def test_ordinary_user_cannot_access_management_pages(self):
        self.client.force_login(self.ordinary_user)
        urls = [
            reverse('dashboard'), reverse('categories'), reverse('posts'),
            reverse('contact_messages'),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn(response.status_code, (302, 403))

    def test_ordinary_user_cannot_manage_users(self):
        self.client.force_login(self.ordinary_user)
        requests = [
            ('get', reverse('users'), None),
            ('post', reverse('add_user'), {'username': 'attacker'}),
            ('post', reverse('edit_user', args=[self.staff_user.id]),
             {'username': 'changed'}),
            ('post', reverse('delete_user', args=[self.staff_user.id]), {}),
        ]
        for method, url, data in requests:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, data=data)
                self.assertIn(response.status_code, (302, 403))
        self.assertTrue(User.objects.filter(pk=self.staff_user.pk).exists())

    def test_custom_user_forms_do_not_expose_privilege_fields(self):
        forbidden = {'is_staff', 'is_superuser', 'groups', 'user_permissions'}
        self.assertTrue(forbidden.isdisjoint(AddUserForm().fields))
        self.assertTrue(forbidden.isdisjoint(EditUserForm().fields))

    def test_delete_endpoints_reject_get(self):
        self.client.force_login(self.superuser)
        urls = [
            reverse('delete_category', args=[self.category.id]),
            reverse('delete_post', args=[self.post.id]),
            reverse('delete_user', args=[self.ordinary_user.id]),
            reverse('delete_message', args=[self.message.id]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)

    def test_contact_messages_are_not_visible_to_ordinary_users(self):
        self.client.force_login(self.ordinary_user)
        for url in (
            reverse('contact_messages'),
            reverse('view_message', args=[self.message.id]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_user_with_contact_permission_can_view_messages(self):
        permission = Permission.objects.get(
            codename='view_contact', content_type__app_label='blogs'
        )
        self.staff_user.user_permissions.add(permission)
        self.client.force_login(self.staff_user)
        self.assertEqual(self.client.get(reverse('contact_messages')).status_code, 200)
