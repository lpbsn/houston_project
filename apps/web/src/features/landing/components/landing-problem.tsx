import terrainEstablishments from '@/features/landing/assets/terrain-establishments.png'

export function LandingProblem() {
  return (
    <div className="sp-chapter sp-chapter-problem">
      <section className="sp-wrap sp-section sp-problem" id="sp-problem">
        <div className="noise-intro">
          <div className="sp-eyebrow">Le problème</div>
          <h2>
            Le terrain vous parle <span className="sp-em">en permanence.</span>
          </h2>
          <p>
            Chaque établissement produit des informations utiles. Dispersées entre les messages, les
            réunions et les outils, elles deviennent difficiles à rapprocher à l’échelle du réseau.
          </p>
        </div>
        <div className="noise-consequences">
          <article>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M4 4h11v8H9l-4 4v-4H4zM17 9h3v10h-4l-3 3v-3h-3v-4" />
            </svg>
            <h3>L’information se fragmente.</h3>
            <p>
              Un même problème peut apparaître sur plusieurs sites sans que la direction en voie la
              répétition.
            </p>
          </article>
          <article>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="13" r="8" />
              <path d="M12 8v5l3 2M3 4l3-2m12 0 3 2" />
            </svg>
            <h3>Les urgences prennent toute la place.</h3>
            <p>
              On traite ce qui demande une réponse immédiate. Le reste attend ou s’oublie.
            </p>
          </article>
          <article>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            <h3>Les signaux faibles restent sans suite.</h3>
            <p>
              Les irritants s’installent et les idées d’amélioration passent entre les mailles du
              filet.
            </p>
          </article>
        </div>
        <figure className="terrain-upload">
          <img
            src={terrainEstablishments}
            width={1448}
            height={1086}
            alt="Un dirigeant débordé devant trois établissements, entouré de notifications, de post-it et de collaborateurs lui remontant des observations."
            loading="lazy"
          />
        </figure>
      </section>
    </div>
  )
}
