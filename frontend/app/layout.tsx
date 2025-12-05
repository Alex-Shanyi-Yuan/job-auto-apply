import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
    title: 'AutoCareer - Job Application Automation',
    description: 'Automate your job search and application process',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    )
}
