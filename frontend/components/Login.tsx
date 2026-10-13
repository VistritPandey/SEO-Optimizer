"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import {
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  sendEmailVerification,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
} from "firebase/auth";
import { firebaseAuth } from "@/lib/firebase";
export function Login() {
  const router = useRouter();
  const query = useSearchParams();
  const [register, setRegister] = useState(query.get("mode") === "register");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const data = new FormData(event.currentTarget);
    try {
      const auth = firebaseAuth();
      const email = String(data.get("email"));
      const password = String(data.get("password"));
      const result = register
        ? await createUserWithEmailAndPassword(auth, email, password)
        : await signInWithEmailAndPassword(auth, email, password);
      if (register) await sendEmailVerification(result.user);
      router.push("/dashboard");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sign in failed.");
    } finally {
      setBusy(false);
    }
  }
  async function google() {
    setBusy(true);
    setMessage("");
    try {
      await signInWithPopup(firebaseAuth(), new GoogleAuthProvider());
      router.push("/dashboard");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sign in failed.");
    } finally {
      setBusy(false);
    }
  }
  async function reset(event: React.MouseEvent<HTMLButtonElement>) {
    const form = event.currentTarget.form;
    const email = form ? String(new FormData(form).get("email")) : "";
    if (!email) {
      setMessage("Enter your email first.");
      return;
    }
    try {
      await sendPasswordResetEmail(firebaseAuth(), email);
      setMessage(
        "If this account exists, you’ll receive a password reset email.",
      );
    } catch {
      setMessage("Could not send the reset email. Please retry.");
    }
  }
  return (
    <main className="auth-shell">
      <Link className="brand" href="/">
        y<span>Your Optimiser</span>
      </Link>
      <section className="auth-card">
        <span className="eyebrow">YOUR WEBSITE’S WORKSPACE</span>
        <h1>
          {register ? "Start something" : "Good to have"}
          <br />
          <em>{register ? "worth finding." : "you back."}</em>
        </h1>
        <p>
          One place for findings, verified changes and the next useful step.
        </p>
        {message && (
          <p className="alert" role="status">
            {message}
          </p>
        )}
        <button
          className="button secondary full"
          onClick={google}
          disabled={busy}
        >
          Continue with Google ↗
        </button>
        <span className="divider">OR USE EMAIL</span>
        <form onSubmit={submit}>
          <label>
            Email
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              minLength={register ? 12 : 1}
              autoComplete={register ? "new-password" : "current-password"}
              required
            />
          </label>
          <button className="button full" disabled={busy}>
            {busy
              ? "One moment…"
              : register
                ? "Create free workspace ↗"
                : "Sign in ↗"}
          </button>
          {!register && (
            <button type="button" className="text-link" onClick={reset}>
              Forgot password?
            </button>
          )}
        </form>
        <button className="text-link" onClick={() => setRegister(!register)}>
          {register
            ? "Already have a workspace? Sign in"
            : "New here? Create a free workspace"}
        </button>
        <small>
          Email accounts need verification before connecting a repository.
        </small>
      </section>
    </main>
  );
}
