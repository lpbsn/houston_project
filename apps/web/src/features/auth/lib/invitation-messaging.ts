export function buildInvitationCreatedMessage(email: string) {
  return `Invitation créée. Un email va être envoyé à ${email}.`
}

export function buildInvitationResentMessage(email: string) {
  return `Invitation renvoyée à ${email}`
}

export function buildInvitationResentDisabledEmailMessage(email: string) {
  return (
    `Le nouveau lien a été généré pour ${email}, mais l'email n'a pas pu être envoyé. ` +
    'Vous pouvez copier le lien et le transmettre manuellement.'
  )
}

export const REINVITE_CONFIRM_MESSAGE =
  "Un nouveau lien d'invitation va être généré. L'ancien lien ne sera plus utilisable."
