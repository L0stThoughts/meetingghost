import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  // Simple proxy placeholder to backend API
  return NextResponse.json({ ok: true })
}
