/** Move complete draft objects: identities, assignees and dates stay attached. */
export function reorderDraftTasks<T extends { id: string }>(
  tasks: T[],
  id: string,
  targetId: string,
): T[] {
  const from = tasks.findIndex((task) => task.id === id)
  const to = tasks.findIndex((task) => task.id === targetId)
  if (from < 0 || to < 0 || from === to) return tasks
  const next = [...tasks]
  const [task] = next.splice(from, 1)
  next.splice(to, 0, task)
  return next
}
