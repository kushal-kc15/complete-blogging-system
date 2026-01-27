# ✨ InkSpire - Modern Blogging Platform

<p align="center">
  <img src="https://img.shields.io/badge/Django-6.0-green?style=for-the-badge&logo=django" alt="Django">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Bootstrap-5.0-purple?style=for-the-badge&logo=bootstrap" alt="Bootstrap">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

<p align="center">
  <strong>A feature-rich, production-ready blogging platform built with Django</strong>
</p>

---

## 🚀 Features

### Core Features
- ✅ **Rich Text Editor** - CKEditor 5 with image uploads, code blocks, and formatting
- ✅ **User Authentication** - Registration, login, logout, password change
- ✅ **User Profiles** - Customizable profiles with avatars, bio, and social links
- ✅ **Categories** - Organize posts by categories
- ✅ **Featured Posts** - Highlight important content

### Engagement Features
- ❤️ **Likes** - Users can like posts
- 🔖 **Bookmarks** - Save posts for later reading
- 💬 **Nested Comments** - Threaded comment system with replies
- 👁️ **View Count** - Track post popularity
- ⏱️ **Reading Time** - Automatic reading time calculation

### SEO & Marketing
- 🔍 **SEO Meta Tags** - Custom meta descriptions for each post
- 📡 **RSS Feed** - Syndicate your content
- 🗺️ **XML Sitemap** - Search engine friendly
- 🔗 **Social Sharing** - Share to Twitter, Facebook, LinkedIn, WhatsApp
- 📧 **Contact Form** - Built-in contact form with dashboard management

### Dashboard
- 📊 **Admin Dashboard** - Manage posts, categories, users, and messages
- 👥 **User Management** - Create, edit, delete users with permissions
- 📝 **Post Management** - Draft/publish workflow with featured images
- 📬 **Message Center** - View and manage contact form submissions

---

## 📸 Screenshots

| Home Page | Blog Detail | Dashboard |
|-----------|-------------|-----------|
| Modern homepage with featured posts | Rich content with comments | Full admin dashboard |

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| **Django 6.0** | Web framework |
| **Python 3.12** | Programming language |
| **SQLite/PostgreSQL** | Database |
| **Bootstrap 5** | Frontend styling |
| **CKEditor 5** | Rich text editor |
| **Crispy Forms** | Form rendering |
| **WhiteNoise** | Static file serving |
| **Gunicorn** | WSGI server |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+ installed
- Git installed

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/inkspire.git
   cd inkspire
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Open your browser**
   ```
   http://127.0.0.1:8000
   ```

---

## 📁 Project Structure

```
inkspire/
├── blog_main/              # Main Django project
│   ├── settings.py         # Development settings
│   ├── settings_prod.py    # Production settings
│   ├── urls.py             # Main URL configuration
│   ├── views.py            # Home, auth, profile views
│   ├── feeds.py            # RSS feed
│   ├── sitemaps.py         # XML sitemap
│   └── static/             # Static files (CSS, images)
├── blogs/                  # Blog app
│   ├── models.py           # Blog, Category, Comment, Like, etc.
│   ├── views.py            # Blog views
│   └── admin.py            # Admin configuration
├── dashboard/              # Dashboard app
│   ├── views.py            # Dashboard views
│   ├── forms.py            # Forms for posts, categories
│   └── urls.py             # Dashboard URLs
├── templates/              # HTML templates
│   ├── base.html           # Base template
│   ├── home.html           # Homepage
│   ├── blog_detail.html    # Single post view
│   └── dashboard/          # Dashboard templates
├── media/                  # User uploaded files
├── requirements.txt        # Python dependencies
├── Procfile               # Heroku/Railway deployment
├── runtime.txt            # Python version
└── README.md              # This file
```

---

## 🚀 Deployment

### PythonAnywhere (Free)

1. Sign up at [pythonanywhere.com](https://pythonanywhere.com)
2. Open a Bash console and clone your repo
3. Create virtualenv and install requirements
4. Configure WSGI file
5. Set up static files
6. Reload your web app

### Railway / Render

1. Connect your GitHub repository
2. Set environment variables:
   - `SECRET_KEY`
   - `DEBUG=False`
   - `ALLOWED_HOSTS`
   - `DJANGO_SETTINGS_MODULE=blog_main.settings_prod`
3. Deploy automatically

### DigitalOcean

Use your GitHub Student Pack for $200 free credits!
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

---

## ⚙️ Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | Debug mode | `False` for production |
| `ALLOWED_HOSTS` | Allowed domains | `yourdomain.com,www.yourdomain.com` |

---

## 👤 Default Credentials

After running `python manage.py populate_db`:

| User | Password | Role |
|------|----------|------|
| admin | admin123 | Superuser |
| john_doe | password123 | Regular user |

⚠️ **Change these passwords in production!**

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Django Documentation
- Bootstrap Team
- CKEditor Team
- All open-source contributors

---

<p align="center">
  Made with ❤️ using Django
</p>

<p align="center">
  <a href="#-inkspire---modern-blogging-platform">Back to Top ⬆️</a>
</p>
