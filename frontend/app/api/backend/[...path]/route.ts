import {NextRequest, NextResponse} from 'next/server';
import {allowedRequest} from '@/lib/proxy-policy.mjs';
export const dynamic = 'force-dynamic';
async function proxy(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const {path} = await context.params;
  const route = path.join('/');
  if (!allowedRequest(route, request.method)) return NextResponse.json({detail: 'Endpoint unavailable'}, {status: 404});
  const origin = process.env.OPT_BACKEND_URL;
  if (!origin) return NextResponse.json({detail: 'Backend is not configured'}, {status: 503});
  const target = new URL(origin);
  if (target.protocol !== 'https:' && !(process.env.NODE_ENV === 'development' && ['localhost', '127.0.0.1'].includes(target.hostname))) {
    return NextResponse.json({detail: 'Backend must use HTTPS'}, {status: 503});
  }
  const authorization = request.headers.get('authorization') || '';
  if (!/^Bearer [A-Za-z0-9._-]+$/.test(authorization)) return NextResponse.json({detail: 'Sign in to continue'}, {status: 401});
  const body = ['GET', 'HEAD'].includes(request.method) ? undefined : await request.text();
  if (body && Buffer.byteLength(body) > 2_000_000) return NextResponse.json({detail: 'Request too large'}, {status: 413});
  try {
    const result = await fetch(new URL('/api/v1/' + route, target), {
      method: request.method, headers: {'Authorization': authorization, 'Content-Type': 'application/json'},
      body, redirect: 'manual', cache: 'no-store', signal: AbortSignal.timeout(30_000),
    });
    if (result.status >= 300 && result.status < 400) return NextResponse.json({detail: 'Unexpected backend redirect'}, {status: 502});
    return new NextResponse(await result.text(), {status: result.status, headers: {'Content-Type': 'application/json', 'Cache-Control': 'no-store'}});
  } catch {
    return NextResponse.json({detail: 'Backend unavailable. Please retry.'}, {status: 502});
  }
}
export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
