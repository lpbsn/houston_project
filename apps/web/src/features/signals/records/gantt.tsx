import { BusinessUnitBadge } from '@/components/ui/terrain/business-unit-badge'
import type { FieldRecord, RecordStage } from './api'
import { dateLabel, stages } from './shared'
import { dateInZone, ganttSpan, ganttWindow, type GanttZoom } from './gantt-layout'

const tone: Record<RecordStage, { background: string; color: string }> = {
  todo: { background: '#E4EAE6', color: '#253E31' },
  doing: { background: '#075940', color: '#FFFFFF' },
  review: { background: '#FFE4A1', color: '#523300' },
  closed: { background: '#E3E5E8', color: '#303A45' },
}
const monthLabel = (day: string) =>
  new Intl.DateTimeFormat('fr-FR', {
    month: 'long', year: 'numeric', timeZone: 'UTC',
  }).format(new Date(`${day}T12:00:00Z`))

export function RecordGantt({
  records,
  month,
  zoom,
  timeZone,
  onOpen,
}: {
  records: FieldRecord[]
  month: string
  zoom: GanttZoom
  timeZone: string
  onOpen: (id: string) => void
}) {
  const { days, from, to } = ganttWindow(month, zoom)
  const today = dateInZone(timeZone)
  const todayIndex = days.indexOf(today)
  const dayWidth = zoom === 'month' ? 36 : 16
  const labelWidth = 300
  const timelineWidth = days.length * dayWidth
  const rows = records.flatMap((record) => {
    const span = ganttSpan(record, from, to)
    return span ? [{ record, ...span }] : []
  })
  const months = days.reduce<{ month: string; count: number }[]>(
    (groups, day) => {
      const key = day.slice(0, 7)
      const last = groups.at(-1)
      if (last?.month === key) last.count += 1
      else groups.push({ month: key, count: 1 })
      return groups
    }, [],
  )
  const weekends = days.flatMap((day, index) => {
    const weekday = new Date(`${day}T12:00:00Z`).getUTCDay()
    return weekday === 0 || weekday === 6 ? [index] : []
  })
  const gridStyle = {
    backgroundImage: 'linear-gradient(to right, #DFE5DF 1px, transparent 1px)',
    backgroundSize: `${dayWidth}px 100%`,
  }

  return (
    <section aria-label="Diagramme de Gantt" className="space-y-3 text-[#17251F]">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
        {stages.map((stage) => (
          <span key={stage.id} className="inline-flex items-center gap-2">
            <span aria-hidden="true" className="h-3 w-6 rounded border border-black/15" style={{ background: tone[stage.id].background }} />
            {stage.label}
          </span>
        ))}
        <span className="font-semibold">◆ Échéance</span>
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="h-3 w-0.5 bg-[#075940]" />
          Aujourd’hui
        </span>
        <span className="text-[#95271A]">Zone hachurée : retard</span>
      </div>
      <div
        role="region"
        aria-label="Planning des fiches, défilement horizontal et vertical"
        tabIndex={0}
        className="max-h-[70vh] overflow-auto rounded-2xl border border-[#C9D2C7] bg-white shadow-sm focus-visible:outline-2 focus-visible:outline-[#075940]"
      >
        <div style={{ width: labelWidth + timelineWidth }}>
          <div className="sticky top-0 z-30 flex border-b border-[#C9D2C7] bg-[#F0F4EE]">
            <div className="sticky left-0 z-40 flex shrink-0 flex-col justify-center border-r border-[#C9D2C7] bg-[#F0F4EE] px-4 py-3" style={{ width: labelWidth }}>
              <span className="text-sm font-semibold">Fiche · responsable</span>
              <span className="mt-1 text-xs text-[#45564A]">{rows.length} fiche{rows.length > 1 ? 's' : ''} affichée{rows.length > 1 ? 's' : ''}</span>
            </div>
            <div style={{ width: timelineWidth }}>
              <div className="flex h-9 border-b border-[#D7DFD5]">
                {months.map((group) => (
                  <div key={group.month} className="truncate border-r border-[#C9D2C7] px-3 py-2 text-xs font-semibold capitalize" style={{ width: group.count * dayWidth }}>
                    {monthLabel(`${group.month}-01`)}
                  </div>
                ))}
              </div>
              <div className="flex h-10">
                {days.map((day, index) => {
                  const weekday = new Date(`${day}T12:00:00Z`).getUTCDay()
                  const showLabel = zoom === 'month' || weekday === 1 || day === today
                  return (
                    <div key={day} title={day === today ? `Aujourd’hui · ${dateLabel(day)}` : dateLabel(day)} aria-current={day === today ? 'date' : undefined} className={`relative shrink-0 border-r border-[#DFE5DF] text-center text-xs ${day === today ? 'bg-[#075940] font-bold text-white' : weekends.includes(index) ? 'bg-[#E5EBE3]' : ''}`} style={{ width: dayWidth }}>
                      {showLabel && (
                        <span className={`absolute left-0 top-3 ${zoom === 'quarter' ? 'z-10 whitespace-nowrap pl-1' : 'w-full'}`}>
                          {Number(day.slice(8))}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
          {rows.map(({ record, start, end, due, lateStart, continuesBefore, continuesAfter }) => {
            const stage = stages.find((item) => item.id === record.stage)!.label
            const calendar = record.calendar!
            const caption = `${record.title} · ${stage} · Du ${dateLabel(calendar.start)} au ${dateLabel(calendar.end)} · Échéance ${dateLabel(calendar.due)}${calendar.overdue ? ' · En retard' : ''}${record.blocked_reason ? ` · Bloqué : ${record.blocked_reason}` : ''}`
            return (
              <div key={record.id} className="flex h-28 border-b border-[#DFE5DF] last:border-b-0">
                <div className="sticky left-0 z-20 flex shrink-0 flex-col justify-center gap-1 border-r border-[#C9D2C7] bg-white px-4 py-2" style={{ width: labelWidth }}>
                  <button title={record.title} onClick={() => onOpen(record.id)} className="line-clamp-1 text-left text-sm font-semibold leading-tight hover:underline focus-visible:outline-2 focus-visible:outline-[#075940]">{record.title}</button>
                  <div className="flex items-center gap-2">
                    <BusinessUnitBadge colorIndex={record.color_index} className="truncate">{record.pole}</BusinessUnitBadge>
                    {record.blocked_reason && <span title={record.blocked_reason} className="shrink-0 rounded bg-[#FFE4A1] px-1.5 py-0.5 text-[11px] font-semibold text-[#523300]">Bloqué</span>}
                  </div>
                  <p className="truncate text-xs text-[#344A3D]">{record.owner?.name ?? 'Responsable à définir'}</p>
                  <p className={`text-xs ${calendar.overdue ? 'font-semibold text-[#95271A]' : 'text-[#344A3D]'}`}>
                    {calendar.overdue ? 'En retard' : stage} · Éch. {dateLabel(calendar.due)}
                  </p>
                </div>
                <div className="relative isolate shrink-0" style={{ width: timelineWidth, ...gridStyle }}>
                  {weekends.map((day) => <span key={day} aria-hidden="true" className="pointer-events-none absolute inset-y-0 bg-[#EDF1EA]/65" style={{ left: day * dayWidth, width: dayWidth }} />)}
                  {todayIndex >= 0 && <span aria-hidden="true" className="pointer-events-none absolute inset-y-0 z-10 w-0.5 bg-[#075940]/60" style={{ left: (todayIndex + 0.5) * dayWidth }} />}
                  <button
                    aria-label={`Ouvrir ${caption}`}
                    title={caption}
                    onClick={() => onOpen(record.id)}
                    className={`absolute top-9 z-10 h-10 overflow-hidden rounded-lg border border-black/20 text-left text-xs font-semibold shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#075940] ${record.blocked_reason ? 'ring-2 ring-[#B47816] ring-offset-1' : ''}`}
                    style={{ left: start * dayWidth + 2, width: (end - start + 1) * dayWidth - 4, ...tone[record.stage] }}
                  >
                    {lateStart !== null && <span aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-0 border-l border-[#95271A]" style={{ left: `${((lateStart - start) / (end - start + 1)) * 100}%`, background: 'repeating-linear-gradient(135deg, #F9D5CB 0px, #F9D5CB 5px, #F2B9A9 5px, #F2B9A9 10px)' }} />}
                    {(end - start + 1) * dayWidth >= 100 && <span className="relative mx-2 block w-fit max-w-[calc(100%-16px)] truncate rounded bg-white px-1.5 py-0.5 text-[#17251F]">
                      {`${continuesBefore ? '‹ ' : ''}${stage}${continuesAfter ? ' ›' : ''}`}
                    </span>}
                  </button>
                  {due !== null && (
                    <span role="img" aria-label={`Échéance de ${record.title} : ${dateLabel(calendar.due)}`} title={`Échéance : ${dateLabel(calendar.due)}`} className="pointer-events-none absolute top-[26px] z-20 h-3 w-3 rotate-45 rounded-[2px] border-2 border-white bg-[#162B22] shadow-sm" style={{ left: (due + 0.5) * dayWidth - 6 }} />
                  )}
                </div>
              </div>
            )
          })}
          {!rows.length && <p className="sticky left-0 w-fit max-w-full p-6 text-sm text-[#344A3D]">Aucune fiche avec échéance sur cette période.</p>}
        </div>
      </div>
      <p className="text-xs text-[#45564A]">Une ligne par fiche, de sa création à sa fin. La couleur indique son étape. Cliquez pour ouvrir le détail.</p>
    </section>
  )
}
