"use client";

import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";
import { site } from "@/lib/site";

const endpoint = "https://formspree.io/f/xdoqkdpy";

export function ContactForm() {
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">(
    "idle",
  );
  const [error, setError] = useState("");
  const pending = useRef(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    if (data.get("_gotcha")) return;
    pending.current = true;
    setStatus("sending");
    setError("");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20_000);
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        body: data,
        headers: { Accept: "application/json" },
        credentials: "omit",
        signal: controller.signal,
      });
      const result: unknown = await response.json();
      if (
        !response.ok ||
        !result ||
        typeof result !== "object" ||
        !("ok" in result) ||
        result.ok !== true ||
        "errors" in result ||
        "error" in result
      ) {
        setError(
          response.status === 429
            ? "The contact form is busy. Please try again later or email us directly."
            : "Your message could not be submitted. Please check your details or email us directly.",
        );
        setStatus("error");
        return;
      }
      form.reset();
      setStatus("sent");
    } catch {
      setError(
        "We couldn’t confirm your submission. Your message is still here. Check your connection before trying again, or email us directly.",
      );
      setStatus("error");
    } finally {
      window.clearTimeout(timeout);
      pending.current = false;
    }
  }

  return (
    <form
      className="contact-form"
      action={endpoint}
      method="POST"
      onSubmit={submit}
      aria-label="Contact Your Optimiser"
      aria-busy={status === "sending"}
    >
      <input
        type="hidden"
        name="_subject"
        value="Your Optimiser contact request"
      />
      <div className="contact-honeypot" aria-hidden="true">
        <label>
          Leave this field empty
          <input name="_gotcha" tabIndex={-1} autoComplete="off" />
        </label>
      </div>
      <div className="contact-fields">
        <label htmlFor="contact-name">
          Your name
          <input
            id="contact-name"
            name="name"
            autoComplete="name"
            maxLength={100}
            required
          />
        </label>
        <label htmlFor="contact-email">
          Email address
          <input
            id="contact-email"
            name="email"
            type="email"
            autoComplete="email"
            maxLength={254}
            required
          />
        </label>
      </div>
      <label htmlFor="contact-topic">
        What can we help with?
        <select
          id="contact-topic"
          name="topic"
          defaultValue="Product question"
          required
        >
          <option>Product question</option>
          <option>Something isn’t working</option>
          <option>Account or privacy request</option>
          <option>Security report</option>
          <option>Partnership or feedback</option>
        </select>
      </label>
      <label htmlFor="contact-message">
        Your message
        <textarea
          id="contact-message"
          name="message"
          rows={6}
          maxLength={5000}
          required
          placeholder="Tell us what’s on your mind."
        />
      </label>
      <p className="contact-form-note">
        We use these details to reply to your request. Messages are processed by
        Formspree. Please leave out passwords, API keys and sensitive account
        details. <Link href="/privacy">Privacy notice →</Link>
      </p>
      <div className="contact-form-actions">
        <button
          type="submit"
          className="button"
          disabled={status === "sending"}
        >
          {status === "sending" ? "Sending…" : "Send message ↗"}
        </button>
        <a href={`mailto:${site.supportEmail}`} className="text-link">
          Prefer email?
        </a>
      </div>
      <div className="contact-feedback" aria-live="polite" aria-atomic="true">
        {status === "sent" && (
          <p className="contact-success" role="status">
            Thanks. Your message has been submitted. We’ll reply to the email
            you provided.
          </p>
        )}
        {status === "error" && (
          <p className="contact-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </form>
  );
}
