import screenAgent from '@/features/landing/assets/screen-agent.png'
import screenDashboardDelays from '@/features/landing/assets/screen-dashboard-delays.png'
import screenDashboardSubjects from '@/features/landing/assets/screen-dashboard-subjects.png'
import screenExecution from '@/features/landing/assets/screen-execution.png'
import screenObservation from '@/features/landing/assets/screen-observation.png'

export function LandingProductFlow() {
  return (
    <section className="sp-product-flow" id="sp-product">
      <div className="sp-wrap sp-section">
        <div className="sp-eyebrow">Du terrain à la décision</div>
        <h2>
          Du terrain aux décisions,
          <br />
          <span className="sp-em">en trois étapes.</span>
        </h2>
        <p className="sp-flow-intro">
          Vos équipes captent. Vos dashboards donnent une vue d’ensemble. Votre agent analyse et
          propose les prochaines actions.
        </p>
        <div className="sf-flow">
          <article className="sf-step sf-mobile-step">
            <div className="sf-heading">
              <span className="sf-number">01</span>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M6 2h12v20H6z M10 18h4" />
              </svg>
            </div>
            <h3>L’application mobile</h3>
            <p>Faites remonter la réalité du terrain et suivez les actions avec vos équipes.</p>
            <div className="sf-device-area sf-mobile-stage">
              <div className="sf-phones">
                <div className="sf-real-phone sf-phone-back">
                  <img
                    src={screenExecution}
                    alt="Spore — suivi des plans d’action, écran Exécution"
                    width={944}
                    height={2048}
                    loading="lazy"
                  />
                </div>
                <div className="sf-real-phone sf-phone-front">
                  <img
                    src={screenObservation}
                    alt="Spore — création d’une observation par texte, photo ou vocal"
                    width={944}
                    height={2048}
                    loading="lazy"
                  />
                </div>
              </div>
            </div>
            <div className="sf-mobile-features">
              <div className="sf-mobile-feature">
                <span className="sf-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <rect x="4" y="5" width="16" height="15" rx="3" />
                    <path d="M9 5V3h6v2M8 11h8M8 15h5" />
                  </svg>
                </span>
                <div>
                  <strong>Capturez le terrain</strong>
                  <span>Observations · Photos · Vocal</span>
                </div>
              </div>
              <div className="sf-mobile-feature">
                <span className="sf-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M20 11a8 8 0 0 1-8 8H4l-2 3V11a9 9 0 0 1 18 0Z" />
                    <path d="M7 10h8M7 14h5" />
                  </svg>
                </span>
                <div>
                  <strong>Échangez en équipe</strong>
                  <span>Chat</span>
                </div>
              </div>
              <div className="sf-mobile-feature">
                <span className="sf-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <rect x="3" y="3" width="18" height="18" rx="5" />
                    <path d="m7 12 3 3 7-7" />
                  </svg>
                </span>
                <div>
                  <strong>Passez à l’action</strong>
                  <span>Plans d’action · Résolutions</span>
                </div>
              </div>
            </div>
          </article>

          <div className="sf-arrow" aria-label="Les données terrain alimentent les dashboards">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M4 12h16m-6-6 6 6-6 6" />
            </svg>
          </div>

          <article className="sf-step sf-dashboard-step">
            <div className="sf-heading">
              <span className="sf-number">02</span>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M3 3h7v7H3z M14 3h7v11h-7z M3 14h7v7H3z M14 18h7v3h-7z" />
              </svg>
            </div>
            <h3>Les dashboards</h3>
            <p>
              Comprenez les enjeux de chaque établissement et de votre réseau en quelques secondes.
            </p>
            <div className="sf-device-area sf-dashboard-stage">
              <div className="sf-monitors">
                <div className="sf-real-desktop sf-monitor-back">
                  <div className="sf-screen-rim">
                    <span />
                  </div>
                  <img
                    src={screenDashboardDelays}
                    alt="Dashboard Spore : retards et qualité des résolutions"
                    width={2048}
                    height={1105}
                    loading="lazy"
                  />
                  <div className="sf-monitor-chin" />
                  <div className="sf-monitor-foot" />
                </div>
                <div className="sf-real-desktop sf-monitor-front">
                  <div className="sf-screen-rim">
                    <span />
                  </div>
                  <img
                    src={screenDashboardSubjects}
                    alt="Dashboard Spore : sujets récurrents et nouveaux sujets"
                    width={2048}
                    height={1110}
                    loading="lazy"
                  />
                  <div className="sf-monitor-chin" />
                  <div className="sf-monitor-foot" />
                </div>
              </div>
            </div>
            <div className="sf-mobile-features">
              <div className="sf-mobile-feature">
                <span className="sf-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M3 17 9 11l4 3 8-10M15 4h6v6" />
                  </svg>
                </span>
                <div>
                  <strong>Repérez les enjeux</strong>
                  <span>Sujets · Tendances</span>
                </div>
              </div>
              <div className="sf-mobile-feature">
                <span className="sf-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <circle cx="12" cy="12" r="9" />
                    <path d="M12 7v5l3 2" />
                  </svg>
                </span>
                <div>
                  <strong>Suivez les échéances</strong>
                  <span>Délais · Échéances</span>
                </div>
              </div>
              <div className="sf-mobile-feature">
                <span className="sf-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="m12 3 3 6 6 1-4 5 1 6-6-3-6 3 1-6-4-5 6-1Z" />
                  </svg>
                </span>
                <div>
                  <strong>Évaluez les résultats</strong>
                  <span>Qualité des résolutions</span>
                </div>
              </div>
            </div>
          </article>

          <div className="sf-arrow" aria-label="Les données consolidées alimentent l’agent">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M4 12h16m-6-6 6 6-6 6" />
            </svg>
          </div>

          <article className="sf-step sf-agent-step">
            <div className="sf-heading">
              <span className="sf-number">03</span>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3z" />
              </svg>
            </div>
            <h3>L’agent IA</h3>
            <p>
              Croisez vos chiffres avec les faits du terrain pour expliquer les écarts et décider
              quoi faire.
            </p>
            <div className="sf-device-area sf-agent-stage">
              <div className="sf-real-desktop sf-agent-monitor">
                <div className="sf-screen-rim">
                  <span />
                </div>
                <img
                  src={screenAgent}
                  alt="Spore Brain : analyse du reporting et proposition de plan d’action contextualisée par les observations terrain"
                  width={2048}
                  height={1081}
                  loading="lazy"
                />
                <div className="sf-monitor-chin" />
                <div className="sf-monitor-foot" />
              </div>
            </div>
            <div className="sf-mobile-features">
              <div className="sf-mobile-feature">
                <span className="sf-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M4 20V4h16M8 16v-4M12 16V8M16 16v-6" />
                  </svg>
                </span>
                <div>
                  <strong>Analysez vos chiffres</strong>
                  <span>Analyse des reportings</span>
                </div>
              </div>
              <div className="sf-mobile-feature">
                <span className="sf-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <circle cx="11" cy="11" r="7" />
                    <path d="m16 16 5 5M8 11h6M11 8v6" />
                  </svg>
                </span>
                <div>
                  <strong>Détectez les signaux</strong>
                  <span>Signaux faibles · Axes d’amélioration</span>
                </div>
              </div>
              <div className="sf-mobile-feature">
                <span className="sf-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <rect x="3" y="3" width="18" height="18" rx="5" />
                    <path d="m7 12 3 3 7-7" />
                  </svg>
                </span>
                <div>
                  <strong>Décidez des actions</strong>
                  <span>Plans d’action</span>
                </div>
              </div>
            </div>
          </article>
        </div>
        <div className="sf-report">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M5 2h10l4 4v16H5z M8 10h8M8 14h8M8 18h8M12 10v8" />
          </svg>
          <span>
            <strong>Vos chiffres entrent aussi dans l’équation.</strong> Partagez vos reportings
            avec l’agent pour enrichir son analyse du terrain.
          </span>
        </div>
      </div>
    </section>
  )
}
