import { TeamMemberRow } from '@/features/auth/components/team/team-member-row'
import type { TeamRoleSection } from '@/features/auth/lib/team-members'
import { TerrainSectionLabel } from '@/components/ui/terrain'

type TeamMemberListProps = {
  sections: TeamRoleSection[]
  activeMembershipId: string | null
  onSelectMember: (membershipId: string) => void
}

export function TeamMemberList({
  sections,
  activeMembershipId,
  onSelectMember,
}: TeamMemberListProps) {
  let rowIndex = 0

  return (
    <div className="space-y-4">
      {sections.map((section) => (
        <section key={section.role} className="space-y-2">
          <TerrainSectionLabel>
            {section.label} · {section.members.length}
          </TerrainSectionLabel>
          <div className="space-y-2">
            {section.members.map((membership) => {
              const index = rowIndex
              rowIndex += 1
              return (
                <TeamMemberRow
                  key={membership.id}
                  membership={membership}
                  isSelf={membership.id === activeMembershipId}
                  onSelect={onSelectMember}
                  index={index}
                />
              )
            })}
          </div>
        </section>
      ))}
    </div>
  )
}
