# Astro Assistant - AI-Powered Shopping Assistant

Astro Assistant helps you make smart purchasing decisions with AI-powered product analysis, price comparison, and personalized recommendations across top Indian e-commerce stores.

## Features

- 🚀 AI-powered product analysis
- 💰 Price comparison across multiple stores
- 📊 Smart buying recommendations
- ⏱️ Search history tracking
- 🔍 SEO optimized for better visibility
- 🌙 Dark theme with space-themed UI

## Prerequisites

- Python 3.8+
- PostgreSQL (with pgAdmin 4)
- Node.js (for frontend assets if needed)

## Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd BACKEND
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the PostgreSQL database:
   - Open pgAdmin 4
   - Create a new database named `astro_assistant`
   - Update the `.env` file with your database credentials

5. Run the Flask application:
   ```bash
   python app.py
   ```
   The backend will be available at `http://localhost:5000`

## Frontend Setup

The frontend is a static website that can be served from any web server. For development, you can use Python's built-in HTTP server:

```bash
cd FRONTEND
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

## Deployment

### Option 1: Netlify (Recommended for Frontend)

1. Push your code to a GitHub repository
2. Sign up/Log in to [Netlify](https://www.netlify.com/)
3. Click "New site from Git"
4. Select your repository and set the publish directory to `FRONTEND`
5. Deploy the site

### Option 2: Vercel

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```
2. Deploy:
   ```bash
   cd FRONTEND
   vercel
   ```

### Backend Deployment

For production, consider deploying the backend to:
- Heroku
- PythonAnywhere
- Google App Engine
- AWS Elastic Beanstalk

Make sure to set the following environment variables in your production environment:
- `DATABASE_URL`: Your PostgreSQL connection string
- `FLASK_ENV`: Set to "production"
- `SECRET_KEY`: A secure random string

## Environment Variables

Create a `.env` file in the `BACKEND` directory with the following variables:

```
DATABASE_URL=postgresql://username:password@localhost:5432/astro_assistant
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
```

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with Flask and SQLAlchemy
- Frontend powered by vanilla JavaScript and CSS
- Icons from Lucide
- Charts by Chart.js
