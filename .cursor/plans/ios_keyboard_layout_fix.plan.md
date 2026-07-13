---
name: iOS keyboard layout fix
overview: Instrumenter minimalement, mesurer T0/T1/T2 sur le chat PWA, diagnostiquer, puis appliquer un diff minimal scoped TerrainShell — sans présupposer lock, offsetTop ni changement de hauteur.
todos:
  - id: instrument
    content: Instrumentation temporaire minimale dans TerrainShell ou Web Inspector — pas de helper sauf nécessité
    status: completed
  - id: measure-chat-pwa
    content: Mesures T0/T1/T2 sur textarea chat en PWA standalone
    status: completed
  - id: diagnose
    content: Diagnostic à partir des deltas — scroll doc, visualViewport, hauteur shell (combinables)
    status: completed
  - id: fix-and-revalidate
    content: Diff minimal selon diagnostic, revalidation iPhone, retrait instrumentation
    status: completed
isProject: true
---

# iOS Safari/PWA — topbar décalée au focus clavier

## Symptôme

Focus clavier sur un champ éditable terrain → layout remonte, topbar sous la barre système. Cause non établie. **Aucun fix avant mesure.**

---

## 1. Instrumentation temporaire (minimale)

**Option préférée :** snippet inline dans [`terrain-shell.tsx`](apps/web/src/components/layout/terrain-shell.tsx) derrière `import.meta.env.DEV` — ref sur le conteneur racine, logs T0/T1/T2 au `focusin` / `focusout` / `visualViewport` `resize`.

**Alternative :** mesures manuelles via Safari Web Inspector (remote debugging) sans toucher au code.

Pas de helper dédié ([`ios-keyboard-layout-probe.ts`](apps/web/src/lib/ios-keyboard-layout-probe.ts)) sauf si le inline devient ingérable.

**La sonde ne corrige rien** — mesure uniquement.

---

## 2. Première repro — chat PWA

Route : conversation chat, textarea composer. Mode : **PWA standalone** uniquement dans un premier temps.

| Instant | Moment |
|---------|--------|
| **T0** | Au repos |
| **T1** | Au focus, bug visible |
| **T2** | Après le tap qui restaure le layout |

**Métriques** (à chaque instant) :

- `window.scrollY`
- `document.scrollingElement.scrollTop`
- `window.innerHeight`
- `visualViewport.height`
- `visualViewport.offsetTop`
- `TerrainShell.getBoundingClientRect()` → `top`, `height`

**Étendre** à Safari navigateur et à d'autres champs (`/reporting`, etc.) **seulement si** le premier résultat est ambigu ou pour confirmer que le bug est partagé.

---

## 3. Diagnostic (à confirmer par les chiffres)

Trois signaux observables aux deltas **T0 → T1** (résidu **T2**). **Non exclusifs** — plusieurs peuvent coexister.

| Signal | Indice |
|--------|--------|
| Scroll document | `scrollY` ou `scrollingElement.scrollTop` augmente |
| Visual viewport | `visualViewport.offsetTop` ou autre décalage vv sans scroll doc |
| Hauteur shell | `visualViewport.height` baisse mais `shellHeight` reste ~T0 ; noter si `h-dvh` suit ou non |

Le diagnostic retenu guide le fix ; il n'impose pas encore d'implémentation.

---

## 4. Fix (après diagnostic uniquement)

**Règle :** diff minimal scoped [`TerrainShell`](apps/web/src/components/layout/terrain-shell.tsx), une décision par signal confirmé.

| Signal confirmé | Principe (sans implémentation figée) |
|-----------------|--------------------------------------|
| Scroll document | Lock ou contrepoids scoped terrain **seulement** si scroll mesuré |
| Visual viewport | Correctif adapté aux mesures — **ne pas présupposer** une compensation `offsetTop` |
| Hauteur shell | Ajuster la hauteur **seulement** si mesure prouve `h-dvh` (ou l'unité actuelle) incorrecte |

Exclus sans preuve : fix chat-only, padding clavier arbitraire, topbar/composer `fixed`, lock ou changement `h-dvh` « au cas où ».

**Tests automatisés :** définis **après** choix du fix réel — comportement ajouté, pas classes CSS.

---

## 5. Résultat attendu

1. **Mesure** — tableau T0/T1/T2 (chat PWA ; extensions si besoin)
2. **Diagnostic** — signaux confirmés, combinaisons incluses
3. **Diff minimal** — aligné sur le diagnostic
4. **Revalidation iPhone** — T1/T2 post-fix OK ; régression login, modale photo, scroll interne
5. **Retrait** de l'instrumentation temporaire
