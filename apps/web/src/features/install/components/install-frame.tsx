import sporeIcon from '@/assets/brand/spore-icon-green.png'

export function InstallFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh grid-rows-[auto_1fr_auto] bg-[#F9FAFB] bg-[radial-gradient(circle_at_bottom_left,rgba(139,92,246,0.06),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(59,130,246,0.06),transparent_40%)]">
      <header className="px-4 pt-[max(1rem,var(--app-safe-top))]" aria-hidden />
      <main className="flex flex-col items-center justify-center gap-6 px-4 py-8">
        <div className="flex items-center gap-2.5">
          <span className="text-3xl font-bold tracking-tight text-[#111827]">spore</span>
          <img src={sporeIcon} alt="" className="size-16 object-contain" />
        </div>
        <div className="w-full max-w-lg">{children}</div>
      </main>
      <footer className="pb-[max(1.5rem,var(--app-safe-bottom))] text-center text-xs text-[#9CA3AF]">
        © 2026 Spore
      </footer>
    </div>
  )
}
