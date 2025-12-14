# AutoCareer Frontend

This is the Next.js frontend for the AutoCareer application.

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui
- **Icons:** Lucide React

## Getting Started

1.  **Install dependencies:**
    ```bash
    npm install
    ```

2.  **Run the development server:**
    ```bash
    npm run dev
    ```

3.  **Open [http://localhost:3000](http://localhost:3000)** with your browser to see the result.

## Project Structure

- `app/`: Next.js App Router pages and layouts.
- `components/`: Reusable UI components.
- `lib/`: Utility functions and API clients.
- `public/`: Static assets.

## API Integration

The frontend communicates with the backend services via the API client defined in `lib/api.ts`.
The backend API is expected to be running at `http://localhost:8000`.
