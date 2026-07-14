from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.deletion import PROTECT, ProtectedError
from django.test import TestCase
from io import BytesIO
from PIL import Image
from django.urls import reverse

from blogs.models import Blog, Category, Comment, Contact
from dashboard.forms import AddUserForm, BlogForm, EditUserForm


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
        self.comment = Comment.objects.create(
            user=self.ordinary_user, blog=self.post, comment='Needs review'
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

    def test_superuser_user_forms_render_supported_fields_only(self):
        self.client.force_login(self.superuser)
        supported = ('username', 'first_name', 'last_name', 'email', 'is_active')
        forbidden = ('is_staff', 'is_superuser', 'groups', 'user_permissions')

        add_response = self.client.get(reverse('add_user'))
        edit_response = self.client.get(
            reverse('edit_user', args=[self.ordinary_user.id])
        )
        self.assertEqual(add_response.status_code, 200)
        self.assertEqual(edit_response.status_code, 200)
        for response in (add_response, edit_response):
            with self.subTest(path=response.request['PATH_INFO']):
                for field_name in supported:
                    self.assertContains(response, f'name="{field_name}"')
                for field_name in forbidden:
                    self.assertNotContains(response, f'name="{field_name}"')
                for label in ('Staff', 'Superuser', 'Groups', 'Permissions'):
                    self.assertNotContains(response, label)
        self.assertContains(add_response, 'name="password1"')
        self.assertContains(add_response, 'name="password2"')
        self.assertNotContains(edit_response, 'name="password1"')
        self.assertNotContains(edit_response, 'name="password2"')

    def test_non_superusers_cannot_open_user_forms(self):
        for user in (self.ordinary_user, self.staff_user):
            self.client.force_login(user)
            for url in (reverse('add_user'), reverse('edit_user', args=[self.superuser.id])):
                with self.subTest(user=user.username, url=url):
                    self.assertIn(self.client.get(url).status_code, (302, 403))

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

    def test_comment_moderation_is_not_visible_to_ordinary_users(self):
        self.client.force_login(self.ordinary_user)
        response = self.client.get(reverse('dashboard_comments'))
        self.assertIn(response.status_code, (302, 403))

    def test_comment_visibility_toggle_rejects_get(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(
            reverse('toggle_comment_visibility', args=[self.comment.id])
        )
        self.assertEqual(response.status_code, 405)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_visible)

    def test_staff_can_hide_and_restore_comment(self):
        self.client.force_login(self.staff_user)
        url = reverse('toggle_comment_visibility', args=[self.comment.id])
        self.client.post(url)
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_visible)
        self.client.post(url)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_visible)

    def test_user_with_contact_permission_can_view_messages(self):
        permission = Permission.objects.get(
            codename='view_contact', content_type__app_label='blogs'
        )
        self.staff_user.user_permissions.add(permission)
        self.client.force_login(self.staff_user)
        self.assertEqual(self.client.get(reverse('contact_messages')).status_code, 200)


class BlogFormImageValidationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Images')
        self.valid_data = {
            'title': 'Image post',
            'category': self.category.id,
            'short_description': 'Short description',
            'blog_body': '<p>Body</p>',
            'status': 'draft',
            'featured_image_alt': 'Useful image description',
            'meta_description': '',
        }

    def image_bytes(self, image_format='PNG'):
        image = Image.new('RGB', (1, 1), color='white')
        buffer = BytesIO()
        image.save(buffer, format=image_format)
        return buffer.getvalue()

    def test_rejects_unsupported_featured_image_type(self):
        upload = SimpleUploadedFile(
            'article.gif', self.image_bytes('GIF'), content_type='image/gif'
        )
        form = BlogForm(data=self.valid_data, files={'featured_image': upload})
        self.assertFalse(form.is_valid())
        self.assertIn('Upload a JPEG, PNG, or WebP image.', form.errors['featured_image'])

    def test_rejects_oversized_featured_image(self):
        upload = SimpleUploadedFile(
            'article.jpg',
            self.image_bytes('JPEG') + b'x' * BlogForm.MAX_FEATURED_IMAGE_SIZE,
            content_type='image/jpeg',
        )
        form = BlogForm(data=self.valid_data, files={'featured_image': upload})
        self.assertFalse(form.is_valid())
        self.assertIn('Featured image must be 3 MB or smaller.', form.errors['featured_image'])


class PostSlugGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='slug-admin',
            email='slug-admin@example.com',
            password='test-password',
        )
        self.category = Category.objects.create(name='Slugs')
        self.client.force_login(self.user)

    def create_post(self, title, status='draft'):
        response = self.client.post(
            reverse('add_post'),
            {
                'title': title,
                'category': self.category.id,
                'short_description': 'A slug test post.',
                'blog_body': '<p>Slug test body.</p>',
                'status': status,
                'featured_image_alt': '',
                'meta_description': '',
            },
        )
        self.assertRedirects(response, reverse('posts'))
        return Blog.objects.filter(title=title, status=status).order_by('-id').first()

    def test_duplicate_titles_receive_readable_sequential_slugs(self):
        first = self.create_post('My First Article', status='published')
        second = self.create_post('My First Article')
        third = self.create_post('My First Article')

        self.assertEqual(first.slug, 'my-first-article')
        self.assertEqual(second.slug, 'my-first-article-2')
        self.assertEqual(third.slug, 'my-first-article-3')
        self.assertEqual(
            self.client.get(reverse('Blog_detail', args=[first.slug])).status_code,
            200,
        )

    def test_empty_and_long_titles_receive_valid_bounded_slugs(self):
        fallback_post = self.create_post('!!!')
        long_title = 'a' * 200
        long_post = self.create_post(long_title)
        long_duplicate = self.create_post(long_title)

        max_length = Blog._meta.get_field('slug').max_length
        self.assertEqual(fallback_post.slug, 'post')
        self.assertLessEqual(len(long_post.slug), max_length)
        self.assertLessEqual(len(long_duplicate.slug), max_length)
        self.assertTrue(long_duplicate.slug.endswith('-2'))

    def test_draft_and_published_posts_share_slug_namespace(self):
        draft = self.create_post('Shared Title', status='draft')
        published = self.create_post('Shared Title', status='published')

        self.assertEqual(draft.slug, 'shared-title')
        self.assertEqual(published.slug, 'shared-title-2')
        self.assertEqual(
            self.client.get(reverse('Blog_detail', args=[published.slug])).status_code,
            200,
        )

    def test_editing_title_preserves_existing_slug(self):
        post = self.create_post('Original Title')
        response = self.client.post(
            reverse('edit_post', args=[post.id]),
            {
                'title': 'Changed Title',
                'category': self.category.id,
                'short_description': 'Updated summary.',
                'blog_body': '<p>Updated body.</p>',
                'status': 'draft',
                'featured_image_alt': '',
                'meta_description': '',
            },
        )

        self.assertRedirects(response, reverse('posts'))
        post.refresh_from_db()
        self.assertEqual(post.slug, 'original-title')


class DashboardPostPaginationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='pagination-admin',
            email='pagination-admin@example.com',
            password='test-password',
        )
        self.category = Category.objects.create(name='Pagination')
        self.client.force_login(self.user)

    def create_posts(self, count):
        return [
            Blog.objects.create(
                title=f'Post {index}',
                slug=f'pagination-post-{index}',
                category=self.category,
                author=self.user,
                short_description='Description',
                blog_body='<p>Body</p>',
                status='draft',
            )
            for index in range(count)
        ]

    def test_posts_are_paginated_in_existing_order(self):
        posts = self.create_posts(7)
        response = self.client.get(reverse('posts'))

        page = response.context['posts']
        self.assertEqual(page.paginator.per_page, 6)
        self.assertEqual(page.paginator.count, 7)
        self.assertEqual(list(page.object_list), list(Blog.objects.order_by('-updated_at')[:6]))
        self.assertContains(response, 'Next')
        self.assertNotContains(response, 'Previous')
        self.assertContains(response, page.object_list[0].title)
        self.assertContains(response, reverse('edit_post', args=[page.object_list[0].id]))
        self.assertContains(response, reverse('delete_post', args=[page.object_list[0].id]))

        second_response = self.client.get(f"{reverse('posts')}?page=2")
        second_page = second_response.context['posts']
        self.assertEqual(second_page.number, 2)
        self.assertEqual(len(second_page.object_list), 1)
        self.assertContains(second_response, 'Previous')
        self.assertNotContains(second_response, 'Next')
        self.assertNotEqual(
            {post.id for post in page.object_list},
            {post.id for post in second_page.object_list},
        )

    def test_invalid_and_out_of_range_pages_are_safe(self):
        self.create_posts(7)
        for page in ('invalid', '9999'):
            with self.subTest(page=page):
                response = self.client.get(f"{reverse('posts')}?page={page}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['posts'].number, 1 if page == 'invalid' else 2)

    def test_empty_post_list_keeps_empty_state(self):
        response = self.client.get(reverse('posts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No posts found')
        self.assertNotContains(response, 'Page 1 of')


class DashboardCommentPaginationTests(TestCase):
    def setUp(self):
        self.moderator = User.objects.create_user(
            username='comment-moderator', password='test-password', is_staff=True
        )
        self.author = User.objects.create_user(
            username='comment-author', password='test-password'
        )
        category = Category.objects.create(name='Comment pagination')
        self.post = Blog.objects.create(
            title='Moderated post', slug='moderated-post', category=category,
            author=self.author, short_description='Description',
            blog_body='<p>Body</p>', status='published'
        )
        self.client.force_login(self.moderator)

    def create_comments(self, count):
        return [
            Comment.objects.create(
                user=self.author, blog=self.post, comment=f'Comment {index}'
            )
            for index in range(count)
        ]

    def test_comments_are_paginated_with_existing_order_and_actions(self):
        self.create_comments(11)
        response = self.client.get(reverse('dashboard_comments'))
        page = response.context['comments']

        self.assertEqual(page.paginator.per_page, 10)
        self.assertEqual(page.paginator.count, 11)
        self.assertEqual(
            [comment.id for comment in page.object_list],
            [comment.id for comment in Comment.objects.order_by('-created_at')[:10]],
        )
        self.assertContains(response, 'Next')
        self.assertNotContains(response, 'Previous')
        self.assertContains(
            response,
            reverse('toggle_comment_visibility', args=[page.object_list[0].id]),
        )

        second_response = self.client.get(f"{reverse('dashboard_comments')}?page=2")
        second_page = second_response.context['comments']
        self.assertEqual(len(second_page.object_list), 1)
        self.assertContains(second_response, 'Previous')
        self.assertNotContains(second_response, 'Next')
        self.assertTrue(
            {comment.id for comment in page.object_list}.isdisjoint(
                comment.id for comment in second_page.object_list
            )
        )

    def test_invalid_and_out_of_range_comment_pages_are_safe(self):
        self.create_comments(11)
        for page_number in ('invalid', '9999'):
            with self.subTest(page=page_number):
                response = self.client.get(
                    f"{reverse('dashboard_comments')}?page={page_number}"
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['comments'].number, 1 if page_number == 'invalid' else 2)

    def test_empty_comment_list_keeps_empty_state(self):
        response = self.client.get(reverse('dashboard_comments'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No comments yet')
        self.assertNotContains(response, 'Page 1 of')


class DashboardContactMessagePaginationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='message-admin', email='message-admin@example.com',
            password='test-password',
        )
        self.client.force_login(self.admin)

    def create_messages(self, count):
        return [
            Contact.objects.create(
                name=f'Sender {index}',
                email=f'sender{index}@example.com',
                subject=f'Subject {index}',
                message=f'Message {index}',
            )
            for index in range(count)
        ]

    def test_messages_are_paginated_in_existing_order_with_actions(self):
        self.create_messages(11)
        response = self.client.get(reverse('contact_messages'))
        page = response.context['messages']

        self.assertEqual(page.paginator.per_page, 10)
        self.assertEqual(page.paginator.count, 11)
        self.assertEqual(
            [message.id for message in page.object_list],
            [message.id for message in Contact.objects.order_by('-created_at')[:10]],
        )
        self.assertContains(response, 'New')
        self.assertContains(response, reverse('view_message', args=[page.object_list[0].id]))
        self.assertContains(response, reverse('delete_message', args=[page.object_list[0].id]))
        self.assertContains(response, 'Next')
        self.assertNotContains(response, 'Previous')

        second_response = self.client.get(f"{reverse('contact_messages')}?page=2")
        second_page = second_response.context['messages']
        self.assertEqual(len(second_page.object_list), 1)
        self.assertContains(second_response, 'Previous')
        self.assertNotContains(second_response, 'Next')
        self.assertTrue(
            {message.id for message in page.object_list}.isdisjoint(
                message.id for message in second_page.object_list
            )
        )

    def test_invalid_and_out_of_range_message_pages_are_safe(self):
        self.create_messages(11)
        for page_number in ('invalid', '9999'):
            with self.subTest(page=page_number):
                response = self.client.get(
                    f"{reverse('contact_messages')}?page={page_number}"
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['messages'].number, 1 if page_number == 'invalid' else 2)

    def test_empty_message_inbox_keeps_empty_state(self):
        response = self.client.get(reverse('contact_messages'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No messages found')
        self.assertNotContains(response, 'Page 1 of')


class ContactMessageReadStateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='read-admin', email='read-admin@example.com',
            password='test-password',
        )
        self.message = Contact.objects.create(
            name='Reader', email='reader@example.com', subject='Unread',
            message='Private content',
        )

    def test_message_get_is_read_only_and_shows_mark_read_form(self):
        self.client.force_login(self.admin)
        url = reverse('view_message', args=[self.message.id])
        for _ in range(2):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Mark as read')
            self.assertContains(response, 'csrfmiddlewaretoken')
            self.message.refresh_from_db()
            self.assertFalse(self.message.is_read)

    def test_mark_read_is_post_only_authorized_and_idempotent(self):
        self.client.force_login(self.admin)
        mark_url = reverse('mark_message_read', args=[self.message.id])
        self.assertEqual(self.client.get(mark_url).status_code, 405)

        response = self.client.post(mark_url)
        self.assertRedirects(response, reverse('view_message', args=[self.message.id]))
        self.message.refresh_from_db()
        self.assertTrue(self.message.is_read)

        response = self.client.post(mark_url)
        self.assertRedirects(response, reverse('view_message', args=[self.message.id]))
        self.assertNotContains(self.client.get(reverse('view_message', args=[self.message.id])), 'Mark as read')

    def test_unauthorized_users_cannot_mark_message_read(self):
        ordinary_user = User.objects.create_user(
            username='read-reader', password='test-password'
        )
        mark_url = reverse('mark_message_read', args=[self.message.id])
        self.client.force_login(ordinary_user)
        self.assertEqual(self.client.post(mark_url).status_code, 403)
        self.message.refresh_from_db()
        self.assertFalse(self.message.is_read)

        self.client.logout()
        self.assertEqual(self.client.post(mark_url).status_code, 302)

    def test_missing_message_returns_404(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('mark_message_read', args=[999999]))
        self.assertEqual(response.status_code, 404)
        self.message.refresh_from_db()
        self.assertFalse(self.message.is_read)


class DashboardUserPaginationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='user-page-admin', email='user-page-admin@example.com',
            password='test-password',
        )
        self.client.force_login(self.admin)

    def create_users(self, count):
        return [
            User.objects.create_user(
                username=f'page-user-{index}',
                email=f'page-user-{index}@example.com',
                password='test-password',
            )
            for index in range(count)
        ]

    def test_users_are_paginated_with_existing_order_and_actions(self):
        self.create_users(11)
        response = self.client.get(reverse('users'))
        page = response.context['users']

        self.assertEqual(page.paginator.per_page, 10)
        self.assertEqual(page.paginator.count, 12)
        self.assertEqual(
            [user.id for user in page.object_list],
            [user.id for user in User.objects.order_by('id')[:10]],
        )
        self.assertContains(response, 'Next')
        self.assertNotContains(response, 'Previous')
        self.assertContains(response, reverse('edit_user', args=[page.object_list[0].id]))
        self.assertContains(response, reverse('delete_user', args=[page.object_list[0].id]))

        second_response = self.client.get(f"{reverse('users')}?page=2")
        second_page = second_response.context['users']
        self.assertEqual(len(second_page.object_list), 2)
        self.assertContains(second_response, 'Previous')
        self.assertNotContains(second_response, 'Next')
        self.assertTrue(
            {user.id for user in page.object_list}.isdisjoint(
                user.id for user in second_page.object_list
            )
        )

    def test_invalid_and_out_of_range_user_pages_are_safe(self):
        self.create_users(11)
        for page_number in ('invalid', '9999'):
            with self.subTest(page=page_number):
                response = self.client.get(
                    f"{reverse('users')}?page={page_number}"
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['users'].number, 1 if page_number == 'invalid' else 2)

    def test_minimal_user_list_renders_without_pagination_controls(self):
        response = self.client.get(reverse('users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.admin.username)
        self.assertNotContains(response, 'Page 1 of')


class CategoryDeletionSafetyTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='category-admin', email='category-admin@example.com',
            password='test-password',
        )
        self.client.force_login(self.admin)

    def create_post(self, category, title='Protected post', status='published'):
        return Blog.objects.create(
            title=title,
            slug=title.lower().replace(' ', '-'),
            category=category,
            author=self.admin,
            short_description='Description',
            blog_body='<p>Body</p>',
            status=status,
        )

    def test_blog_category_uses_protect(self):
        field = Blog._meta.get_field('category')
        self.assertIs(field.remote_field.on_delete, PROTECT)

    def test_unused_category_can_be_deleted(self):
        category = Category.objects.create(name='Unused category')
        response = self.client.post(reverse('delete_category', args=[category.id]))

        self.assertRedirects(response, reverse('categories'))
        self.assertFalse(Category.objects.filter(pk=category.id).exists())

    def test_used_categories_cannot_be_deleted_and_posts_are_preserved(self):
        for status in ('published', 'draft'):
            category = Category.objects.create(name=f'{status} category')
            post = self.create_post(category, f'{status} protected post', status)

            with self.subTest(status=status):
                response = self.client.post(
                    reverse('delete_category', args=[category.id]), follow=True
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    'This category cannot be deleted because it is being used by one or more posts.',
                )
                self.assertTrue(Category.objects.filter(pk=category.id).exists())
                self.assertTrue(Blog.objects.filter(pk=post.id).exists())

    def test_direct_orm_deletion_of_used_category_raises_protected_error(self):
        category = Category.objects.create(name='ORM protected category')
        post = self.create_post(category, 'ORM protected post')

        with self.assertRaises(ProtectedError):
            category.delete()

        self.assertTrue(Category.objects.filter(pk=category.id).exists())
        self.assertTrue(Blog.objects.filter(pk=post.id).exists())


class UserDeletionSafetyTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='user-delete-admin', email='user-delete-admin@example.com',
            password='test-password',
        )
        self.author = User.objects.create_user(
            username='post-author', password='test-password'
        )
        self.category = Category.objects.create(name='User deletion safety')
        self.client.force_login(self.admin)

    def create_post(self, title, status='published'):
        return Blog.objects.create(
            title=title,
            slug=title.lower().replace(' ', '-'),
            category=self.category,
            author=self.author,
            short_description='Description',
            blog_body='<p>Body</p>',
            status=status,
        )

    def test_blog_author_uses_protect(self):
        field = Blog._meta.get_field('author')
        self.assertIs(field.remote_field.on_delete, PROTECT)

    def test_user_without_posts_can_be_deleted(self):
        user = User.objects.create_user(username='no-posts', password='test-password')
        response = self.client.post(reverse('delete_user', args=[user.id]))

        self.assertRedirects(response, reverse('users'))
        self.assertFalse(User.objects.filter(pk=user.id).exists())

    def test_authored_posts_block_dashboard_deletion_and_preserve_data(self):
        posts = [
            self.create_post('Published author post', 'published'),
            self.create_post('Draft author post', 'draft'),
        ]
        response = self.client.post(
            reverse('delete_user', args=[self.author.id]), follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'This user cannot be deleted because they are the author of one or more posts.',
        )
        self.assertTrue(User.objects.filter(pk=self.author.id).exists())
        for post in posts:
            post.refresh_from_db()
            self.assertEqual(post.author_id, self.author.id)

    def test_direct_orm_deletion_of_author_raises_protected_error(self):
        post = self.create_post('Direct ORM author post')

        with self.assertRaises(ProtectedError):
            self.author.delete()

        self.assertTrue(User.objects.filter(pk=self.author.id).exists())
        post.refresh_from_db()
        self.assertEqual(post.author_id, self.author.id)
