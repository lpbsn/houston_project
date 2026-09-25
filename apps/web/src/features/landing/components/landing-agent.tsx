import logoLePalais from '@/features/landing/assets/logo-le-palais.png'
import logoMamaShelter from '@/features/landing/assets/logo-mama-shelter.png'
import logoMrBricolage from '@/features/landing/assets/logo-mr-bricolage.png'
import { LandingProductFlow } from '@/features/landing/components/landing-product-flow'

export function LandingAgent() {
  return (
    <div className="sp-chapter sp-chapter-solution">
      <LandingProductFlow />

      <section className="sp-future" id="sp-agent">
        <div className="sp-wrap sp-section">
          <div className="sp-eyebrow">L’agent Spore · Votre intelligence opérationnelle</div>
          <h2>
            Vos chiffres. Votre terrain.
            <br />
            <span className="sp-em">Une intelligence qui fait le lien.</span>
          </h2>
          <p className="agent-lead">
            Demandez-lui ce qui freine vos établissements. Spore croise vos reportings avec les
            observations, les échanges et les plans d’action pour faire émerger les problèmes,
            leurs causes possibles et les leviers d’amélioration.
          </p>
          <div className="agent-abilities">
            <div>
              <b>Il analyse.</b>
              <p>Les écarts de vos reportings, éclairés par les faits de l’exploitation.</p>
            </div>
            <div>
              <b>Il rapproche.</b>
              <p>Les signaux dispersés qui peuvent révéler un même problème.</p>
            </div>
            <div>
              <b>Il propose.</b>
              <p>Des plans d’action argumentés, avec responsables, échéances et suivi.</p>
            </div>
          </div>
          <div className="sp-cases">
            <h3>Un agent construit avec des exploitants.</h3>
            <div
              className="sp-experience-logos"
              aria-label="Établissements issus de l’expérience de notre cofondateur"
            >
              <figure>
                <div>
                  <img src={logoLePalais} alt="Le Palais" width={240} height={240} loading="lazy" />
                </div>
                <figcaption>Le Palais Nancy</figcaption>
              </figure>
              <figure>
                <div>
                  <img
                    src={logoMrBricolage}
                    alt="Mr Bricolage"
                    width={1113}
                    height={202}
                    loading="lazy"
                  />
                </div>
                <figcaption>Mr Bricolage Nancy</figcaption>
              </figure>
              <figure>
                <div>
                  <img
                    src={logoMamaShelter}
                    alt="Mama Shelter Nice"
                    width={560}
                    height={741}
                    loading="lazy"
                  />
                </div>
                <figcaption>Mama Shelter Nice</figcaption>
              </figure>
            </div>
            <p>
              Spore s’appuie déjà sur des cas issus de l’expérience de notre cofondateur au Palais
              Nancy, chez Mr Bricolage Nancy et au Mama Shelter Nice. Ces situations réelles
              nourrissent ses raisonnements et ses recommandations opérationnelles.
            </p>
            <p className="sp-note">Références d’expérience professionnelle du cofondateur.</p>
          </div>
        </div>
      </section>
    </div>
  )
}
