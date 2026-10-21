import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import story from "../public/customer/story.json";

const C = {
  paper: "#f7f7f0",
  ink: "#24342a",
  green: "#173529",
  lime: "#cce89a",
  line: "#dbe0d6",
  muted: "#6a776b",
  warm: "#a06148",
};
export const YOUR_DURATION = story.reduce(
  (sum, scene) => sum + scene.frames,
  0,
);
const serif = "Georgia, serif";
const rounded: React.CSSProperties = {
  borderRadius: 22,
  border: `1px solid ${C.line}`,
  overflow: "hidden",
};

const Pill: React.FC<{ children: React.ReactNode; warning?: boolean }> = ({
  children,
  warning = false,
}) => (
  <span
    style={{
      display: "inline-block",
      fontSize: 19,
      padding: "9px 15px",
      borderRadius: 30,
      background: warning ? "#f4e4d8" : "#e9f0df",
      color: warning ? C.warm : C.green,
    }}
  >
    {children}
  </span>
);
const Lamp = () => (
  <div style={{ position: "relative", width: 300, height: 350 }}>
    <div
      style={{
        position: "absolute",
        inset: -20,
        background: "radial-gradient(ellipse, #e6d4a660, transparent 66%)",
      }}
    />
    <div
      style={{
        position: "absolute",
        left: 35,
        top: 50,
        width: 230,
        height: 140,
        clipPath: "polygon(24% 0,76% 0,100% 100%,0 100%)",
        background:
          "repeating-linear-gradient(90deg,#e6decc,#e6decc 7px,#d8cfba 8px,#e6decc 11px)",
        zIndex: 2,
      }}
    />
    <div
      style={{
        position: "absolute",
        left: 141,
        top: 165,
        width: 18,
        height: 155,
        background: "linear-gradient(90deg,#a0784c,#caaa76,#a0784c)",
      }}
    />
    <div
      style={{
        position: "absolute",
        left: 55,
        top: 309,
        width: 190,
        height: 32,
        borderRadius: "50%",
        background: "linear-gradient(#c1a175,#99734b)",
        boxShadow: "0 15px 20px #6e5b3220",
      }}
    />
  </div>
);
const Website: React.FC<{
  fixed?: boolean;
  error?: boolean;
  spacing?: boolean;
}> = ({ fixed = false, error = false, spacing = false }) => (
  <div
    style={{
      ...rounded,
      background: "#fffefa",
      width: 1040,
      height: 640,
      boxShadow: "0 18px 50px #2030200a",
    }}
  >
    <div
      style={{
        padding: "17px 26px",
        borderBottom: `1px solid ${C.line}`,
        display: "flex",
        justifyContent: "space-between",
        fontSize: 18,
        color: C.muted,
      }}
    >
      <span style={{ letterSpacing: 4 }}>● ● ●</span>
      <span>cedar.example / {error ? "collection" : "home"}</span>
      <span>↗</span>
    </div>
    <div
      style={{
        padding: "20px 38px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <strong style={{ font: `38px ${serif}`, fontWeight: 400 }}>cedar.</strong>
      <span style={{ fontSize: 18, color: C.muted }}>Thoughtful lighting</span>
    </div>
    {error ? (
      <div style={{ padding: "36px 45px", height: 360 }}>
        <div style={{ font: `100px ${serif}`, color: C.warm }}>404</div>
        <h3 style={{ fontSize: 35, fontWeight: 400, margin: "8px 0 20px" }}>
          This collection cannot be found.
        </h3>
        <p style={{ fontSize: 24, color: C.muted }}>
          The homepage looks fine.
          <br />
          The visitor’s next step is broken.
        </p>
      </div>
    ) : (
      <div
        style={{
          display: "flex",
          padding: "15px 45px",
          height: 350,
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ width: 560, paddingTop: spacing ? 22 : 0 }}>
          <div style={{ fontSize: 15, letterSpacing: 2, color: C.muted }}>
            QUIET OBJECTS. WARM SPACES.
          </div>
          <h3
            style={{
              font: `58px/1.07 ${serif}`,
              letterSpacing: -2,
              margin: "18px 0",
            }}
          >
            Light that feels
            <br />
            <i style={{ color: C.green }}>like home.</i>
          </h3>
          <p
            style={{
              fontSize: 21,
              color: C.muted,
              lineHeight: 1.5,
              maxWidth: 450,
            }}
          >
            Thoughtful lighting for everyday spaces.
            <br />
            Solid cedar. Soft linen. A little warmth.
          </p>
          <div
            style={{
              display: "inline-block",
              padding: "15px 23px",
              background: C.green,
              borderRadius: 6,
              color: "white",
              fontSize: 20,
            }}
          >
            Explore the collection ↗
          </div>
        </div>
        <Lamp />
      </div>
    )}
    <div
      style={{
        margin: "12px 30px",
        padding: "20px 23px",
        borderRadius: 12,
        background: "#f0f2e9",
      }}
    >
      <div
        style={{
          fontSize: 13,
          letterSpacing: 1.3,
          color: C.muted,
          marginBottom: 10,
        }}
      >
        PAGE DESCRIPTION FOR SEARCH
      </div>
      <div
        style={{
          fontSize: 20,
          color: fixed ? C.green : C.warm,
          lineHeight: 1.45,
        }}
      >
        {fixed
          ? "Thoughtful lighting for everyday spaces. Meet the Cedar Desk Lamp: solid cedar, linen shade, warm 2700K light."
          : "Missing after the homepage update"}
      </div>
    </div>
  </div>
);
const Agent: React.FC<{ children: React.ReactNode; status?: string }> = ({
  children,
  status = "Checking the update",
}) => (
  <div
    style={{
      ...rounded,
      background: C.green,
      color: C.paper,
      width: 610,
      minHeight: 600,
      padding: 34,
      borderColor: C.green,
    }}
  >
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 17,
        borderBottom: "1px solid #ffffff25",
        paddingBottom: 27,
        marginBottom: 28,
      }}
    >
      <span
        style={{
          background: C.lime,
          color: C.green,
          borderRadius: 12,
          width: 55,
          height: 55,
          textAlign: "center",
          font: `italic 49px ${serif}`,
        }}
      >
        y
      </span>
      <div>
        <strong style={{ fontSize: 24, fontWeight: 500 }}>
          Your Optimiser
        </strong>
        <div style={{ fontSize: 17, color: "#b8ccbc", marginTop: 6 }}>
          {status}
        </div>
      </div>
    </div>
    {children}
  </div>
);
const Row: React.FC<{
  label: string;
  detail: string;
  done?: boolean;
  warning?: boolean;
}> = ({ label, detail, done = false, warning = false }) => (
  <div
    style={{
      padding: "21px 0",
      borderBottom: "1px solid #ffffff25",
      display: "flex",
      gap: 18,
    }}
  >
    <span style={{ fontSize: 25, color: warning ? "#eab48f" : C.lime }}>
      {warning ? "!" : done ? "✓" : "↗"}
    </span>
    <div>
      <strong
        style={{
          fontSize: 25,
          fontWeight: 500,
          color: warning ? "#f1c5a4" : "#f6f8ef",
        }}
      >
        {label}
      </strong>
      <p
        style={{
          fontSize: 20,
          color: "#b9ccbd",
          lineHeight: 1.5,
          margin: "9px 0 0",
        }}
      >
        {detail}
      </p>
    </div>
  </div>
);
const Cursor: React.FC<{ x: number; y: number; click?: boolean }> = ({
  x,
  y,
  click = false,
}) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      zIndex: 10,
      transform: "rotate(-12deg)",
    }}
  >
    {click && (
      <div
        style={{
          position: "absolute",
          left: -30,
          top: -25,
          width: 80,
          height: 80,
          borderRadius: "50%",
          border: `3px solid ${C.lime}`,
          opacity: 0.8,
        }}
      />
    )}
    <svg width="47" height="57" viewBox="0 0 30 38">
      <path
        d="M3 2v30l7-8 6 12 6-3-6-11h11Z"
        fill="white"
        stroke={C.green}
        strokeWidth="2"
      />
    </svg>
  </div>
);
const Intro = () => (
  <div style={{ display: "flex", gap: 70, alignItems: "center", height: 635 }}>
    <div style={{ width: 815 }}>
      <div style={{ font: `82px/1.05 ${serif}`, letterSpacing: -3 }}>
        An AI agent that
        <br />
        <i style={{ color: C.green }}>follows through.</i>
      </div>
      <p
        style={{
          fontSize: 30,
          color: C.muted,
          lineHeight: 1.6,
          margin: "28px 0",
        }}
      >
        Notices the update.
        <br />
        Fixes a confirmed problem.
        <br />
        Checks the website afterward.
      </p>
      <Pill>Then keeps watching.</Pill>
    </div>
    <div style={{ ...rounded, background: "white", width: 780, padding: 45 }}>
      {[
        "Homepage updated",
        "A broken collection link is found",
        "A focused fix is prepared",
        "The website is checked again",
      ].map((label, i) => (
        <div
          key={label}
          style={{
            display: "flex",
            gap: 20,
            alignItems: "center",
            padding: "23px 0",
            borderBottom: i === 3 ? "none" : `1px solid ${C.line}`,
            fontSize: 28,
          }}
        >
          <span
            style={{
              background: i === 3 ? C.green : "#e9f0df",
              color: i === 3 ? "white" : C.green,
              width: 42,
              height: 42,
              borderRadius: "50%",
              display: "grid",
              placeItems: "center",
              fontSize: 20,
            }}
          >
            {i === 3 ? "✓" : i + 1}
          </span>
          {label}
        </div>
      ))}
    </div>
  </div>
);
const Update = () => {
  const frame = useCurrentFrame();
  const clicked = frame > 115;
  const x = interpolate(frame, [20, 90], [910, 170], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(frame, [20, 90], [370, 565], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div style={{ display: "flex", gap: 50, position: "relative" }}>
      <Website error={clicked} />
      <Agent status="Website update detected">
        <Pill>Homepage update merged</Pill>
        <Row
          label="A new design goes live"
          detail="Your team carries on building."
        />
        <Row
          label="The next step now fails"
          detail="The main collection button leads to a missing page."
          warning={clicked}
        />
        <p
          style={{
            fontSize: 24,
            lineHeight: 1.6,
            color: "#b9ccbd",
            marginTop: 30,
          }}
        >
          A page can look right
          <br />
          and still need attention.
        </p>
      </Agent>
      <Cursor x={x} y={y - 125} click={frame >= 90 && frame < 115} />
    </div>
  );
};
const Check = () => {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", gap: 50 }}>
      <Website error={false} />
      <Agent>
        <Row
          label="Read the changed page"
          detail="Understand the update and existing content."
          done={frame > 25}
        />
        <Row
          label="Follow the collection link"
          detail="Confirmed: the destination returns 404."
          warning={frame > 70}
        />
        <Row
          label="Check page information"
          detail="Confirmed: the description is missing."
          warning={frame > 115}
        />
        <div style={{ marginTop: 28, fontSize: 20, color: C.lime }}>
          Two confirmed problems. A focused next step.
        </div>
      </Agent>
    </div>
  );
};
const Fix = () => {
  const frame = useCurrentFrame();
  const ready = frame > 120;
  return (
    <div style={{ display: "flex", gap: 50 }}>
      <div
        style={{
          ...rounded,
          background: "white",
          width: 1040,
          height: 640,
          padding: 38,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 30,
          }}
        >
          <h3 style={{ fontSize: 30, fontWeight: 500, margin: 0 }}>
            The proposed changes
          </h3>
          <Pill>Homepage only</Pill>
        </div>
        {[
          [
            "COLLECTION BUTTON",
            "/collections/lighting/ → missing page",
            "/shop/ → existing collection",
          ],
          [
            "PAGE DESCRIPTION",
            "Missing",
            "Restored from the existing page content",
          ],
        ].map(([title, before, after]) => (
          <div
            key={title}
            style={{
              margin: "27px 0",
              padding: 27,
              background: "#f5f6ef",
              borderRadius: 13,
            }}
          >
            <div
              style={{
                fontSize: 15,
                letterSpacing: 1.5,
                color: C.muted,
                marginBottom: 17,
              }}
            >
              {title}
            </div>
            <div
              style={{
                fontSize: 25,
                color: C.warm,
                marginBottom: 17,
                display: "flex",
                gap: 17,
              }}
            >
              <span>−</span>
              {before}
            </div>
            <div
              style={{
                fontSize: 25,
                color: C.green,
                display: "flex",
                gap: 17,
                opacity: ready ? 1 : 0.3,
              }}
            >
              <span>+</span>
              {after}
            </div>
          </div>
        ))}
        <div style={{ padding: "20px 4px", fontSize: 22, color: C.muted }}>
          Your design, product price and private preview stay as intended.
        </div>
      </div>
      <Agent status="Preparing a fix">
        <Row
          label="Use the working destination"
          detail="Links to the verified collection page."
          done={frame > 40}
        />
        <Row
          label="Use supported information"
          detail="A description drawn from what the page already says."
          done={frame > 90}
        />
        <Row
          label="Test before review"
          detail="The proposed page changes pass their checks."
          done={ready}
        />
        <div style={{ marginTop: 27, fontSize: 20, color: C.lime }}>
          Ready for a reviewable update.
        </div>
      </Agent>
    </div>
  );
};
const Review = () => {
  const frame = useCurrentFrame();
  const approved = frame > 145;
  return (
    <div style={{ display: "flex", gap: 50, position: "relative" }}>
      <div
        style={{
          ...rounded,
          background: "white",
          width: 1040,
          height: 640,
          padding: 42,
        }}
      >
        <span style={{ fontSize: 16, letterSpacing: 1.4, color: C.muted }}>
          PROPOSED WEBSITE UPDATE · EXAMPLE REVIEW
        </span>
        <h3
          style={{
            fontSize: 42,
            fontWeight: 400,
            margin: "25px 0 20px",
            letterSpacing: -1,
          }}
        >
          Restore the collection path
          <br />
          and homepage description
        </h3>
        <p
          style={{
            fontSize: 25,
            lineHeight: 1.6,
            color: C.muted,
            maxWidth: 870,
          }}
        >
          Visitors should reach the collection from the homepage. The page
          description should use the existing, supported content.
        </p>
        <div
          style={{
            padding: "23px 0",
            borderTop: `1px solid ${C.line}`,
            borderBottom: `1px solid ${C.line}`,
            fontSize: 23,
            lineHeight: 1.9,
          }}
        >
          ✓ Focused source change
          <br />✓ Page checks passed
          <br />✓ Explanation and before/after included
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 22,
            marginTop: 30,
          }}
        >
          <span
            style={{
              display: "inline-block",
              background: C.green,
              color: "white",
              padding: "16px 24px",
              borderRadius: 8,
              fontSize: 23,
            }}
          >
            {approved ? "✓ Approved for this example" : "Approve example fix →"}
          </span>
          <span style={{ fontSize: 18, color: C.muted }}>
            Your team decides.
          </span>
        </div>
      </div>
      <Agent
        status={
          approved ? "Waiting for the updated website" : "Ready for your team"
        }
      >
        <Row
          label="A pull request for review"
          detail="See exactly what the agent wants to change."
          done
        />
        <Row
          label="Control stays with you"
          detail="Your project settings determine which updates need approval."
          done
        />
        <p
          style={{
            fontSize: 26,
            lineHeight: 1.6,
            color: "#b9ccbd",
            marginTop: 30,
          }}
        >
          A proposal is not
          <br />a verified live fix.
          <br />
          <span style={{ color: C.lime }}>The agent follows through.</span>
        </p>
      </Agent>
      {frame > 75 && (
        <Cursor x={200} y={550} click={frame > 130 && frame < 160} />
      )}
    </div>
  );
};
const Verify = () => {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", gap: 50 }}>
      <div
        style={{
          ...rounded,
          width: 1040,
          height: 640,
          background: "white",
          position: "relative",
        }}
      >
        <Img
          src={staticFile("customer/recorded-collection.png")}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "top",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 25,
            bottom: 25,
            padding: "13px 20px",
            background: C.green,
            color: "white",
            borderRadius: 10,
            fontSize: 20,
          }}
        >
          ✓ Collection opened after the recorded fix
        </div>
      </div>
      <Agent status="Checking the updated website">
        <Row
          label="Collection link opens"
          detail="The visitor reaches the real collection page."
          done={frame > 35}
        />
        <Row
          label="Description restored"
          detail="The served page contains the supported description."
          done={frame > 80}
        />
        <Row
          label="Close the confirmed issue"
          detail="The result is checked after the fix goes live."
          done={frame > 120}
        />
        <div style={{ fontSize: 22, color: C.lime, marginTop: 25 }}>
          Back to watching for the next change.
        </div>
        <p style={{ fontSize: 17, color: "#b9ccbd", lineHeight: 1.5 }}>
          This checks the fix. Search engines decide
          <br />
          how and when to use the page.
        </p>
      </Agent>
    </div>
  );
};
const Healthy = () => (
  <div style={{ display: "flex", gap: 50 }}>
    <Website fixed spacing />
    <Agent status="Next homepage update checked">
      <Pill>Design spacing updated</Pill>
      <Row
        label="Collection still opens"
        detail="Visitors can still reach the products."
        done
      />
      <Row
        label="Page information intact"
        detail="The description and product facts are unchanged."
        done
      />
      <Row
        label="No fix needed"
        detail="No unnecessary edit. No extra review."
        done
      />
      <div style={{ marginTop: 25, fontSize: 23, color: C.lime }}>
        Your team’s design stays as intended.
      </div>
    </Agent>
  </div>
);
const Watch = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 80, height: 635 }}>
    <div style={{ width: 770 }}>
      <h3
        style={{
          font: `75px/1.1 ${serif}`,
          letterSpacing: -3,
          fontWeight: 400,
          margin: 0,
        }}
      >
        Beyond the audit.
        <br />
        <i style={{ color: C.green }}>An ongoing agent.</i>
      </h3>
      <p
        style={{ fontSize: 29, lineHeight: 1.6, color: C.muted, marginTop: 30 }}
      >
        Checks after website updates.
        <br />
        Regular checks in between.
        <br />A clear record of what changed.
      </p>
      <Pill>Update → check → fix when needed → verify</Pill>
    </div>
    <div
      style={{
        ...rounded,
        background: C.green,
        width: 780,
        padding: 40,
        color: "white",
      }}
    >
      <div style={{ fontSize: 25, marginBottom: 25 }}>
        Your website’s activity
      </div>
      <Row
        label="Homepage issue fixed"
        detail="Working link and description verified."
        done
      />
      <Row
        label="Design update checked"
        detail="No fix needed. No extra review."
        done
      />
      <Row
        label="Monitoring continues"
        detail="Ready for the next website update."
        done
      />
      <div
        style={{
          display: "flex",
          gap: 15,
          alignItems: "center",
          fontSize: 22,
          color: C.lime,
          marginTop: 25,
        }}
      >
        <span
          style={{
            width: 9,
            height: 9,
            borderRadius: "50%",
            background: C.lime,
          }}
        />
        Your Optimiser is watching.
      </div>
    </div>
  </div>
);
const scenes = [Intro, Update, Check, Fix, Review, Verify, Healthy, Watch];
const Scene: React.FC<{ index: number }> = ({ index }) => {
  const frame = useCurrentFrame();
  const duration = story[index].frames;
  const enter = interpolate(frame, [0, 14], [0, 1], {
    extrapolateRight: "clamp",
  });
  const exit = interpolate(frame, [duration - 10, duration], [1, 0], {
    extrapolateLeft: "clamp",
  });
  const Content = scenes[index];
  return (
    <AbsoluteFill
      style={{
        background: C.paper,
        fontFamily: "Arial, sans-serif",
        color: C.ink,
        padding: "38px 65px",
      }}
    >
      <div
        style={{
          opacity: Math.min(enter, exit),
          transform: `translateY(${(1 - enter) * 12}px)`,
        }}
      >
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 27,
          }}
        >
          <div style={{ display: "flex", gap: 15, alignItems: "center" }}>
            <span style={{ font: `italic 42px ${serif}`, color: C.green }}>
              y
            </span>
            <strong style={{ fontSize: 24, fontWeight: 500 }}>
              Your Optimiser
            </strong>
          </div>
          <div style={{ fontSize: 17, color: C.muted }}>
            Illustrated customer journey · example website
          </div>
        </header>
        <div
          style={{
            fontSize: 15,
            letterSpacing: 2,
            color: C.muted,
            marginBottom: 15,
          }}
        >
          {story[index].chapter}
        </div>
        <h1
          style={{
            fontSize: 54,
            fontWeight: 500,
            letterSpacing: -1.7,
            margin: "0 0 30px",
            lineHeight: 1.15,
          }}
        >
          {story[index].title}
        </h1>
        <Content />
      </div>
      <div
        style={{
          position: "absolute",
          left: 65,
          right: 65,
          bottom: 85,
          background: C.green,
          color: C.paper,
          borderRadius: 12,
          padding: "14px 24px",
          fontSize: 26,
          lineHeight: 1.45,
          textAlign: "center",
        }}
      >
        {story[index].caption}
      </div>
      <div style={{ position: "absolute", left: 65, right: 65, bottom: 25 }}>
        <div style={{ display: "flex", gap: 7, marginBottom: 17 }}>
          {story.map((s, i) => (
            <div
              key={s.chapter}
              style={{
                height: 3,
                flex: 1,
                background: i <= index ? C.green : "#d8dfd2",
              }}
            />
          ))}
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 15,
            color: C.muted,
          }}
        >
          <span>
            Find the real problem. Make the focused fix. Check the result.
          </span>
          <span>{String(index + 1).padStart(2, "0")} / 08</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
export const YourOptimiser = () => {
  let from = 0;
  return (
    <AbsoluteFill>
      {story.map((scene, index) => {
        const start = from;
        from += scene.frames;
        return (
          <Sequence
            key={scene.chapter}
            from={start}
            durationInFrames={scene.frames}
          >
            <Scene index={index} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
