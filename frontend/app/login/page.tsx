import {Suspense} from 'react';
import {Login} from '@/components/Login';
export const metadata = {title: 'Sign in', robots: {index: false, follow: false}};
export default function Page() {return <Suspense fallback={<main className="auth-shell">Loading sign in…</main>}><Login/></Suspense>;}
