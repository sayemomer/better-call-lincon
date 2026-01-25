// src/pages/AboutUsPage.tsx
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

/**
 * ✅ Put your team photos here:
 * src/assets/team/
 *  - omer.jpg
 *  - mahdieh.jpg
 *  - sharifa.jpg
 */
import omerImg from "../assets/about/omer.jpg";
import mahdiehImg from "../assets/about/mahdieh.jpg";
import sharifaImg from "../assets/about/sharifa.jpg";

type TeamMember = {
  name: string;
  role: string;
  photo: string;
  bio: string; // 2 sentences
  highlights: string[]; // bullet points
  tags?: string[];
  links?: {
    linkedin?: string;
    github?: string;
    email?: string;
  };
};

function LinkedInIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
      <path d="M4.98 3.5C4.98 4.88 3.87 6 2.5 6S0 4.88 0 3.5 1.12 1 2.5 1 4.98 2.12 4.98 3.5ZM.5 24h4V7.98h-4V24ZM8.5 7.98h3.83v2.19h.05c.53-1.01 1.83-2.08 3.77-2.08 4.03 0 4.77 2.65 4.77 6.09V24h-4v-7.42c0-1.77-.03-4.04-2.46-4.04-2.46 0-2.84 1.92-2.84 3.91V24h-4V7.98Z" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
      <path d="M12 .5C5.73.5.75 5.64.75 12c0 5.1 3.29 9.43 7.86 10.96.58.11.79-.26.79-.57v-2.2c-3.2.71-3.88-1.39-3.88-1.39-.52-1.35-1.27-1.71-1.27-1.71-1.04-.72.08-.71.08-.71 1.15.08 1.76 1.21 1.76 1.21 1.02 1.78 2.68 1.26 3.33.96.1-.75.4-1.26.73-1.55-2.55-.29-5.23-1.3-5.23-5.78 0-1.28.45-2.33 1.2-3.15-.12-.29-.52-1.47.11-3.07 0 0 .98-.32 3.2 1.2.93-.26 1.93-.39 2.92-.4.99.01 1.99.14 2.92.4 2.22-1.52 3.2-1.2 3.2-1.2.63 1.6.23 2.78.11 3.07.75.82 1.2 1.87 1.2 3.15 0 4.49-2.69 5.49-5.25 5.78.41.36.78 1.08.78 2.18v3.23c0 .32.21.69.8.57 4.56-1.53 7.85-5.86 7.85-10.96C23.25 5.64 18.27.5 12 .5Z" />
    </svg>
  );
}

function MailIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
      <path d="M2.25 6.75A3.75 3.75 0 0 1 6 3h12a3.75 3.75 0 0 1 3.75 3.75v10.5A3.75 3.75 0 0 1 18 21H6a3.75 3.75 0 0 1-3.75-3.75V6.75Zm3.2-.86 6.02 4.28c.32.23.75.23 1.07 0l6.02-4.28A2.25 2.25 0 0 0 18 4.5H6a2.25 2.25 0 0 0-1.35.39ZM19.5 7.9l-6.1 4.34c-.85.6-1.95.6-2.8 0L4.5 7.9v9.35C4.5 18.22 5.28 19 6.25 19h11.5c.97 0 1.75-.78 1.75-1.75V7.9Z" />
    </svg>
  );
}

function SocialLink({
  href,
  label,
  children,
}: {
  href: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      aria-label={label}
      className="inline-flex items-center gap-2 rounded-xl border border-blue-200/40 bg-white/70 px-3 py-2 text-sm text-slate-700 shadow-sm hover:bg-white"
    >
      {children}
    </a>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-blue-200/40 bg-white/70 px-3 py-1 text-xs text-slate-700">
      {children}
    </span>
  );
}

export default function AboutUsPage() {
  const navigate = useNavigate();

  const team = useMemo<TeamMember[]>(
    () => [
      {
        name: "Omer Sayem",
        role: "Applied AI & Systems Engineering",
        photo: omerImg,
        bio: "Applied Computer Science student specializing in AI systems, backend engineering, and secure application design. Experienced in building end-to-end ML pipelines, agent-based systems, and privacy-aware architectures.",
        highlights: [
          "Machine Learning, Generative AI & model integration",
          "Backend APIs (FastAPI), system design & database modeling",
          "Security-aware engineering and applied research projects",
        ],
        tags: ["AI Systems", "Backend", "Security-minded"],
        links: {
          // TODO: replace with real
          linkedin: "https://www.linkedin.com/in/omer-sayem/",
        },
      },
      {
  name: "Mahdieh Shekarian",
  role: "M.Applied Computer Science • ML & Software Engineering",
  photo: mahdiehImg,
  bio: "Master’s student in Applied Computer Science at Concordia University with strong foundations in machine learning, deep learning, and software engineering. Experienced in building AI-driven systems using Django, FastAPI, TensorFlow, and PyTorch, with hands-on research and teaching experience.",
  highlights: [
    "Machine Learning & NLP (Text Summarization, Sentiment Analysis, Feature Engineering)",
    "Deep Learning projects including medical image analysis (Fast R-CNN, segmentation metrics)",
    "Backend development with Django & database integration (MySQL, MongoDB)",
  ],
  tags: ["Machine Learning", "Deep Learning", "Django", "NLP", "Agile"],
         links: {
          // TODO: replace with real
          linkedin: "https://www.linkedin.com/in/mahdieh-shekarian/",
        
        },
},
      {
        name: "Sharifa Akter",
        role: "Information Systems Security (MSc, Co-op)",
        photo: sharifaImg,
        bio: "Cybersecurity-focused engineer with hands-on experience in offensive and defensive security, with strong foundations in cryptography and secure systems.",
        highlights: [
          "Container security, ethical hacking & threat detection",
          "Real-world attack simulations (ARP spoofing, MITM, container breakout)",
          "Secure system implementation including RSA signature workflows",
        ],
        tags: ["Container Security", "Ethical Hacking", "Cryptography"],
        links: {
          // TODO: replace with real
          linkedin: "https://www.linkedin.com/in/aktersharifa/",
        
        },
      },
    ],
    []
  );

  return (
    <div className="min-h-screen bg-[#edf3f8] text-slate-800">
      {/* Fixed background */}
      <div className="fixed inset-0 -z-10 bg-[#e3edf6]" />

      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-3xl border border-blue-200/40 bg-[#f4f8fc] p-6 shadow-xl">
          {/* Top bar */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate("/home")}
              className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              ← Back
            </button>

          </div>

          {/* WHO WE ARE (exactly from your screenshot) */}
          <div className="mt-10 text-center">
            <div className="text-xs font-semibold tracking-[0.22em] text-slate-500">
              TEAM
            </div>
            <h2 className="mt-3 text-3xl font-semibold text-slate-900 md:text-4xl">
              Who we are
            </h2>
            <p className="mx-auto mt-4 max-w-3xl text-base text-slate-600 md:text-lg">
              A small team combining security, engineering, and product thinking — focused
              on building reliable tools that respect users.
            </p>
          </div>

          {/* Photos row (bigger) */}
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {team.map((m) => (
              <div key={m.name} className="flex flex-col items-center">
                <img
                  src={m.photo}
                  alt={`${m.name} profile`}
                  className="h-40 w-40 rounded-2xl border border-blue-200/40 object-cover shadow-md"
                  loading="lazy"
                />
              </div>
            ))}
          </div>

          {/* Info row under each photo */}
          <div className="mt-6 grid gap-6 md:grid-cols-3">
            {team.map((m) => (
              <div
                key={m.name}
                className="rounded-3xl border border-blue-200/40 bg-[#edf3f8] p-6 shadow-sm"
              >
                <div className="text-center">
                  <div className="text-xl font-semibold text-slate-900">{m.name}</div>
                  <div className="mt-1 text-sm text-slate-600">{m.role}</div>

                  {m.tags && m.tags.length > 0 && (
                    <div className="mt-4 flex flex-wrap justify-center gap-2">
                      {m.tags.map((t) => (
                        <Tag key={t}>{t}</Tag>
                      ))}
                    </div>
                  )}
                </div>

                <p className="mt-5 text-sm leading-relaxed text-slate-700">{m.bio}</p>

                <ul className="mt-5 space-y-2 text-sm text-slate-700">
                  {m.highlights.map((h) => (
                    <li key={h} className="flex gap-2">
                      <span className="mt-[7px] h-2 w-2 flex-none rounded-full bg-blue-600" />
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>

                {(m.links?.linkedin || m.links?.github || m.links?.email) && (
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {m.links?.linkedin && (
                      <SocialLink href={m.links.linkedin} label={`${m.name} LinkedIn`}>
                        <LinkedInIcon />
                        <span>LinkedIn</span>
                      </SocialLink>
                    )}
                    {m.links?.github && (
                      <SocialLink href={m.links.github} label={`${m.name} GitHub`}>
                        <GitHubIcon />
                        <span>GitHub</span>
                      </SocialLink>
                    )}
                    {m.links?.email && (
                      <SocialLink href={m.links.email} label={`Email ${m.name}`}>
                        <MailIcon />
                        <span>Email</span>
                      </SocialLink>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Our major / focus area section (from your sketch) */}
          <div className="mt-10 rounded-3xl border border-blue-200/40 bg-[#edf3f8] p-6">
            <div className="text-sm font-semibold text-slate-900">Our focus</div>
            <p className="mt-2 text-sm text-slate-600">
              We focus on building an immigration guidance assistant that prioritizes
              clarity, privacy, and security — using modern AI systems and strong software
              engineering practices.
            </p>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-blue-200/40 bg-white/60 p-4 text-sm text-slate-700">
                <div className="font-semibold text-slate-900">Security-first</div>
                <div className="mt-1 text-slate-600">
                  Privacy-aware design, safe defaults, and clear boundaries on what the
                  system can and cannot do.
                </div>
              </div>
              <div className="rounded-2xl border border-blue-200/40 bg-white/60 p-4 text-sm text-slate-700">
                <div className="font-semibold text-slate-900">Practical guidance</div>
                <div className="mt-1 text-slate-600">
                  Steps, checklists, and timelines that help users act with confidence.
                </div>
              </div>
              <div className="rounded-2xl border border-blue-200/40 bg-white/60 p-4 text-sm text-slate-700">
                <div className="font-semibold text-slate-900">Reliable engineering</div>
                <div className="mt-1 text-slate-600">
                  Clean architecture, stable APIs, and quality-focused iteration.
                </div>
              </div>
            </div>
          </div>

          {/* Footer note */}
          <div className="mt-8 rounded-3xl border border-blue-200/40 bg-[#edf3f8] p-5 text-sm text-slate-600">
            <span className="font-semibold text-slate-700">Note:</span> This project
            provides informational guidance only — not legal advice.
          </div>
        </div>
      </div>
    </div>
  );
}