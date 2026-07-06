import { WheelColumn } from './planning-wheel-column'

export type PlanningOptionPickerOption = {
  value: string
  label: string
}

type PlanningOptionPickerProps = {
  value: string
  options: PlanningOptionPickerOption[]
  onChange: (value: string) => void
  ariaLabel: string
}

export function PlanningOptionPicker({
  value,
  options,
  onChange,
  ariaLabel,
}: PlanningOptionPickerProps) {
  return (
    <div className="relative px-3 pb-3">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-3 top-1/2 h-9 -translate-y-1/2 rounded-lg bg-[#EEF3FF]"
      />
      <div className="relative">
        <WheelColumn label={ariaLabel} options={options} value={value} onChange={onChange} />
      </div>
    </div>
  )
}
