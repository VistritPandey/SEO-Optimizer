"use client";

export function DemoPlayback({
  name,
  step,
  total,
  duration,
  playing,
  running,
  toggle,
}: {
  name: string;
  step: number;
  total: number;
  duration: number;
  playing: boolean;
  running: boolean;
  toggle: () => void;
}) {
  return (
    <div
      className="demo-playback"
      data-playing={playing}
      data-running={running}
    >
      <div className="demo-playback-bar">
        <span className="demo-playback-hint">
          <span className="playback-indicator" aria-hidden="true" />
          {playing ? "Auto-playing example" : "Explore at your pace"}
          <span className="playback-invitation"> · try any step</span>
        </span>
        <button
          type="button"
          data-demo-playback
          aria-label={`${playing ? "Pause" : "Play"} ${name}`}
          onClick={toggle}
        >
          <span aria-hidden="true">{playing ? "Ⅱ" : "▷"}</span>
          {playing ? "Pause" : "Play"}
        </button>
      </div>
      <div className="demo-playback-track" aria-hidden="true">
        {Array.from({ length: total }, (_, index) => (
          <span key={index} className={index < step ? "done" : ""}>
            {index === step && (
              <span
                key={`${step}-${running}`}
                className={running ? "filling" : "selected"}
                style={{ animationDuration: `${duration}ms` }}
              />
            )}
          </span>
        ))}
      </div>
    </div>
  );
}
