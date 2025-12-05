# AutoCareer - Job Application Automation SaaS

A monorepo project for automating job search and application processes using Next.js (frontend) and Python Lambda functions (backend).

## Project Structure

```
/job-auto-apply
├── frontend/          # Next.js application
├── backend/          # Python microservices
├── package.json      # Root package.json with monorepo scripts
└── .env.local.example # Environment variables template
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- AWS CLI (for deployment)
- TeX Live (for LaTeX compilation)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/job-auto-apply.git
   cd job-auto-apply
   ```

2. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **Install backend dependencies**
   ```bash
   cd backend/services/resume-tailor
   pip install -r requirements.txt
   cd ../../..
   ```

4. **Set up environment variables**
   ```bash
   copy .env.local.example .env.local
   ```
   Edit `.env.local` with your actual API keys and configuration.

### Development

Run both frontend and backend in development mode:

```bash
npm run dev
```

Or run them separately:

**Frontend (Terminal 1):**
```bash
npm run dev:web
```

**Backend (Terminal 2):**
```bash
npm run dev:api
```

The frontend will be available at `http://localhost:3000`
The backend API will be available at `http://localhost:8000`

## Project Architecture

- **Frontend**: Next.js 14+ with App Router, TypeScript, Tailwind CSS
- **Backend**: Python FastAPI services deployed as AWS Lambda functions
- **Database**: DynamoDB for job tracking and user data
- **Storage**: S3 for resume PDFs
- **LLM**: OpenAI GPT-4o for resume tailoring and job matching

## Deployment

Deploy to AWS using SST:

```bash
npm run deploy
```

## Documentation

- [Project Specification](./README.md)
- [Folder Structure](./FolderStruct.md)
- [Module Specifications](./spec.md)

## License

MIT
