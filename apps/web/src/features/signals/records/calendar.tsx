import type { FieldRecord } from './api'
import { dateLabel } from './shared'

const iso = (date: Date) => date.toISOString().slice(0, 10)
export function monthWindow(month: string) {
  const first = new Date(`${month}-01T12:00:00Z`)
  first.setUTCDate(first.getUTCDate() - ((first.getUTCDay() + 6) % 7))
  const days = Array.from({ length: 42 }, (_, index) => {
    const day = new Date(first)
    day.setUTCDate(day.getUTCDate() + index)
    return iso(day)
  })
  return { days, from: days[0], to: days[41] }
}
export function recordWeekSpans(
  records: FieldRecord[],
  first: string,
  last: string,
) {
  const ordered = records
    .filter(
      (r) => r.calendar && r.calendar.start <= last && r.calendar.end >= first,
    )
    .sort(
      (a, b) =>
        a.calendar!.start.localeCompare(b.calendar!.start) ||
        a.id.localeCompare(b.id),
    )
  const occupied: number[] = []
  return ordered.map((record) => {
    const calendar = record.calendar!
    const start = Math.max(
      0,
      Math.round((Date.parse(calendar.start) - Date.parse(first)) / 86400000),
    )
    const end = Math.min(
      6,
      Math.round((Date.parse(calendar.end) - Date.parse(first)) / 86400000),
    )
    let lane = occupied.findIndex((previousEnd) => previousEnd < start)
    if (lane < 0) lane = occupied.length
    occupied[lane] = end
    return { record, start, end, lane }
  })
}
export function RecordCalendar({
  records,
  month,
  onOpen,
}: {
  records: FieldRecord[]
  month: string
  onOpen: (id: string) => void
}) {
  const { days } = monthWindow(month)
  return (
    <div className="overflow-x-auto rounded-2xl border border-[#CBD5CA] bg-white text-[#17251F]">
      <div className="min-w-[700px]">
        <div className="grid grid-cols-7 bg-[#EFF3ED] p-3 text-center text-xs font-bold">
          {['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.', 'Dim.'].map((d) => (
            <span key={d}>{d}</span>
          ))}
        </div>
        {Array.from({ length: 6 }, (_, week) => {
          const weekDays = days.slice(week * 7, week * 7 + 7)
          const spans = recordWeekSpans(records, weekDays[0], weekDays[6])
          const lanes = Math.max(1, ...spans.map((s) => s.lane + 1))
          return (
            <div
              key={week}
              className="relative border-t border-[#DADFD8]"
              style={{ minHeight: 44 + lanes * 36 }}
            >
              <div className="absolute inset-0 grid grid-cols-7">
                {weekDays.map((d) => (
                  <div
                    key={d}
                    className={`border-r border-[#E2E7DF] px-3 py-2 text-xs ${d.startsWith(month) ? 'text-[#17251F]' : 'bg-[#F5F6F3] text-[#566256]'}`}
                  >
                    {Number(d.slice(8))}
                  </div>
                ))}
              </div>
              <div
                className="relative grid grid-cols-7 gap-y-1 px-1 pt-9 pb-2"
                style={{ gridTemplateRows: `repeat(${lanes}, 32px)` }}
              >
                {spans.map(({ record, start, end, lane }) => (
                  <button
                    key={record.id}
                    onClick={() => onOpen(record.id)}
                    className={`mx-0.5 truncate rounded-lg px-2 text-left text-xs font-semibold focus:outline-2 focus:outline-offset-2 focus:outline-[#075940] ${record.calendar?.overdue ? 'bg-[#FCE5DF] text-[#861F13]' : 'bg-[#DCEDE4] text-[#064C35]'}`}
                    style={{
                      gridColumn: `${start + 1} / ${end + 2}`,
                      gridRow: lane + 1,
                    }}
                    title={`${record.title} · Échéance ${dateLabel(record.due_on!)}${record.stage === 'closed' ? ' · Clos' : ''}`}
                  >
                    {record.calendar!.start < weekDays[0] ? '‹ ' : ''}
                    {record.title}
                    {record.due_on! >= weekDays[0] &&
                    record.due_on! <= weekDays[6]
                      ? ` · ◆ ${Number(record.due_on!.slice(8))}`
                      : ''}
                    {record.calendar!.end > weekDays[6] ? ' ›' : ''}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
