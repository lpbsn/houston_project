import { PUBLIC_TERMS_URL } from '@/lib/legal'

type TermsAcceptCheckboxProps = {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  id?: string
}

export function TermsAcceptCheckbox({
  checked,
  onCheckedChange,
  id = 'terms-accept',
}: TermsAcceptCheckboxProps) {
  return (
    <label className="flex items-start gap-2 text-sm text-[#5c5a54]" htmlFor={id}>
      <input
        id={id}
        type="checkbox"
        className="mt-1"
        checked={checked}
        onChange={(event) => onCheckedChange(event.target.checked)}
      />
      <span>
        J’accepte les{' '}
        <a href={PUBLIC_TERMS_URL} className="underline" target="_blank" rel="noreferrer">
          conditions d’utilisation
        </a>{' '}
        (optionnel maintenant ; requis avant de publier un contenu visible par l’équipe).
      </span>
    </label>
  )
}
