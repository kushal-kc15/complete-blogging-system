import os
import random

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from blogs.models import Category, Blog, UserProfile
from django.utils.text import slugify


class Command(BaseCommand):
    help = (
        'Populate the database with sample content: categories, sample '
        'authors, and blog posts. This command never creates a default '
        'admin account with a hardcoded password. To provision a superuser '
        'for this sample data, set the DJANGO_ADMIN_USERNAME, '
        'DJANGO_ADMIN_EMAIL, and DJANGO_ADMIN_PASSWORD environment '
        'variables before running this command, or create one separately '
        'with "python manage.py createsuperuser".'
    )

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')

        # Optionally create a superuser, but only from credentials supplied
        # via environment variables. No default/hardcoded admin account is
        # created, and no password is ever printed to the console.
        admin_username = os.environ.get('DJANGO_ADMIN_USERNAME', '').strip()
        admin_email = os.environ.get('DJANGO_ADMIN_EMAIL', '').strip()
        admin_password = os.environ.get('DJANGO_ADMIN_PASSWORD', '').strip()

        admin = None
        if admin_username and admin_email and admin_password:
            admin, admin_created = User.objects.get_or_create(
                username=admin_username,
                defaults={'email': admin_email},
            )
            if admin_created:
                admin.set_password(admin_password)
                admin.is_staff = True
                admin.is_superuser = True
                admin.save()
                UserProfile.objects.get_or_create(
                    user=admin, defaults={'bio': 'Site Administrator'})
                self.stdout.write(self.style.SUCCESS(
                    f'Created admin user "{admin_username}" from '
                    'environment variables.'))
            else:
                self.stdout.write(
                    f'Admin user "{admin_username}" already exists; '
                    'skipping creation.'
                )
        else:
            self.stdout.write(
                'Skipping admin user creation: set DJANGO_ADMIN_USERNAME, '
                'DJANGO_ADMIN_EMAIL, and DJANGO_ADMIN_PASSWORD environment '
                'variables to create one here, or run '
                '"python manage.py createsuperuser" separately.'
            )

        # Create sample users
        users_data = [
            {'username': 'john_doe', 'email': 'john@example.com',
                'first_name': 'John', 'last_name': 'Doe'},
            {'username': 'jane_smith', 'email': 'jane@example.com',
                'first_name': 'Jane', 'last_name': 'Smith'},
            {'username': 'mike_wilson', 'email': 'mike@example.com',
                'first_name': 'Mike', 'last_name': 'Wilson'},
        ]

        authors = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                UserProfile.objects.create(
                    user=user, bio=f"I'm {user_data['first_name']}, a passionate blogger.")
                self.stdout.write(f"Created user: {user_data['username']}")
            authors.append(user)

        # Include the admin user as a potential author only if one was
        # created above from environment-supplied credentials.
        if admin is not None:
            authors.append(admin)

        # Create Categories
        categories_data = [
            'Technology',
            'Programming',
            'Web Development',
            'Data Science',
            'Artificial Intelligence',
            'DevOps',
            'Mobile Development',
            'Cybersecurity',
            'Cloud Computing',
            'Software Engineering',
        ]

        categories = []
        for cat_name in categories_data:
            cat, created = Category.objects.get_or_create(name=cat_name)
            categories.append(cat)
            if created:
                self.stdout.write(f"Created category: {cat_name}")

        # Create Blog Posts
        blog_posts = [
            {
                'title': 'Getting Started with Django: A Complete Beginner Guide',
                'short_description': 'Learn the basics of Django web framework. This comprehensive guide covers installation, project setup, and building your first web application.',
                'blog_body': '''
                <h2>Introduction to Django</h2>
                <p>Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design. Built by experienced developers, it takes care of much of the hassle of web development.</p>
                
                <h3>Why Choose Django?</h3>
                <ul>
                    <li><strong>Fast:</strong> Django was designed to help developers take applications from concept to completion quickly.</li>
                    <li><strong>Secure:</strong> Django takes security seriously and helps developers avoid many common security mistakes.</li>
                    <li><strong>Scalable:</strong> Some of the busiest sites on the web leverage Django's ability to quickly and flexibly scale.</li>
                </ul>
                
                <h3>Installation</h3>
                <p>To install Django, simply run:</p>
                <pre><code>pip install django</code></pre>
                
                <h3>Creating Your First Project</h3>
                <p>Once installed, you can create a new project with:</p>
                <pre><code>django-admin startproject myproject</code></pre>
                
                <p>This will create a directory structure with all the files you need to get started.</p>
                
                <h3>Conclusion</h3>
                <p>Django is an excellent choice for web development. Its batteries-included approach means you can focus on building your application rather than reinventing the wheel.</p>
                ''',
                'category': 'Web Development',
                'tags': ['Python', 'Django', 'Tutorial', 'Beginner'],
                'is_featured': True,
            },
            {
                'title': 'Python Machine Learning: Building Your First Model',
                'short_description': 'Discover how to build machine learning models with Python. Step-by-step tutorial using scikit-learn for classification and regression.',
                'blog_body': '''
                <h2>Introduction to Machine Learning with Python</h2>
                <p>Machine learning is transforming industries across the globe. With Python and libraries like scikit-learn, you can start building ML models today.</p>
                
                <h3>What is Machine Learning?</h3>
                <p>Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.</p>
                
                <h3>Setting Up Your Environment</h3>
                <pre><code>pip install numpy pandas scikit-learn matplotlib</code></pre>
                
                <h3>Your First Classification Model</h3>
                <p>Let's build a simple classifier using the iris dataset:</p>
                <pre><code>from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# Load data
iris = load_iris()
X_train, X_test, y_train, y_test = train_test_split(iris.data, iris.target)

# Train model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Evaluate
print(f"Accuracy: {model.score(X_test, y_test)}")</code></pre>
                
                <h3>Conclusion</h3>
                <p>This is just the beginning of your machine learning journey. Keep practicing and exploring different algorithms!</p>
                ''',
                'category': 'Data Science',
                'tags': ['Python', 'Machine Learning', 'Tutorial', 'Beginner'],
                'is_featured': True,
            },
            {
                'title': 'Docker for Developers: Containerization Made Simple',
                'short_description': 'Master Docker containerization. Learn to build, ship, and run applications in containers for consistent development environments.',
                'blog_body': '''
                <h2>Understanding Docker</h2>
                <p>Docker is a platform for developing, shipping, and running applications in containers. Containers are lightweight, standalone packages that include everything needed to run software.</p>
                
                <h3>Why Use Docker?</h3>
                <ul>
                    <li>Consistent environments across development, testing, and production</li>
                    <li>Isolation of applications and dependencies</li>
                    <li>Easy scaling and deployment</li>
                    <li>Reduced "it works on my machine" problems</li>
                </ul>
                
                <h3>Basic Docker Commands</h3>
                <pre><code># Pull an image
docker pull python:3.9

# Run a container
docker run -it python:3.9 bash

# List running containers
docker ps

# Build an image
docker build -t myapp .</code></pre>
                
                <h3>Creating a Dockerfile</h3>
                <pre><code>FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]</code></pre>
                
                <p>Start containerizing your applications today!</p>
                ''',
                'category': 'DevOps',
                'tags': ['Docker', 'DevOps', 'Tutorial', 'Best Practices'],
                'is_featured': False,
            },
            {
                'title': 'Building REST APIs with Django REST Framework',
                'short_description': 'Create powerful REST APIs using Django REST Framework. Complete guide with authentication, serializers, and viewsets.',
                'blog_body': '''
                <h2>Django REST Framework Overview</h2>
                <p>Django REST Framework (DRF) is a powerful toolkit for building Web APIs. It provides authentication, serialization, and many other features out of the box.</p>
                
                <h3>Installation</h3>
                <pre><code>pip install djangorestframework</code></pre>
                
                <h3>Creating a Serializer</h3>
                <pre><code>from rest_framework import serializers
from .models import Article

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'created_at']</code></pre>
                
                <h3>Creating Views</h3>
                <pre><code>from rest_framework import viewsets
from .models import Article
from .serializers import ArticleSerializer

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer</code></pre>
                
                <h3>Authentication</h3>
                <p>DRF supports various authentication methods including Token, JWT, and OAuth2.</p>
                
                <p>Start building your APIs with confidence!</p>
                ''',
                'category': 'Web Development',
                'tags': ['Python', 'Django', 'REST API', 'Tutorial'],
                'is_featured': False,
            },
            {
                'title': 'React Hooks: A Complete Guide for Modern React Development',
                'short_description': 'Master React Hooks with practical examples. Learn useState, useEffect, useContext, and custom hooks for cleaner code.',
                'blog_body': '''
                <h2>Introduction to React Hooks</h2>
                <p>React Hooks let you use state and other React features without writing a class. They were introduced in React 16.8.</p>
                
                <h3>useState Hook</h3>
                <pre><code>import { useState } from 'react';

function Counter() {
    const [count, setCount] = useState(0);
    
    return (
        &lt;button onClick={() => setCount(count + 1)}&gt;
            Count: {count}
        &lt;/button&gt;
    );
}</code></pre>
                
                <h3>useEffect Hook</h3>
                <pre><code>import { useEffect, useState } from 'react';

function DataFetcher() {
    const [data, setData] = useState(null);
    
    useEffect(() => {
        fetch('/api/data')
            .then(res => res.json())
            .then(setData);
    }, []);
    
    return &lt;div&gt;{JSON.stringify(data)}&lt;/div&gt;;
}</code></pre>
                
                <h3>Custom Hooks</h3>
                <p>You can create your own hooks to reuse stateful logic between components.</p>
                
                <p>Hooks make your React code cleaner and more reusable!</p>
                ''',
                'category': 'Programming',
                'tags': ['JavaScript', 'React', 'Tutorial', 'Tips'],
                'is_featured': True,
            },
            {
                'title': 'AWS for Beginners: Cloud Computing Fundamentals',
                'short_description': 'Start your cloud journey with AWS. Learn about EC2, S3, RDS, and other essential AWS services for developers.',
                'blog_body': '''
                <h2>What is AWS?</h2>
                <p>Amazon Web Services (AWS) is the world's most comprehensive cloud platform, offering over 200 fully featured services from data centers globally.</p>
                
                <h3>Core AWS Services</h3>
                <ul>
                    <li><strong>EC2:</strong> Virtual servers in the cloud</li>
                    <li><strong>S3:</strong> Scalable object storage</li>
                    <li><strong>RDS:</strong> Managed relational databases</li>
                    <li><strong>Lambda:</strong> Serverless compute</li>
                    <li><strong>CloudFront:</strong> Content delivery network</li>
                </ul>
                
                <h3>Getting Started</h3>
                <p>Create a free tier account at aws.amazon.com and explore the console. AWS offers 12 months of free tier access to many services.</p>
                
                <h3>Best Practices</h3>
                <ul>
                    <li>Enable MFA on your root account</li>
                    <li>Use IAM users instead of root</li>
                    <li>Set up billing alerts</li>
                    <li>Use regions close to your users</li>
                </ul>
                
                <p>Cloud computing is the future - start learning today!</p>
                ''',
                'category': 'Cloud Computing',
                'tags': ['AWS', 'Tutorial', 'Beginner', 'Best Practices'],
                'is_featured': False,
            },
            {
                'title': 'Git Best Practices for Team Collaboration',
                'short_description': 'Learn Git workflows and best practices for effective team collaboration. Branching strategies, commit messages, and code reviews.',
                'blog_body': '''
                <h2>Git for Teams</h2>
                <p>Git is essential for modern software development. When working in teams, following best practices ensures smooth collaboration.</p>
                
                <h3>Branching Strategy</h3>
                <p>Use a consistent branching strategy like Git Flow or GitHub Flow:</p>
                <ul>
                    <li><strong>main:</strong> Production-ready code</li>
                    <li><strong>develop:</strong> Integration branch</li>
                    <li><strong>feature/*:</strong> New features</li>
                    <li><strong>hotfix/*:</strong> Emergency fixes</li>
                </ul>
                
                <h3>Commit Message Guidelines</h3>
                <pre><code>feat: add user authentication
fix: resolve login redirect issue
docs: update API documentation
refactor: simplify database queries</code></pre>
                
                <h3>Pull Request Tips</h3>
                <ul>
                    <li>Keep PRs small and focused</li>
                    <li>Write descriptive titles and descriptions</li>
                    <li>Request reviews from relevant team members</li>
                    <li>Address feedback promptly</li>
                </ul>
                
                <p>Good Git practices lead to better code and happier teams!</p>
                ''',
                'category': 'Software Engineering',
                'tags': ['Git', 'Best Practices', 'Tips', 'Tutorial'],
                'is_featured': False,
            },
            {
                'title': 'PostgreSQL Performance Tuning: Advanced Optimization',
                'short_description': 'Optimize your PostgreSQL database for maximum performance. Indexing strategies, query optimization, and configuration tuning.',
                'blog_body': '''
                <h2>PostgreSQL Performance</h2>
                <p>PostgreSQL is a powerful database, but like any database, it requires proper tuning for optimal performance.</p>
                
                <h3>Indexing Strategies</h3>
                <pre><code>-- B-tree index (default)
CREATE INDEX idx_users_email ON users(email);

-- Partial index
CREATE INDEX idx_active_users ON users(id) WHERE active = true;

-- Composite index
CREATE INDEX idx_orders_user_date ON orders(user_id, created_at DESC);</code></pre>
                
                <h3>Query Optimization</h3>
                <ul>
                    <li>Use EXPLAIN ANALYZE to understand query plans</li>
                    <li>Avoid SELECT * - specify only needed columns</li>
                    <li>Use appropriate JOINs</li>
                    <li>Consider query caching</li>
                </ul>
                
                <h3>Configuration Tuning</h3>
                <pre><code># postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 64MB
maintenance_work_mem = 128MB</code></pre>
                
                <p>Regular monitoring and tuning keeps your database running smoothly!</p>
                ''',
                'category': 'Technology',
                'tags': ['PostgreSQL', 'Performance', 'Advanced', 'Best Practices'],
                'is_featured': False,
            },
            {
                'title': 'Kubernetes Deployment: From Zero to Production',
                'short_description': 'Deploy applications to Kubernetes like a pro. Learn pods, services, deployments, and production best practices.',
                'blog_body': '''
                <h2>Kubernetes Essentials</h2>
                <p>Kubernetes (K8s) is the leading container orchestration platform. It automates deployment, scaling, and management of containerized applications.</p>
                
                <h3>Core Concepts</h3>
                <ul>
                    <li><strong>Pod:</strong> Smallest deployable unit</li>
                    <li><strong>Service:</strong> Network abstraction for pods</li>
                    <li><strong>Deployment:</strong> Manages pod replicas</li>
                    <li><strong>Ingress:</strong> External access to services</li>
                </ul>
                
                <h3>Sample Deployment</h3>
                <pre><code>apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 8080</code></pre>
                
                <h3>kubectl Commands</h3>
                <pre><code>kubectl apply -f deployment.yaml
kubectl get pods
kubectl logs pod-name
kubectl scale deployment myapp --replicas=5</code></pre>
                
                <p>Master Kubernetes to level up your DevOps skills!</p>
                ''',
                'category': 'DevOps',
                'tags': ['Kubernetes', 'Docker', 'DevOps', 'Advanced'],
                'is_featured': False,
            },
            {
                'title': 'Web Security Essentials: Protecting Your Applications',
                'short_description': 'Learn essential web security practices. Protect against XSS, CSRF, SQL injection, and other common vulnerabilities.',
                'blog_body': '''
                <h2>Web Application Security</h2>
                <p>Security should be a priority from day one. Understanding common vulnerabilities helps you build more secure applications.</p>
                
                <h3>Common Vulnerabilities</h3>
                <ul>
                    <li><strong>XSS:</strong> Cross-Site Scripting</li>
                    <li><strong>CSRF:</strong> Cross-Site Request Forgery</li>
                    <li><strong>SQL Injection:</strong> Database attacks</li>
                    <li><strong>Authentication flaws:</strong> Weak passwords, session hijacking</li>
                </ul>
                
                <h3>Prevention Strategies</h3>
                <pre><code># Always escape user input
from django.utils.html import escape
safe_text = escape(user_input)

# Use parameterized queries
cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])

# Enable CSRF protection
{% csrf_token %}</code></pre>
                
                <h3>Security Headers</h3>
                <pre><code>Content-Security-Policy: default-src 'self'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000</code></pre>
                
                <p>Security is everyone's responsibility. Stay vigilant!</p>
                ''',
                'category': 'Cybersecurity',
                'tags': ['Security', 'Best Practices', 'Tutorial', 'Tips'],
                'is_featured': False,
            },
        ]

        # Create blog posts
        for idx, post_data in enumerate(blog_posts):
            category = Category.objects.get(name=post_data['category'])
            slug = slugify(post_data['title']) + \
                f'-{random.randint(1000, 9999)}'

            blog, created = Blog.objects.get_or_create(
                title=post_data['title'],
                defaults={
                    'slug': slug,
                    'category': category,
                    'author': random.choice(authors),
                    'blog_body': post_data['blog_body'],
                    'short_description': post_data['short_description'],
                    'status': 'published',
                    'is_featured': post_data['is_featured'],
                    'views': random.randint(50, 500),
                    'meta_description': post_data['short_description'][:160],
                }
            )

            if created:
                self.stdout.write(
                    f"Created blog post: {post_data['title'][:50]}...")

        self.stdout.write(self.style.SUCCESS(
            '\n✓ Sample data created successfully!'))
        self.stdout.write(self.style.SUCCESS(
            'Sample user accounts were created (e.g. "john_doe") with the '
            'password "password123" for local development only. No '
            'passwords are ever printed for admin accounts by this '
            'command.'
        ))
        if admin is None:
            self.stdout.write(
                'No admin user was created. Run '
                '"python manage.py createsuperuser" to create one.'
            )
