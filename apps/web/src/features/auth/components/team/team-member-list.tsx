import { useMemo } from 'react'

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
  const sectionRowOffsets = useMemo(
    () =>
      sections.reduce<number[]>(
        (offsets, _, sectionIndex) => [
          ...offsets,
          sectionIndex === 0
            ? 0
            : offsets[sectionIndex - 1]! + sections[sectionIndex - 1]!.members.length,
        ],
        [],
      ),
    [sections],
  )

  return (
    <div className="space-y-4">
      {sections.map((section, sectionIndex) => (
        <section key={section.role} className="space-y-2">
          <TerrainSectionLabel>
            {section.label} · {section.members.length}
          </TerrainSectionLabel>
          <div className="space-y-2">
            {section.members.map((membership, memberIndex) => (
              <TeamMemberRow
                key={membership.id}
                membership={membership}
                isSelf={membership.id === activeMembershipId}
                onSelect={onSelectMember}
                index={sectionRowOffsets[sectionIndex] + memberIndex}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
