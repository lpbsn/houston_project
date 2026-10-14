import { useRef, useState, type FormEvent } from 'react'
import { QueryClient, QueryClientProvider, useMutation } from '@tanstack/react-query'

import { sendContact } from '../contact-api'
import { ContactVerification } from './contact-verification'
import '../landing-contact.css'

const queryClient = new QueryClient()
function ContactForm() {
  const [token, setToken] = useState('')
  const [verificationKey, setVerificationKey] = useState(0)
  const requestId = useRef<string | undefined>(undefined)
  const busy = useRef(false)
  const mutation = useMutation({ mutationFn: sendContact, retry: false })
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy.current || !token) return
    busy.current = true
    const form = event.currentTarget
    const fields = new FormData(form)
    requestId.current ??= crypto.randomUUID()
    try {
      await mutation.mutateAsync({
        name: String(fields.get('name') || ''), email: String(fields.get('email') || ''),
        organization: String(fields.get('organization') || ''), phone: String(fields.get('phone') || ''),
        message: String(fields.get('message') || ''), website: String(fields.get('website') || ''),
        token, requestId: requestId.current,
      })
      form.reset()
    } catch { /* Keep the form intact; the mutation renders the error below. */ }
    finally { busy.current = false; setToken(''); setVerificationKey(n => n + 1) }
  }
  if (mutation.isSuccess) return <div className="sp-contact-success" role="status">
    <h3>Merci, votre demande a bien été envoyée.</h3>
    <p>Nous reviendrons vers vous pour échanger sur votre établissement.</p>
  </div>
  return <form onSubmit={submit} aria-label="Contacter Spore" aria-busy={mutation.isPending}>
    <fieldset disabled={mutation.isPending}>
      <div className="sp-contact-grid">
        <label>Nom et prénom<input id="sp-contact-name" name="name" autoComplete="name" required maxLength={120} /></label>
        <label>E-mail professionnel<input name="email" type="email" autoComplete="email" required maxLength={254} /></label>
        <label>Établissement ou groupe<input name="organization" autoComplete="organization" required maxLength={180} /></label>
        <label>Téléphone (facultatif)<input name="phone" type="tel" autoComplete="tel" maxLength={40} /></label>
      </div>
      <label>Votre message<textarea name="message" required maxLength={4000} rows={4} placeholder="Parlez-nous de votre établissement et de vos besoins." /></label>
      <div className="sp-contact-honeypot" aria-hidden="true">
        <label>Site internet<input name="website" tabIndex={-1} autoComplete="off" /></label>
      </div>
      <p className="sp-contact-privacy">Vos coordonnées servent à répondre à votre demande. Aucune inscription automatique à une newsletter. <a href="/politique-de-confidentialite/">Politique de confidentialité</a>.</p>
      <ContactVerification key={verificationKey} onToken={setToken} />
      {mutation.isError && <p className="sp-contact-error" role="alert">L’envoi n’a pas pu être confirmé. Vos informations sont conservées ici : réessayez après la vérification.</p>}
      <button className="sp-button" type="submit" disabled={mutation.isPending || !token}>
        {mutation.isPending ? 'Envoi en cours…' : 'Envoyer ma demande ↗'}
      </button>
    </fieldset>
  </form>
}
export function LandingContact() {
  return <section id="sp-contact" className="sp-wrap sp-section sp-contact" tabIndex={-1} aria-labelledby="sp-contact-title">
    <div className="sp-eyebrow">Parlons de votre établissement</div>
    <h2 id="sp-contact-title">Découvrez Spore en action.</h2>
    <p>Une démonstration, une question ou un projet multi-établissements ? Écrivez-nous.</p>
    <QueryClientProvider client={queryClient}><ContactForm /></QueryClientProvider>
  </section>
}
