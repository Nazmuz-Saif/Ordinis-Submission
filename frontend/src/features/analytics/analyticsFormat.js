// "+2.5 pts vs last month". No text at all when last month had no attendance to compare with.
export function changeText(change) {
  if (change === null || change === undefined) return { text: undefined, tone: 'neutral' }
  const sign = change > 0 ? '+' : ''
  const tone = change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral'
  return { text: `${sign}${change} pts vs last month`, tone }
}
