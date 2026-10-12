"use strict";
const liveJob = document.querySelector("[data-live-job]");
if (liveJob) {
  let previousStatus = null;
  const timer = window.setInterval(async () => {
    try {
      const response = await fetch(`/api/v1/jobs/${liveJob.dataset.liveJob}`, {credentials: "same-origin"});
      if (!response.ok) { window.clearInterval(timer); return; }
      const job = await response.json();
      if (previousStatus !== null && previousStatus !== job.status) { window.location.reload(); }
      previousStatus = job.status;
      if (!["queued", "running", "waiting_checks", "waiting_deployment"].includes(job.status)) {
        window.clearInterval(timer);
        window.location.reload();
      }
    } catch (_) { /* Transient disconnects are retried on the next bounded poll. */ }
  }, 5000);
}
