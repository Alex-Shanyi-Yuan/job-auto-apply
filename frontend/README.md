# AutoCareer Frontend

The web interface for AutoCareer - built with Next.js 14, TypeScript, and shadcn/ui.

## Features

- 📊 **Dashboard** - Track all job applications with status badges
- 🔍 **Suggestions** - AI-discovered jobs with scoring and source management
- 📝 **Apply** - Manual URL submission for resume tailoring
- 📄 **Job Details** - View requirements and download tailored PDFs

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui
- **State**: React hooks with polling

## Getting Started

### Prerequisites

- Node.js 18+
- Backend services running (see [main README](../README.md))

### Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Landing (redirects to dashboard)
│   ├── dashboard/          # Application history
│   ├── apply/              # Manual URL submission
│   ├── suggestions/        # AI job discovery
│   └── jobs/[id]/          # Job details
│
├── components/ui/          # shadcn/ui components
│   ├── badge.tsx
│   ├── button.tsx
│   ├── card.tsx
│   ├── input.tsx
│   ├── label.tsx
│   └── table.tsx
│
├── lib/
│   ├── api.ts              # Backend API client
│   └── utils.ts            # Utility functions
│
└── public/                 # Static assets
```

## Pages

### Dashboard (`/dashboard`)
- Lists all applied jobs
- Status badges (Processing, Applied, Failed, etc.)
- Click job to view details

### Suggestions (`/suggestions`)
- **Global Filter**: Set criteria applied to all sources
- **Job Sources**: Add/edit/delete job board search URLs
- **Suggestions List**: AI-scored jobs from all sources
- **Actions**: Apply or Dismiss each job

### Apply (`/apply`)
- Manual job URL submission
- Triggers resume tailoring workflow

### Job Details (`/jobs/[id]`)
- Company and title
- Extracted requirements
- PDF download button
- Error messages if failed

## API Client

The `lib/api.ts` module provides typed functions for all backend endpoints:

```typescript
// Jobs
getJobs()
getJob(id)
applyForJob(url)
dismissJob(id)

// Sources
getSources()
createSource(name, url, filter?)
updateSource(id, updates)
deleteSource(id)

// Suggestions
getSuggestions()
refreshSuggestions()
getScanStatus()

// Settings
getGlobalFilter()
updateGlobalFilter(prompt)
```

## Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Related Documentation

- [Main Project README](../README.md)
- [Backend API Spec](../backend/services/resume-tailor/spec.md)
- [Project Structure](../FolderStruct.md)
