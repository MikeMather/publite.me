![Title image](/screenshots/title.svg)


### A minimalist, self-hostable, easily customizable blogging platform.

![tests](https://github.com/MikeMather/publite.me/actions/workflows/tests.yml/badge.svg)

[Documentation](https://publite.me/documentation) | [Browse Themes](https://publite.me/themes)

|  |  |
|---------|---------|
| ![Solarized](/screenshots/solarized.png) | ![analog](/screenshots/analog-synthesizer.png) |

|  |  |
|---------|---------|
| ![Solarized](/screenshots/typewriter.png) | ![analog](/screenshots/polaroid.png) |


## Features

- **Self-host the whole thing**: Host it yourself easily
- **Markdown Editor**: Built-in markdown editor in the admin dashboard
- **Customizable Themes**: Choose from our theme library or create your own
- **Responsive Design**: Optimized for all devices
- **RSS Support**: Built-in RSS feed for your blog
- **Comment System**: Simple comment system
- **Media Management**: Upload and manage images and files
- **SEO Friendly**: Meta tags support and sitemap generation

## Setup

### Option 1: Using Docker

1. Run the container:
   ```bash
   docker run -v ./data:/app/data \
     -e DB_PATH=/app/data/blog.db \
     -e MEDIA_ROOT=/app/data/media \
     -e SECRET_KEY=your_secret_key \
     -p 8000:8000 mikemather/publite:latest
   ```
2. Access the blog at `http://localhost:8000`
3. Access the admin dashboard at `http://localhost:8000/admin`

### Option 2: Using Docker Compose

1. Clone the repository: `git clone https://github.com/your-username/publite.me.git`
2. Update the environment variables in `docker-compose.yml`
3. Run the application: `docker-compose up`
4. Access the blog at `http://localhost:8000`
5. Access the admin dashboard at `http://localhost:8000/admin`

### Option 3: Manual Setup

1. Clone the repository: `git clone https://github.com/your-username/publite.me.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `.env` file
4. Run the application: `python run.py`
5. Access the blog at `http://localhost:8000`
6. Access the admin dashboard at `http://localhost:8000/admin`

## Development Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`
4. Install development dependencies: `pip install -r requirements-dev.txt`
5. Set up pre-commit hooks: `pre-commit install`
6. Run the development server: `python run.py`

## Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
