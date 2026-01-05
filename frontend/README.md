# DocTagger Frontend

This is the web interface for DocTagger, built with Next.js, React, and TypeScript.

## Getting Started

1. Install dependencies:

```bash
npm install
```

2. Create a `.env.local` file (copy from `.env.example`):

```bash
cp .env.example .env.local
```

3. Update the API URL in `.env.local` if needed (default is `http://localhost:8000`)

4. Run the development server:

```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Features

- **Dashboard**: View system status and statistics
- **File Upload**: Upload PDFs for processing
- **Document Browser**: View processed documents with tags and metadata
- **Real-time Updates**: WebSocket support for live processing updates
- **Watcher Control**: Start/stop the folder watcher from the UI

## Building for Production

```bash
npm run build
npm start
```

## Environment Variables

- `NEXT_PUBLIC_API_URL`: URL of the DocTagger API server (default: `http://localhost:8000`)

## Technology Stack

- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS
- WebSocket for real-time updates
