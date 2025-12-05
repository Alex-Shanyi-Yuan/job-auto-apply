import { NextResponse } from 'next/server'

export async function GET() {
    // Job sourcing cron job logic
    return NextResponse.json({ message: 'Job sourcing completed' })
}
