# NCO Search Frontend

Next.js 14 frontend for NCO Semantic Search application.

## Features

- 🔍 Real-time semantic search with debouncing
- 🎤 Voice search support (Hindi by default, fallback to English)
- 📊 Confidence scoring visualization
- ⭐ Favorite occupations (localStorage)
- 💬 User feedback collection
- 📱 Responsive design with Tailwind CSS
- ♿ Accessible UI with keyboard navigation

## Setup

### Prerequisites

- Node.js 18+
- Backend API running (default: http://localhost:8000)

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Update NEXT_PUBLIC_API_URL if backend is not on localhost:8000